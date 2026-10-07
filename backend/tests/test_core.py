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
from app.services.intent_service import parse_intent
from app.services.recipient_service import resolve_recipient
from app.services.safe_to_spend_service import calculate_safe_to_spend, check_transaction_impact
from app.services.transaction_draft_service import DraftState, create_draft, get_draft_summary, transition_state
from app.services.relationship_service import classify_relationship
from app.services.trusted_helper_service import add_trusted_helper
from app.services.recipient_service import add_trusted_contact
from app.services.helper_mode_service import create_relationship, helper_access, revoke, update_permissions

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

def test_banglish_send_intent_never_invents_a_recipient_or_amount():
    parsed=parse_intent("Rafi ke 2000 taka pathabo")
    assert parsed.intent == "send_money"
    assert parsed.recipient_query == "rafi"
    assert parsed.amount == 2000
    incomplete=parse_intent("Rafi ke taka pathao")
    assert incomplete.intent == "send_money"
    assert incomplete.recipient_query == "rafi"
    assert incomplete.amount is None

def test_safe_to_spend_and_transfer_impact_reconcile():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        safe=calculate_safe_to_spend(db,user)
        assert safe['safe_to_spend'] == max(0, round(safe['current_balance']-safe['upcoming_committed_expenses']-safe['recommended_reserve']-safe['reserved_savings'],2))
        impact=check_transaction_impact(db,user,2000)
        assert impact['total'] >= 2005
        assert impact['safe_to_spend_after'] <= safe['safe_to_spend']
    finally: db.close()

def test_recipient_resolution_and_draft_state_machine_require_human_steps():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        contact, ambiguous=resolve_recipient(db,user.id,"Rafi")
        assert contact is not None and not ambiguous and contact.name == "Rafi Ahmed"
        draft=create_draft(db,user.id,contact.id,contact.name,contact.phone_number,2000)
        assert draft.state == DraftState.DRAFT.value
        summary=get_draft_summary(db,draft,user,classify_relationship(db,user.id,contact,contact.name,2000),calculate_safe_to_spend(db,user))
        assert summary['balance_after'] == round(float(user.account.balance)-summary['total'],2)
        assert summary['runway_after_days'] <= summary['runway_before_days']
        with __import__('pytest').raises(ValueError):
            transition_state(db,draft,DraftState.COMPLETED)
        transition_state(db,draft,DraftState.REVIEWED)
        transition_state(db,draft,DraftState.CONFIRMED)
        transition_state(db,draft,DraftState.PIN_VERIFIED)
        transition_state(db,draft,DraftState.COMPLETED)
        assert draft.state == DraftState.COMPLETED.value
    finally: db.close()

def test_trusted_helper_never_receives_payment_authority():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        helper=add_trusted_helper(db,user.id,"Nusrat Ahmed","Daughter","01800000000",can_initiate=True)
        assert helper.can_initiate is False
    finally: db.close()

def test_helper_mode_permissions_are_persisted_and_revocation_stops_access():
    db=db_with_demo()
    try:
        owner=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        helper_user=db.scalar(select(User).where(User.email=='demo.salary@upay.local'))
        relationship=create_relationship(db, owner, "Nadia Islam", "01700000000", "Friend", ["guide_navigation"])
        relationship.status="active"; relationship.helper_user_id=helper_user.id; db.commit()
        assert helper_access(db, relationship.id, helper_user.id, "view_financial_health") is None
        update_permissions(db, owner.id, relationship.id, ["guide_navigation", "view_financial_health"])
        assert helper_access(db, relationship.id, helper_user.id, "view_financial_health") is not None
        revoke(db, owner.id, relationship.id)
        assert helper_access(db, relationship.id, helper_user.id, "view_financial_health") is None
    finally: db.close()

def test_ambiguous_recipient_is_returned_for_user_choice():
    db=db_with_demo()
    try:
        user=db.scalar(select(User).where(User.email=='demo.student@upay.local'))
        add_trusted_contact(db,user.id,"Rafi Islam","01811111111","Friend",nickname="Rafi")
        contact, ambiguous=resolve_recipient(db,user.id,"Rafi")
        assert contact is None
        assert {item.name for item in ambiguous} == {"Rafi Ahmed","Rafi Islam"}
    finally: db.close()
