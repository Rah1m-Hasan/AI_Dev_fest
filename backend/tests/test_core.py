"""Service-level verification kept portable for restricted/offline judge environments."""
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from app.db import Base, engine, SessionLocal
from app.models import User, SavingsGoal
from app.services.seed import seed
from app.services.auth import create_token, decode_token
from app.services.analytics_service import spending_summary, run_out_analysis, budget_recommendation, goal_plan, forecast, health_score, safe_to_save, simulate_scenario
from app.services.groq_service import explain

def db_with_demo():
    Base.metadata.create_all(engine)
    db=SessionLocal(); seed(db)
    return db

def test_authentication_token_roundtrip():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        assert decode_token(create_token(user.id))['sub']==str(user.id)
        assert decode_token('not-a-token') is None
    finally: db.close()

def test_transaction_analytics_use_real_seeded_rows():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        spending=spending_summary(db,user.id)
        assert spending['total_spending']>0
        assert round(sum(x['amount'] for x in spending['category_totals']),2)==spending['total_spending']
        assert spending['biggest_category'] in {x['category'] for x in spending['category_totals']}
    finally: db.close()

def test_run_out_evidence_is_grounded_and_fallback_is_available():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        evidence=run_out_analysis(db,user)
        assert evidence['total_expense']>0 and evidence['starting_balance'] is not None
        result=__import__('asyncio').run(explain('run_out',evidence,'Why is my balance low?'))
        assert result['provider'] in {'deterministic_fallback','groq_grounded'}
        assert '৳' in result['text']
    finally: db.close()

def test_budget_savings_forecast_and_health_constraints():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        budget=budget_recommendation(db,user); assert budget['recommended_total_spending']>0 and budget['savings_target']>=0
        goal=SavingsGoal(user_id=user.id,name='Test fund',target_amount=20000,current_amount=1000,target_date=date.today()+timedelta(days=150))
        plan=goal_plan(db,user,goal); assert plan['remaining_amount']==19000 and plan['recommended_weekly_contribution']>0
        cashflow=forecast(db,user,14); assert cashflow['days']==14 and cashflow['expected_expenses']>0
        health=health_score(db,user);assert 0<=health['score']<=100 and len(health['components'])==5
    finally: db.close()

def test_missing_user_scoped_data_is_not_implicitly_created():
    db=db_with_demo()
    try: assert db.get(User,999999) is None
    finally: db.close()

def test_safe_to_save_breakdown_reconciles_without_double_counting_bills():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        result=safe_to_save(db,user,7); breakdown=result['breakdown']
        liquidity=max(0,breakdown['available_balance']+breakdown['expected_income']-breakdown['upcoming_bills']-breakdown['typical_spending']-breakdown['safety_buffer'])
        assert abs(liquidity-breakdown['liquidity_after_needs'])<0.01
        assert abs(min(liquidity,breakdown['disposable_cash_flow_cap'])-breakdown['estimated_flexibility'])<0.01
        assert 0<=result['low']<=result['high']
    finally: db.close()

def test_weekly_reduction_scenario_scales_across_forecast_and_never_mutates_balance():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local')); original=float(user.account.balance)
        result=simulate_scenario(db,user,'reduce_spending',500,7)
        assert result['difference']>500
        assert result['projected_balance']>result['baseline_balance']
        assert float(user.account.balance)==original
    finally: db.close()

def test_budget_categories_are_json_serializable_after_update():
    from app.main import update_budget
    from app.schemas import BudgetIn
    from app.models import Budget
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        budget=db.scalar(select(Budget).where(Budget.user_id==user.id,Budget.status=='active'))
        result=update_budget(budget.id,BudgetIn(total_limit=1000,categories={'Food':Decimal('650.25')}),user,db)
        assert result['categories']['Food']==650.25
        assert isinstance(budget.categories['Food'],float)
    finally: db.close()

def test_required_api_routes_are_registered():
    from app.main import app
    paths={route.path for route in app.routes}
    required={'/api/v1/dashboard/summary','/api/v1/intelligence/overview','/api/v1/transactions/{transaction_id}/context','/api/v1/scenarios/simulate','/api/v1/coach/chat','/api/v1/reports/monthly'}
    assert required<=paths
