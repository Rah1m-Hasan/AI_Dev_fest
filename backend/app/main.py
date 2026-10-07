from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from collections import defaultdict
import re
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db import Base,engine,get_db
from app.models import User,Transaction,Budget,PlanState,SavingsGoal,SavingsContribution,GoalPlanSettings,Notification,CategoryFeedback,HelperRelationship,HelperActivity,HelperAssistanceRequest,PaymentRequest,TrustedContact,TrustedContactAudit
from app.schemas import LoginIn,BudgetIn,PlanIn,GoalIn,GoalUpdateIn,GoalPreviewIn,ContributionIn,ChatIn,CategoryCorrection,ScenarioIn,IntentIn,SendMoneyIn,TrustedContactIn,TrustedContactUpdateIn,PaymentRequestIn,TransactionDraftIn,TrustedHelperIn,HelperRequestIn,HelperModeCreateIn,HelperPermissionsIn,HelperRequestReviewIn,HelperAssistancePrepareIn,AssistantMessageIn,AssistantAuthorizeIn,CompleteLessonIn
from app.api.deps import current_user
from app.services.auth import create_token
from app.services.seed import seed
from app.services.analytics_service import spending_summary,health_score,budget_recommendation,goal_plan,forecast,run_out_analysis,period_bounds,money_pulse,money_runway,safe_to_save,money_story,spending_comparison,simulate_scenario
from app.services.groq_service import explain
from app.core.config import get_settings
from app.services.analytics_service import amount, dec, is_income, is_spending

@asynccontextmanager
async def lifespan(app):
    settings=get_settings()
    if settings.environment.lower() in {"production","staging"}:
        if settings.jwt_secret_key == "demo-only-change-me":
            raise RuntimeError("JWT_SECRET_KEY must be configured outside demo development")
        if not settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("DATABASE_URL must use PostgreSQL outside demo development")
    Base.metadata.create_all(bind=engine)
    db=next(get_db()); seed(db); db.close(); yield
app=FastAPI(title="Upay AI Financial Coach",version="1.0.0",lifespan=lifespan,description="Synthetic-data concept prototype. Not an official upay service.")
app.add_middleware(CORSMiddleware,allow_origins=[get_settings().frontend_url],allow_credentials=True,allow_methods=["GET","POST","PUT","PATCH","DELETE"],allow_headers=["Authorization","Content-Type"])

@app.get("/api/v1/health")
def health(): return {"status":"ok","service":"upay-ai-financial-coach","demo_data":"synthetic"}
@app.get("/api/v1/system/status")
def status(): return {"mode":"demo","data":"synthetic only","groq":"server-side optional with deterministic fallback"}

@app.post("/api/v1/assistant/message")
def assistant_message(body: AssistantMessageIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """One free-form, server-orchestrated entry point for all supported actions."""
    from app.services.assistant_action_service import explain_metric, get_conversation, handle_message
    try:
        conversation = get_conversation(db, user.id, body.conversation_id)
        if body.explain_metric:
            return explain_metric(conversation, body.explain_metric.model_dump())
        return handle_message(db, user, conversation, body.message)
    except PermissionError:
        raise HTTPException(404, "Conversation not found")

@app.post("/api/v1/assistant/actions/{action_id}/confirm")
def assistant_confirm_action(action_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.assistant_action_service import confirm_action
    try: return confirm_action(db, user, action_id)
    except PermissionError: raise HTTPException(404, "Action not found")
    except ValueError as error: raise HTTPException(409, str(error))

@app.post("/api/v1/assistant/actions/{action_id}/authorize")
def assistant_authorize_action(action_id: str, body: AssistantAuthorizeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.assistant_action_service import authorize_action
    try: return authorize_action(db, user, action_id, body.pin)
    except PermissionError: raise HTTPException(404, "Action not found")
    except ValueError as error: raise HTTPException(409, str(error))

@app.delete("/api/v1/assistant/actions/{action_id}")
def assistant_cancel_action(action_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.assistant_action_service import cancel_action
    try: return cancel_action(db, user, action_id)
    except PermissionError: raise HTTPException(404, "Action not found")
    except ValueError as error: raise HTTPException(409, str(error))
@app.post("/api/v1/auth/login")
def login(body:LoginIn,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user: raise HTTPException(401,"Unknown demo profile")
    return {"access_token":create_token(user.id),"token_type":"bearer","user":{"id":user.id,"email":user.email,"display_name":user.display_name,"persona":user.persona,"preferred_language":user.preferred_language}}
@app.get("/api/v1/auth/me")
def me(user:User=Depends(current_user)): return {"id":user.id,"email":user.email,"display_name":user.display_name,"persona":user.persona,"preferred_language":user.preferred_language,"balance":amount(user.account.balance)}

@app.get("/api/v1/dashboard/summary")
def dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    now,start,_=period_bounds(); tx=list(db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.timestamp>=start).order_by(Transaction.timestamp.desc())).all())
    income=sum((t.amount for t in tx if is_income(t)),0); expense=sum((t.amount for t in tx if is_spending(t)),0)
    sp=spending_summary(db,user.id); b=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active").order_by(Budget.id.desc())).first(); fc=forecast(db,user,14)
    weekly=defaultdict(float)
    for t in tx:
        if is_spending(t):weekly[f"Week {(t.timestamp-start).days//7+1}"]+=float(t.amount)
    from app.services.safe_to_spend_service import calculate_safe_to_spend
    return {"disclaimer":"Concept prototype — synthetic demo data, not an official production upay service.","period_label":"Last 30 days","balance":amount(user.account.balance),"this_month":{"income":amount(income),"spending":amount(expense),"savings":amount(income-expense)},"budget":{"limit":amount(b.total_limit) if b else 0,"used":amount(expense),"utilization":round(float(expense/b.total_limit*100),1) if b else 0},"health":health_score(db,user),"spending_breakdown":sp["category_totals"],"weekly_spend":[{"week":k,"amount":round(v,2)} for k,v in sorted(weekly.items())],"recent_transactions":[transaction_out(t) for t in tx[:6]],"ai_insight":{"title":"Calculated spending insight","text":f"{sp['biggest_category'] or 'No category'} is your largest spending category this period.","basis":"deterministic transaction aggregation"},"forecast":fc,"pulse":money_pulse(db,user),"runway":money_runway(db,user),"comparison":spending_comparison(db,user),"safe_to_spend":calculate_safe_to_spend(db,user),"safe_to_save":safe_to_save(db,user,7),"story":money_story(db,user)}

@app.get("/api/v1/intelligence/overview")
def intelligence_overview(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return {"pulse":money_pulse(db,user),"comparison":spending_comparison(db,user),"runway":money_runway(db,user),"safe_to_save":safe_to_save(db,user,7),"story":money_story(db,user),"health":health_score(db,user),"trust":"Calculated from your synthetic demo transactions. Forecasts are estimates, not guarantees."}

@app.get("/api/v1/intelligence/comparison")
def intelligence_comparison(user:User=Depends(current_user),db:Session=Depends(get_db)): return spending_comparison(db,user)
@app.get("/api/v1/intelligence/story")
def intelligence_story(user:User=Depends(current_user),db:Session=Depends(get_db)): return money_story(db,user)
@app.get("/api/v1/intelligence/safe-to-save")
def intelligence_safe_to_save(days:int=Query(7,ge=1,le=30),user:User=Depends(current_user),db:Session=Depends(get_db)): return safe_to_save(db,user,days)
@app.get("/api/v1/intelligence/runway")
def intelligence_runway(user:User=Depends(current_user),db:Session=Depends(get_db)): return money_runway(db,user)
@app.post("/api/v1/scenarios/simulate")
def scenario(body:ScenarioIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    # The service is intentionally read-only: no scenario is ever stored as a
    # transaction, balance, budget, or savings-goal change.
    return simulate_scenario(db,user,body.kind,body.amount,body.days,category=body.category,event_date=body.date,description=body.description)

def transaction_out(t): return {"id":t.id,"merchant_name":t.merchant_name,"category":t.category,"amount":amount(t.amount),"direction":t.direction,"transaction_type":t.transaction_type,"timestamp":t.timestamp.isoformat(),"is_recurring":t.is_recurring,"description":t.description,"source":t.source}
@app.get("/api/v1/transactions")
def transactions(category:str|None=None, direction:str|None=None, q:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),user:User=Depends(current_user),db:Session=Depends(get_db)):
    query=select(Transaction).where(Transaction.user_id==user.id)
    if category: query=query.where(Transaction.category==category)
    if direction: query=query.where(Transaction.direction==direction)
    if q: query=query.where(Transaction.merchant_name.ilike(f"%{q[:80]}%"))
    total=db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows=list(db.scalars(query.order_by(Transaction.timestamp.desc()).offset((page-1)*page_size).limit(page_size)).all())
    return {"items":[transaction_out(t) for t in rows],"page":page,"page_size":page_size,"total":total}
@app.get("/api/v1/transactions/categories")
def categories(): return {"categories":["Food","Transport","Shopping","Bills","Education","Healthcare","Entertainment","Subscriptions","Groceries","Mobile Recharge","Cash Out","Transfers","Rent","Other"]}
@app.get("/api/v1/transactions/summary")
def tx_summary(user:User=Depends(current_user),db:Session=Depends(get_db)): return spending_summary(db,user.id)
@app.post("/api/v1/transactions/check-impact")
def check_transaction_impact(
    amount: float = 0,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    from app.services.safe_to_spend_service import check_transaction_impact as _check
    if amount <= 0:
        raise HTTPException(400,"Amount must be greater than zero")
    return _check(db, user, amount)
@app.get("/api/v1/transactions/{transaction_id}")
def transaction(transaction_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(Transaction,transaction_id)
    if not t or t.user_id!=user.id: raise HTTPException(404,"Transaction not found")
    return transaction_out(t)
@app.get("/api/v1/transactions/{transaction_id}/context")
def transaction_context(transaction_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(Transaction,transaction_id)
    if not t or t.user_id!=user.id: raise HTTPException(404,"Transaction not found")
    summary=spending_summary(db,user.id); comparison=spending_comparison(db,user)
    category=next((item for item in summary["category_totals"] if item["category"]==t.category),None)
    change=next((item for item in comparison["categories"] if item["category"]==t.category),None)
    category_total=dec(category["amount"]) if category else dec(t.amount)
    return {"transaction":transaction_out(t),"category_total":amount(category_total),
            "share_of_category_percent":round(float(dec(t.amount)/category_total*100),1) if category_total else 0,
            "comparison":change,"period":summary["data_period"],"source":"calculated from synthetic demo transactions"}
@app.patch("/api/v1/transactions/{transaction_id}/category")
def correct_category(transaction_id:int,body:CategoryCorrection,user:User=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(Transaction,transaction_id)
    if not t or t.user_id!=user.id: raise HTTPException(404,"Transaction not found")
    db.add(CategoryFeedback(transaction_id=t.id,user_id=user.id,old_category=t.category,new_category=body.category.strip()));t.category=body.category.strip();db.commit();return transaction_out(t)
@app.get("/api/v1/analytics/spending")
def spending(period:str="month",user:User=Depends(current_user),db:Session=Depends(get_db)): return spending_summary(db,user.id,period if period in {"month","week"} else "month")
@app.get("/api/v1/analytics/cashflow")
def cashflow(user:User=Depends(current_user),db:Session=Depends(get_db)):
    now,start,_=period_bounds(); rows=list(db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.timestamp>=start)).all()); income=sum((dec(t.amount) for t in rows if is_income(t)),dec(0)); expense=sum((dec(t.amount) for t in rows if is_spending(t)),dec(0)); return {"income":amount(income),"expense":amount(expense),"net":amount(income-expense),"period":{"start":start.date().isoformat(),"end":now.date().isoformat()},"source":"calculated"}
@app.get("/api/v1/analytics/merchants")
def merchants(user:User=Depends(current_user),db:Session=Depends(get_db)): return {"merchants":spending_summary(db,user.id)["frequent_merchants"]}
@app.get("/api/v1/analytics/recurring")
def recurring(user:User=Depends(current_user),db:Session=Depends(get_db)): return {"recurring_total":spending_summary(db,user.id)["recurring_expenses"]}
@app.get("/api/v1/analytics/comparison")
def comparison(user:User=Depends(current_user),db:Session=Depends(get_db)): return {"categories":spending_summary(db,user.id)["category_totals"]}

@app.post("/api/v1/coach/run-out-analysis")
async def run_out(user:User=Depends(current_user),db:Session=Depends(get_db)):
    evidence=run_out_analysis(db,user); response=await explain("run_out",evidence,"Why did I run out of money?",user.preferred_language)
    return {"evidence":evidence,"explanation":response,"actions":["Set a weekly food target","Create a month-end buffer","Review recurring payments"],"transparency":"Evidence is calculated first; the explanation is grounded only in this evidence."}
@app.post("/api/v1/coach/chat")
async def chat(body:ChatIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    q=body.question.lower()
    if "what if" in q and any(x in q for x in ["less", "reduce", "cut"]):
        match=re.search(r"(?:৳|tk\.?\s*)?([\d,]+(?:\.\d+)?)",q)
        weekly_amount=dec(match.group(1).replace(",","")) if match else dec(500)
        intent,evidence="scenario",{"scenario":simulate_scenario(db,user,"reduce_spending",weekly_amount,7)}
    elif any(x in q for x in ["safe", "save", "savings", "afford"]):
        intent, evidence = "safe_to_save", {"safe_to_save":safe_to_save(db,user),"goals":goals(user,db)}
    elif any(x in q for x in ["what changed", "compare", "difference", "increased", "overspend"]):
        intent, evidence = "spending_comparison", spending_comparison(db,user)
    elif any(x in q for x in ["when", "runway", "run low", "forecast", "bill"]):
        intent, evidence = "forecast", {"runway":money_runway(db,user),"forecast":forecast(db,user,14)}
    elif any(x in q for x in ["goal", "reach"]):
        intent, evidence = "goal_feasibility", {"goals":goals(user,db),"budget":budget_recommendation(db,user)}
    elif any(x in q for x in ["low", "run out", "where", "spend", "খরচ", "টাকা"]):
        intent, evidence = "spending_analysis", run_out_analysis(db,user)
    else:
        intent, evidence = "financial_guidance", {"pulse":money_pulse(db,user),"budget":budget_recommendation(db,user),"forecast":forecast(db,user,14),"health":health_score(db,user)}
    result=await explain("run_out" if intent == "spending_analysis" else "chat",evidence,body.question,body.language)
    return {"answer":result,"intent":intent,"structured_context":evidence,"safety":"Informational guidance only; no transfers, lending, or financial eligibility decisions."}
@app.get("/api/v1/coach/insights")
def insights(user:User=Depends(current_user),db:Session=Depends(get_db)):
    s=spending_summary(db,user.id); return {"insights":[{"type":"spending","severity":"attention","observation":f"{s['biggest_category']} is your largest category this month.","evidence":{"total":s['total_spending']},"suggested_action":"Consider a weekly category target.","confidence":"high"},{"type":"recurring","severity":"info","observation":f"Recurring expenses total ৳{s['recurring_expenses']:,.0f}.","evidence":{"amount":s['recurring_expenses']},"suggested_action":"Review whether each recurring payment is still useful.","confidence":"high"}]}

@app.get("/api/v1/budgets/recommendation")
def budget_rec(user:User=Depends(current_user),db:Session=Depends(get_db)): return budget_recommendation(db,user)

def _plan_out(state: PlanState | None, rec: dict):
    """Keep all plan numbers deterministic and transparently sourced."""
    if not state:
        allocations={"essentials":rec["essential_budget"],"flexible":rec["flexible_budget"],"savings":rec["savings_target"],"safety_buffer":rec["buffer_contribution"]}
        return {"status":"recommended","allocations":allocations,"categories":rec["category_limits"],"accepted_at":None,"updated_at":None,"customized":False}
    return {"status":state.status,"allocations":{"essentials":amount(state.essentials),"flexible":amount(state.flexible),"savings":amount(state.savings),"safety_buffer":amount(state.safety_buffer)},"categories":{key:amount(value) for key,value in state.categories.items()},"accepted_at":state.accepted_at.isoformat() if state.accepted_at else None,"updated_at":state.updated_at.isoformat() if state.updated_at else None,"customized":state.status in {"customized","accepted"}}

def _validate_plan_against_income(body: PlanIn, rec: dict):
    total=body.essentials + body.flexible + body.savings + body.safety_buffer
    if total > dec(rec["period_income"]):
        raise HTTPException(422, f"Plan allocations exceed expected income by ৳{amount(total-dec(rec['period_income'])):,.0f}.")

def _plan_state(user:User, db:Session):
    return db.scalar(select(PlanState).where(PlanState.user_id==user.id))

@app.get("/api/v1/budgets/plan")
def get_plan(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rec=budget_recommendation(db,user)
    return {"recommendation":rec,"plan":_plan_out(_plan_state(user,db),rec)}

@app.put("/api/v1/budgets/plan")
def save_plan(body:PlanIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rec=budget_recommendation(db,user); _validate_plan_against_income(body,rec)
    state=_plan_state(user,db) or PlanState(user_id=user.id)
    state.essentials=body.essentials; state.flexible=body.flexible; state.savings=body.savings; state.safety_buffer=body.safety_buffer
    state.categories={key:amount(value) for key,value in body.categories.items()}; state.status="customized"; state.accepted_at=None
    db.add(state); db.commit(); db.refresh(state)
    return _plan_out(state,rec)

@app.post("/api/v1/budgets/plan/accept")
def accept_plan(body:PlanIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rec=budget_recommendation(db,user); _validate_plan_against_income(body,rec)
    for budget in db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active")):
        budget.status="replaced"
    categories={key:amount(value) for key,value in body.categories.items()}
    budget=Budget(user_id=user.id,total_limit=body.essentials+body.flexible,categories=categories,start_date=date.today()-timedelta(days=29),end_date=date.today())
    db.add(budget); db.flush()
    state=_plan_state(user,db) or PlanState(user_id=user.id)
    state.essentials=body.essentials; state.flexible=body.flexible; state.savings=body.savings; state.safety_buffer=body.safety_buffer; state.categories=categories
    state.status="accepted"; state.budget_id=budget.id; state.accepted_at=datetime.utcnow()
    db.add(state); db.commit(); db.refresh(state)
    return _plan_out(state,rec)
@app.get("/api/v1/budgets/current")
def current_budget(user:User=Depends(current_user),db:Session=Depends(get_db)):
    b=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active").order_by(Budget.id.desc())).first()
    if not b:return None
    spend=spending_summary(db,user.id)["total_spending"];return {"id":b.id,"total_limit":amount(b.total_limit),"categories":{key:amount(value) for key,value in b.categories.items()},"used":spend,"remaining":amount(dec(b.total_limit)-dec(spend)),"status":b.status,"period":{"start":b.start_date.isoformat(),"end":b.end_date.isoformat()}}
@app.post("/api/v1/budgets")
def create_budget(body:BudgetIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    for budget in db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active")):
        budget.status="replaced"
    categories={key:amount(value) for key,value in body.categories.items()}
    start=date.today()-timedelta(days=29); b=Budget(user_id=user.id,total_limit=body.total_limit,categories=categories,start_date=start,end_date=date.today());db.add(b);db.commit();db.refresh(b);return {"id":b.id,"total_limit":amount(b.total_limit),"categories":{key:amount(value) for key,value in b.categories.items()}}
@app.put("/api/v1/budgets/{budget_id}")
def update_budget(budget_id:int,body:BudgetIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    b=db.get(Budget,budget_id)
    if not b or b.user_id!=user.id:raise HTTPException(404,"Budget not found")
    b.total_limit=body.total_limit;b.categories={key:amount(value) for key,value in body.categories.items()};db.commit();return {"id":b.id,"total_limit":amount(b.total_limit),"categories":{key:amount(value) for key,value in b.categories.items()}}

def _goal_or_404(goal_id:int, user:User, db:Session):
    goal=db.get(SavingsGoal,goal_id)
    if not goal or goal.user_id!=user.id: raise HTTPException(404,"Goal not found")
    return goal
def _goal_settings(goal:SavingsGoal, db:Session):
    settings=db.scalar(select(GoalPlanSettings).where(GoalPlanSettings.goal_id==goal.id))
    if not settings:
        settings=GoalPlanSettings(goal_id=goal.id); db.add(settings); db.flush()
    return settings
def _goal_out(goal:SavingsGoal, user:User, db:Session):
    settings=_goal_settings(goal,db)
    plan=goal_plan(db,user,goal)
    return {"id":goal.id,"name":goal.name,"target_amount":amount(goal.target_amount),"current_amount":amount(goal.current_amount),"target_date":goal.target_date.isoformat(),"status":goal.status,"category":settings.category,"saving_preference":settings.saving_preference,"note":settings.note,"planned_monthly_amount":amount(settings.planned_monthly_amount) if settings.planned_monthly_amount else None,"progress_percent":min(100,round(float(goal.current_amount/goal.target_amount*100),1)),"plan":plan}
@app.get("/api/v1/goals")
def goals(user:User=Depends(current_user),db:Session=Depends(get_db)):
    items=[_goal_out(g,user,db) for g in db.scalars(select(SavingsGoal).where(SavingsGoal.user_id==user.id).order_by(SavingsGoal.target_date))]
    db.commit()
    return {"items":items}
@app.post("/api/v1/goals")
def create_goal(body:GoalIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    g=SavingsGoal(user_id=user.id,name=body.goal_name.strip(),target_amount=body.target_amount,current_amount=body.optional_current_savings,target_date=body.deadline);db.add(g);db.flush()
    db.add(GoalPlanSettings(goal_id=g.id,category=body.category.strip(),saving_preference=body.saving_preference,note=body.note.strip() if body.note else None,planned_monthly_amount=body.planned_monthly_amount));db.commit();db.refresh(g);return _goal_out(g,user,db)
@app.get("/api/v1/goals/{goal_id}")
def get_goal(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    return _goal_out(_goal_or_404(goal_id,user,db),user,db)
@app.get("/api/v1/goals/{goal_id}/plan")
def get_goal_plan(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    return goal_plan(db,user,_goal_or_404(goal_id,user,db))
@app.put("/api/v1/goals/{goal_id}")
def update_goal(goal_id:int,body:GoalUpdateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    goal=_goal_or_404(goal_id,user,db); settings=_goal_settings(goal,db)
    if body.deadline and body.deadline <= date.today(): raise HTTPException(422,"deadline must be in the future")
    if body.target_amount is not None:
        if body.target_amount < dec(goal.current_amount): raise HTTPException(422,"target amount cannot be below saved amount")
        goal.target_amount=body.target_amount
    if body.goal_name is not None: goal.name=body.goal_name.strip()
    if body.deadline is not None: goal.target_date=body.deadline
    if body.category is not None: settings.category=body.category.strip()
    if body.saving_preference is not None: settings.saving_preference=body.saving_preference
    if body.note is not None: settings.note=body.note.strip() or None
    if body.planned_monthly_amount is not None: settings.planned_monthly_amount=body.planned_monthly_amount
    db.commit(); db.refresh(goal); return _goal_out(goal,user,db)
@app.post("/api/v1/goals/{goal_id}/alternatives/preview")
def preview_goal_change(goal_id:int,body:GoalPreviewIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    goal=_goal_or_404(goal_id,user,db)
    if body.deadline and body.deadline <= date.today(): raise HTTPException(422,"deadline must be in the future")
    target=body.target_amount if body.target_amount is not None else goal.target_amount
    if dec(target) < dec(goal.current_amount): raise HTTPException(422,"target amount cannot be below saved amount")
    return goal_plan(db,user,goal,target_amount=target,target_date=body.deadline or goal.target_date,planned_monthly_amount=body.planned_monthly_amount)
@app.post("/api/v1/goals/{goal_id}/contributions")
def add_goal_contribution(goal_id:int,body:ContributionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    goal=_goal_or_404(goal_id,user,db)
    if goal.status=="paused": raise HTTPException(409,"Resume this goal before adding money")
    goal.current_amount=dec(goal.current_amount)+body.amount
    if dec(goal.current_amount)>=dec(goal.target_amount): goal.current_amount=goal.target_amount; goal.status="completed"
    db.add(SavingsContribution(goal_id=goal.id,amount=body.amount)); db.commit(); return _goal_out(goal,user,db)
@app.post("/api/v1/goals/{goal_id}/pause")
def pause_goal(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    goal=_goal_or_404(goal_id,user,db)
    if goal.status=="completed": raise HTTPException(409,"Completed goals cannot be paused")
    goal.status="paused"; db.commit(); return _goal_out(goal,user,db)
@app.post("/api/v1/goals/{goal_id}/resume")
def resume_goal(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    goal=_goal_or_404(goal_id,user,db)
    if goal.status=="completed": raise HTTPException(409,"Completed goals cannot be resumed")
    goal.status="active"; db.commit(); return _goal_out(goal,user,db)
@app.delete("/api/v1/goals/{goal_id}")
def delete_goal(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    goal=_goal_or_404(goal_id,user,db)
    for row in db.scalars(select(SavingsContribution).where(SavingsContribution.goal_id==goal.id)): db.delete(row)
    settings=db.scalar(select(GoalPlanSettings).where(GoalPlanSettings.goal_id==goal.id))
    if settings: db.delete(settings)
    db.delete(goal); db.commit(); return {"deleted":True,"id":goal_id}

@app.get("/api/v1/forecast/cashflow")
def cash_forecast(days:int=Query(30,ge=7,le=30),user:User=Depends(current_user),db:Session=Depends(get_db)):return forecast(db,user,days)
@app.get("/api/v1/forecast/upcoming-expenses")
def upcoming(user:User=Depends(current_user),db:Session=Depends(get_db)):return {"items":forecast(db,user,14)["predicted_recurring_expenses"]}
@app.get("/api/v1/financial-health")
def fin_health(user:User=Depends(current_user),db:Session=Depends(get_db)):return health_score(db,user)
@app.get("/api/v1/financial-health/history")
def health_history(user:User=Depends(current_user),db:Session=Depends(get_db)):
    score=health_score(db,user)["score"];return {"history":[{"month":"Previous","score":max(0,score-4)},{"month":"Current","score":score}],"note":"Current is deterministic; historical demo trend is illustrative."}
@app.get("/api/v1/alerts")
def alerts(user:User=Depends(current_user),db:Session=Depends(get_db)):
    b=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active").order_by(Budget.id.desc())).first(); spend=spending_summary(db,user.id)["total_spending"]
    utilization=spend/float(b.total_limit)*100 if b else 0
    data=[{"id":"budget","severity":"attention" if b and utilization>70 else "info","title":"Budget check","body":f"You have used {utilization:.0f}% of your rolling 30-day budget." if b else "Create a budget to receive progress alerts."}]
    data += [{"id":n.id,"severity":n.severity,"title":n.title,"body":n.body,"is_read":n.is_read} for n in db.scalars(select(Notification).where(Notification.user_id==user.id)).all()];return {"alerts":data}
@app.patch("/api/v1/alerts/{alert_id}/read")
def alert_read(alert_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    n=db.get(Notification,alert_id)
    if not n or n.user_id!=user.id:raise HTTPException(404,"Alert not found")
    n.is_read=True;db.commit();return {"id":n.id,"is_read":True}

@app.get("/api/v1/reports/weekly")
def weekly(user:User=Depends(current_user),db:Session=Depends(get_db)):return report(user,db,"week")
@app.get("/api/v1/reports/monthly")
def monthly(user:User=Depends(current_user),db:Session=Depends(get_db)):return report(user,db,"month")
def report(user,db,period):
    sp=spending_summary(db,user.id,period); now,start,_=period_bounds(period); rows=list(db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.timestamp>=start,Transaction.timestamp<now)).all()); income=sum((dec(t.amount) for t in rows if is_income(t)),dec(0)); expense=dec(sp["total_spending"]); current=current_budget(user,db); goal_data=goals(user,db)
    return {"period":period,"period_range":sp["data_period"],"snapshot":{"income":amount(income),"spent":amount(expense),"net":amount(income-expense)},"spending":sp,"comparison":spending_comparison(db,user),"story":money_story(db,user),"budget":current,"goals":goal_data["items"],"health":health_score(db,user),"forecast":forecast(db,user,14),"observations":[f"{sp['biggest_category']} is the largest category.",f"Recurring costs total ৳{sp['recurring_expenses']:,.0f}.","Figures are calculated from synthetic demo data."],"ai_summary":{"provider":"deterministic","text":f"Your {period}ly expense total is ৳{sp['total_spending']:,.0f}. {spending_comparison(db,user)['summary']}"}}
# === LEARN ENDPOINTS ===
@app.get("/api/v1/learning/recommendations")
def learning_recommendations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.learning_service import (
        get_personalized_lessons, get_progress_summary,
        get_user_completed_lesson_ids, get_user_started_lesson_ids,
    )
    from app.schemas import LessonCardOut, LearningRecommendationsOut

    featured, for_you = get_personalized_lessons(db, user)
    completed_ids = get_user_completed_lesson_ids(db, user.id)
    started_ids = get_user_started_lesson_ids(db, user.id)
    progress = get_progress_summary(db, user.id)

    all_cats = ["For You", "Money Basics", "Saving", "Budgeting", "MFS Basics", "Digital Safety"]

    def card_out(lesson, reason):
        return {
            "id": lesson.id,
            "title": lesson.title,
            "summary": lesson.summary,
            "category": lesson.category,
            "difficulty": lesson.difficulty,
            "duration_minutes": lesson.duration_minutes,
            "trigger_type": lesson.trigger_type,
            "trigger_reason": reason,
            "completed": lesson.id in completed_ids,
            "started": lesson.id in started_ids,
        }

    featured_out = card_out(featured[0][0], featured[0][1]) if featured else None
    for_you_out = [card_out(l, r) for l, r in for_you]

    return {
        "featured": featured_out,
        "for_you": for_you_out,
        "tabs": all_cats,
        "progress": progress,
    }


@app.get("/api/v1/learning/lessons")
def learning_lessons(user: User = Depends(current_user), db: Session = Depends(get_db), category: str | None = None):
    from app.services.learning_service import get_all_lessons, get_user_completed_lesson_ids
    from app.schemas import LessonCardOut
    lessons = get_all_lessons(db, category)
    completed_ids = get_user_completed_lesson_ids(db, user.id)
    return {
        "lessons": [
            {
                "id": l.id,
                "title": l.title,
                "summary": l.summary,
                "category": l.category,
                "difficulty": l.difficulty,
                "duration_minutes": l.duration_minutes,
                "trigger_type": l.trigger_type,
                "trigger_reason": None,
                "completed": l.id in completed_ids,
                "started": False,
            }
            for l in lessons
        ]
    }


@app.get("/api/v1/learning/lessons/{lesson_id}")
def learning_lesson_detail(lesson_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.learning_service import get_lesson_detail
    from app.schemas import QuizOut, LessonDetailOut

    lesson, progress, reason = get_lesson_detail(db, lesson_id, user.id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    quiz = None
    if lesson.quiz and isinstance(lesson.quiz, dict):
        quiz = {
            "question": lesson.quiz.get("question", ""),
            "options": lesson.quiz.get("options", []),
            "correct_key": lesson.quiz.get("correct_key", ""),
        }

    return {
        "id": lesson.id,
        "title": lesson.title,
        "summary": lesson.summary,
        "content": lesson.content,
        "content_bn": lesson.content_bn,
        "category": lesson.category,
        "difficulty": lesson.difficulty,
        "duration_minutes": lesson.duration_minutes,
        "personalized_section": lesson.personalized_section,
        "personalized_section_bn": lesson.personalized_section_bn,
        "initial_language": "bn" if user.preferred_language == "bn" and lesson.content_bn else "en",
        "quiz": quiz,
        "trigger_type": lesson.trigger_type,
        "trigger_reason": reason,
        "completed": progress.completed_at is not None if progress else False,
        "started": progress.started_at is not None if progress else False,
    }


@app.post("/api/v1/learning/{lesson_id}/start")
def learning_start(lesson_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.learning_service import start_lesson
    start_lesson(db, user.id, lesson_id)
    return {"started": True}


@app.post("/api/v1/learning/{lesson_id}/complete")
def learning_complete(lesson_id: int, user: User = Depends(current_user), db: Session = Depends(get_db), body: dict | None = None):
    from app.services.learning_service import complete_lesson
    quiz_answer = body.get("quiz_answer") if body else None
    progress, quiz_score = complete_lesson(db, user.id, lesson_id, quiz_answer)
    return {"completed": True, "quiz_score": quiz_score}


@app.get("/api/v1/learning/progress")
def learning_progress(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.learning_service import get_progress_summary
    progress = get_progress_summary(db, user.id)
    return {"categories": progress}


# === OFFERS ENDPOINTS ===
@app.get("/api/v1/offers")
def offers_list(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    category: str | None = None,
    state: str = "active",
):
    from app.services.offers_service import get_all_offers
    from app.models import Offer

    offers_list, prefs = get_all_offers(db, user.id, category, state)
    available_categories = sorted(set(db.scalars(select(Offer.category).where(Offer.active == True)).all()))
    return {
        "offers": offers_list,
        "preferences": prefs,
        "available_categories": available_categories,
        "state": state,
    }


@app.get("/api/v1/offers/saved")
def offers_saved(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.offers_service import get_saved_offers
    offers = get_saved_offers(db, user.id)
    return {"offers": offers}


@app.get("/api/v1/offers/{offer_id}")
def offer_detail(offer_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.offers_service import get_offer_detail
    offer, is_saved = get_offer_detail(db, offer_id, user.id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    return offer


@app.post("/api/v1/offers/{offer_id}/save")
def offer_save(offer_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.offers_service import save_offer
    save_offer(db, user.id, offer_id)
    return {"saved": True}


@app.delete("/api/v1/offers/{offer_id}/save")
def offer_unsave(offer_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.offers_service import unsave_offer
    unsave_offer(db, user.id, offer_id)
    return {"saved": False}


@app.get("/api/v1/offers/preferences")
def offers_preferences(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from app.services.offers_service import _get_user_preference
    return {"personalized_offers_enabled": _get_user_preference(db, user.id)}


@app.put("/api/v1/offers/preferences")
def offers_preferences_update(user: User = Depends(current_user), db: Session = Depends(get_db), body: dict | None = None):
    from app.services.offers_service import _update_preference
    enabled = body.get("enabled", True) if body else True
    _update_preference(db, user.id, enabled)
    return {"personalized_offers_enabled": enabled}

# === NEW AI FINANCIAL COACH ENDPOINTS ===

@app.post("/api/v1/coach/parse-intent")
async def coach_parse_intent(body:IntentIn,user:User=Depends(current_user)):
    """Parse user message into structured intent using deterministic fallback."""
    from app.services.intent_service import parse_intent
    intent = parse_intent(body.question)
    return {"intent":intent.intent,"recipient_query":intent.recipient_query,"amount":intent.amount,"currency":intent.currency,"confidence":intent.confidence,"language":intent.language}

def _mask_phone(phone: str) -> str:
    return f"{phone[:3]}••••••{phone[-2:]}" if len(phone) >= 5 else "Hidden number"

def _trusted_activity(db: Session, user_id: int, contact: TrustedContact):
    transfers = list(db.scalars(select(Transaction).where(Transaction.user_id == user_id, Transaction.merchant_name == contact.name, Transaction.transaction_type == "transfer").order_by(Transaction.timestamp.desc())))
    requests = list(db.scalars(select(PaymentRequest).where(PaymentRequest.user_id == user_id, PaymentRequest.trusted_contact_id == contact.id).order_by(PaymentRequest.created_at.desc())))
    activity = ([{"kind":"sent", "amount":float(row.amount), "at":row.timestamp, "label":"Sent"} for row in transfers] + [{"kind":"requested", "amount":float(row.amount), "at":row.created_at, "label":"Requested"} for row in requests])
    activity.sort(key=lambda row: row["at"], reverse=True)
    return transfers, requests, activity

def _trusted_contact_out(db: Session, user_id: int, contact: TrustedContact, detail: bool = False):
    transfers, requests, activity = _trusted_activity(db, user_id, contact)
    last = activity[0] if activity else None
    result = {"id":contact.id, "name":contact.name, "phone_number":contact.phone_number if detail else _mask_phone(contact.phone_number), "relationship":contact.relationship, "nickname":contact.nickname, "notes":contact.notes if detail else None, "verification_status":contact.verification_status, "verified_at":contact.verified_at.isoformat() if contact.verified_at else None, "created_at":contact.created_at.isoformat(), "last_interaction": last["at"].isoformat() if last else None, "last_transfer_amount":float(transfers[0].amount) if transfers else None, "last_transfer_date":transfers[0].timestamp.date().isoformat() if transfers else None, "total_transfers":len(transfers), "total_requests":len(requests), "first_interaction":activity[-1]["at"].isoformat() if activity else None}
    if detail:
        result["activity"] = [{"kind":row["kind"], "label":row["label"], "amount":row["amount"], "created_at":row["at"].isoformat()} for row in activity[:12]]
    return result

@app.get("/api/v1/trusted-people")
@app.get("/api/v1/trusted-contacts")
def trusted_contacts(q:str|None=None, status:str|None=None, sort:str="recent", user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import get_trusted_contacts
    contacts = get_trusted_contacts(db, user.id)
    if q:
        needle=q.strip().lower()
        contacts=[row for row in contacts if needle in row.name.lower() or needle in row.phone_number or needle in row.relationship.lower() or (row.nickname and needle in row.nickname.lower())]
    if status in {"verified", "unverified", "needs_review"}: contacts=[row for row in contacts if row.verification_status == status]
    items=[_trusted_contact_out(db, user.id, row) for row in contacts]
    if sort == "name": items.sort(key=lambda row: row["name"].lower())
    else: items.sort(key=lambda row: (row["last_interaction"] is not None, row["last_interaction"] or row["created_at"]), reverse=True)
    return {"items":items}

@app.post("/api/v1/trusted-people")
@app.post("/api/v1/trusted-contacts")
def create_trusted_contact(body:TrustedContactIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import add_trusted_contact
    try: contact = add_trusted_contact(db, user.id, body.name, body.phone_number, body.relationship, body.nickname, body.notes)
    except ValueError as error: raise HTTPException(422, str(error))
    return _trusted_contact_out(db, user.id, contact, detail=True)

@app.get("/api/v1/trusted-people/{contact_id}")
def trusted_contact_detail(contact_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import contact_or_none
    contact=contact_or_none(db,user.id,contact_id)
    if not contact: raise HTTPException(404,"Saved person not found")
    return _trusted_contact_out(db,user.id,contact,detail=True)

@app.get("/api/v1/trusted-people/{contact_id}/activity")
def trusted_contact_activity(contact_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import contact_or_none
    contact=contact_or_none(db,user.id,contact_id)
    if not contact: raise HTTPException(404,"Saved person not found")
    return _trusted_contact_out(db,user.id,contact,detail=True)

@app.put("/api/v1/trusted-people/{contact_id}")
def update_trusted_contact(contact_id:int,body:TrustedContactUpdateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import contact_or_none, update_trusted_contact as update_contact
    contact=contact_or_none(db,user.id,contact_id)
    if not contact: raise HTTPException(404,"Saved person not found")
    try: contact=update_contact(db,contact,body.name,body.phone_number,body.relationship,body.nickname,body.notes)
    except ValueError as error: raise HTTPException(422,str(error))
    return _trusted_contact_out(db,user.id,contact,detail=True)

@app.post("/api/v1/trusted-people/{contact_id}/verify")
def verify_trusted_contact(contact_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import contact_or_none, verify_trusted_contact as verify_contact
    contact=contact_or_none(db,user.id,contact_id)
    if not contact: raise HTTPException(404,"Saved person not found")
    return _trusted_contact_out(db,user.id,verify_contact(db,contact),detail=True)

@app.post("/api/v1/trusted-people/{contact_id}/request")
def create_payment_request(contact_id:int,body:PaymentRequestIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import contact_or_none
    contact=contact_or_none(db,user.id,contact_id)
    if not contact: raise HTTPException(404,"Saved person not found")
    request=PaymentRequest(user_id=user.id,trusted_contact_id=contact.id,recipient_name=contact.name,recipient_phone=contact.phone_number,amount=body.amount,note=body.note.strip() if body.note else None)
    db.add(request); db.flush(); db.add(TrustedContactAudit(user_id=user.id,trusted_contact_id=contact.id,event_type="trusted_person_used_for_request")); db.commit(); db.refresh(request)
    return {"id":request.id,"status":request.status,"created_at":request.created_at.isoformat()}

@app.delete("/api/v1/trusted-people/{contact_id}")
@app.delete("/api/v1/trusted-contacts/{contact_id}")
def delete_trusted_contact(contact_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import remove_trusted_contact
    if remove_trusted_contact(db, contact_id, user.id): return {"deleted":True}
    raise HTTPException(404,"Saved person not found")

@app.get("/api/v1/recipients/search")
def search_recipients(q:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import find_best_contact_match
    contacts = find_best_contact_match(db, user.id, q)
    return {"items":[{"id":c.id,"name":c.name,"phone_number":c.phone_number,"relationship":c.relationship,"is_trusted":c.is_trusted} for c in contacts]}

@app.get("/api/v1/recipients/resolve")
def resolve_recipient_query(q:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Resolve a person server-side. Ambiguity is always returned, never guessed."""
    from app.services.recipient_service import resolve_recipient
    contact, ambiguous = resolve_recipient(db, user.id, q)
    def out(c): return {"id":c.id,"name":c.name,"phone_number":c.phone_number,"relationship":c.relationship,"is_trusted":c.is_trusted}
    if contact: return {"status":"resolved","contact":out(contact),"matches":[]}
    if ambiguous: return {"status":"ambiguous","contact":None,"matches":[out(c) for c in ambiguous]}
    return {"status":"not_found","contact":None,"matches":[]}

@app.get("/api/v1/recipients/{recipient_id}/relationship")
def recipient_relationship(recipient_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import get_trusted_contacts
    from app.services.relationship_service import classify_relationship
    contacts = get_trusted_contacts(db, user.id)
    contact = next((c for c in contacts if c.id == recipient_id), None)
    rel_info = classify_relationship(db, user.id, contact, contact.name if contact else "")
    return {"recipient_id":rel_info.recipient_id,"recipient_name":rel_info.recipient_name,"relationship_type":rel_info.relationship_type,"previous_transaction_count":rel_info.previous_transaction_count,"last_transaction_amount":rel_info.last_transaction_amount,"last_transaction_date":rel_info.last_transaction_date,"average_transaction_amount":rel_info.average_transaction_amount,"total_sent":rel_info.total_sent,"evidence":rel_info.evidence}

@app.get("/api/v1/coach/safe-to-spend")
def coach_safe_to_spend(user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.safe_to_spend_service import calculate_safe_to_spend
    return calculate_safe_to_spend(db, user)

@app.get("/api/v1/coach/income-adaptive")
def coach_income_adaptive(user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.income_adaptive_service import calculate_income_adaptive
    return calculate_income_adaptive(db, user)

@app.post("/api/v1/transactions/draft")
def create_transaction_draft(
    body:TransactionDraftIn,
    user:User=Depends(current_user),
    db:Session=Depends(get_db)
):
    from app.services.transaction_draft_service import create_draft, get_draft_summary
    from app.services.relationship_service import classify_relationship
    from app.services.safe_to_spend_service import calculate_safe_to_spend
    from app.services.recipient_service import get_trusted_contacts

    contacts = get_trusted_contacts(db, user.id)
    contact = next((c for c in contacts if c.id == body.recipient_id), None) if body.recipient_id else None
    if body.recipient_id and not contact: raise HTTPException(404, "Saved person not found")
    if contact and (body.recipient_name.strip() != contact.name or body.recipient_phone and body.recipient_phone != contact.phone_number):
        contact.verification_status = "needs_review"; contact.is_trusted = False; db.commit()
        raise HTTPException(409, "Contact details need review. The recipient information differs from the details you saved.")
    if contact and contact.verification_status != "verified" and not body.recognition_confirmed:
        raise HTTPException(409, "Confirm this saved person's phone number before continuing.")
    rel_info = classify_relationship(db, user.id, contact, body.recipient_name, float(body.amount))
    safe_before = calculate_safe_to_spend(db, user)
    draft = create_draft(db, user.id, body.recipient_id, body.recipient_name.strip(), contact.phone_number if contact else body.recipient_phone, float(body.amount), body.reference)
    if contact:
        db.add(TrustedContactAudit(user_id=user.id, trusted_contact_id=contact.id, event_type="trusted_person_used_for_send")); db.commit()
    return get_draft_summary(db, draft, user, rel_info, safe_before)

@app.get("/api/v1/transactions/draft/active")
def get_active_draft(user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.transaction_draft_service import get_active_draft, get_draft_summary
    from app.services.safe_to_spend_service import calculate_safe_to_spend
    from app.services.relationship_service import classify_relationship
    draft = get_active_draft(db, user.id)
    if not draft:
        return {"has_active_draft":False}
    contact = db.scalar(select(TrustedContact).where(TrustedContact.id == draft.recipient_id, TrustedContact.user_id == user.id, TrustedContact.archived_at.is_(None))) if draft.recipient_id else None
    rel_info = classify_relationship(db, user.id, contact, draft.recipient_name, draft.amount)
    safe_before = calculate_safe_to_spend(db, user)
    return {"has_active_draft":True,"draft":get_draft_summary(db, draft, user, rel_info, safe_before)}

@app.post("/api/v1/transactions/draft/{draft_id}/review")
def review_draft(draft_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.transaction_draft_service import get_active_draft, review_draft as _review_draft, DraftState
    draft = get_active_draft(db, user.id)
    if not draft or draft.id != draft_id: raise HTTPException(404,"Draft not found")
    if draft.state != DraftState.DRAFT.value: raise HTTPException(400,f"Cannot review draft in state: {draft.state}")
    draft = _review_draft(db, draft)
    return {"draft_id":draft.id,"state":draft.state}

@app.post("/api/v1/transactions/draft/{draft_id}/confirm")
def confirm_draft(draft_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.transaction_draft_service import get_active_draft, confirm_draft as _confirm_draft, DraftState
    draft = get_active_draft(db, user.id)
    if not draft or draft.id != draft_id:
        raise HTTPException(404,"Draft not found")
    if draft.state != DraftState.REVIEWED.value:
        raise HTTPException(400,f"Cannot confirm draft in state: {draft.state}")
    draft = _confirm_draft(db, draft)
    return {"draft_id":draft.id,"state":draft.state,"requires_pin":True}

@app.post("/api/v1/transactions/draft/{draft_id}/execute")
def execute_draft(draft_id:int,body:SendMoneyIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.transaction_draft_service import get_active_draft, verify_pin, DraftState
    draft = get_active_draft(db, user.id)
    if not draft or draft.id != draft_id:
        raise HTTPException(404,"Draft not found")
    if draft.state != DraftState.CONFIRMED.value:
        raise HTTPException(400,f"Cannot execute draft in state: {draft.state}")
    success, message = verify_pin(db, draft, body.pin)
    if success:
        return {"success":True,"message":"Demo transfer completed. No real money moved.","balance_after":float(db.get(User,user.id).account.balance)}
    return {"success":False,"message":message}

@app.delete("/api/v1/transactions/draft/{draft_id}")
def cancel_draft(draft_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.transaction_draft_service import get_active_draft, cancel_draft as _cancel_draft
    draft = get_active_draft(db, user.id)
    if not draft or draft.id != draft_id:
        raise HTTPException(404,"Draft not found")
    draft = _cancel_draft(db, draft)
    return {"draft_id":draft.id,"state":draft.state}

@app.get("/api/v1/trusted-helpers")
def trusted_helpers(user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.helper_mode_service import output
    helpers = list(db.scalars(select(HelperRelationship).where(HelperRelationship.owner_user_id == user.id).order_by(HelperRelationship.created_at.desc())))
    activities = list(db.scalars(select(HelperActivity).where(HelperActivity.owner_user_id == user.id).order_by(HelperActivity.created_at.desc())))
    latest = {activity.helper_relationship_id: activity for activity in activities if activity.helper_relationship_id is not None}
    return {"items":[output(helper, latest.get(helper.id)) for helper in helpers]}

@app.post("/api/v1/trusted-helpers")
def create_trusted_helper(body:HelperModeCreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.helper_mode_service import create_relationship, output
    try: helper = create_relationship(db, user, body.helper_name, body.phone, body.relationship, body.permissions)
    except ValueError as error: raise HTTPException(422, str(error))
    return output(helper)

@app.get("/api/v1/trusted-helpers/{helper_id}")
def trusted_helper_detail(helper_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.helper_mode_service import relationship_or_none, output
    helper = relationship_or_none(db, user.id, helper_id)
    if not helper: raise HTTPException(404, "Helper not found")
    activity = db.scalar(select(HelperActivity).where(HelperActivity.helper_relationship_id == helper.id).order_by(HelperActivity.created_at.desc()))
    return output(helper, activity)

@app.put("/api/v1/trusted-helpers/{helper_id}/permissions")
def update_helper_permissions(helper_id:int, body:HelperPermissionsIn, user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.helper_mode_service import update_permissions, output
    try: helper = update_permissions(db, user.id, helper_id, body.permissions)
    except ValueError as error: raise HTTPException(409, str(error))
    if not helper: raise HTTPException(404, "Helper not found")
    return output(helper)

@app.post("/api/v1/trusted-helpers/{helper_id}/revoke")
def revoke_helper_access(helper_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.helper_mode_service import revoke, output
    helper = revoke(db, user.id, helper_id)
    if not helper: raise HTTPException(404, "Helper not found")
    return output(helper)

@app.get("/api/v1/trusted-helpers/{helper_id}/activity")
def helper_activity(helper_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.helper_mode_service import relationship_or_none
    if not relationship_or_none(db, user.id, helper_id): raise HTTPException(404, "Helper not found")
    rows = list(db.scalars(select(HelperActivity).where(HelperActivity.helper_relationship_id == helper_id).order_by(HelperActivity.created_at.desc()).limit(50)))
    return {"items":[{"id":row.id,"actor":row.actor,"event_type":row.event_type,"detail":row.detail,"created_at":row.created_at.isoformat()} for row in rows]}

@app.get("/api/v1/helper-activity")
def all_helper_activity(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows = list(db.scalars(select(HelperActivity).where(HelperActivity.owner_user_id == user.id).order_by(HelperActivity.created_at.desc()).limit(30)))
    return {"items":[{"id":row.id,"helper_id":row.helper_relationship_id,"actor":row.actor,"event_type":row.event_type,"detail":row.detail,"created_at":row.created_at.isoformat()} for row in rows]}

@app.get("/api/v1/helper-requests")
def helper_requests(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows = list(db.scalars(select(HelperAssistanceRequest).where(HelperAssistanceRequest.owner_user_id == user.id, HelperAssistanceRequest.status == "waiting_owner_confirmation").order_by(HelperAssistanceRequest.created_at.desc())))
    helpers = {item.id:item for item in db.scalars(select(HelperRelationship).where(HelperRelationship.owner_user_id == user.id))}
    return {"items":[{"id":row.id,"helper_id":row.helper_relationship_id,"helper_name":helpers.get(row.helper_relationship_id).helper_name if helpers.get(row.helper_relationship_id) else "Your helper","request_type":row.request_type,"title":row.title,"detail":row.detail,"status":row.status,"created_at":row.created_at.isoformat()} for row in rows]}

@app.post("/api/v1/helper-requests/{request_id}/review")
def review_helper_request(request_id:int, body:HelperRequestReviewIn, user:User=Depends(current_user),db:Session=Depends(get_db)):
    row = db.get(HelperAssistanceRequest, request_id)
    if not row or row.owner_user_id != user.id: raise HTTPException(404, "Request not found")
    row.status = body.decision; row.reviewed_at = datetime.utcnow()
    db.add(HelperActivity(owner_user_id=user.id, helper_relationship_id=row.helper_relationship_id, event_type="assistance_request_reviewed", detail=f"You {body.decision} a request", actor="owner"))
    db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/helper-access/{relationship_id}/financial-health")
def helper_financial_health(relationship_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Restricted helper-facing example; server enforcement is independent of UI."""
    from app.services.helper_mode_service import helper_access, record_activity
    relationship = helper_access(db, relationship_id, user.id, "view_financial_health")
    if not relationship: raise HTTPException(403, "This helper does not have access to financial health.")
    result = health_score(db, db.get(User, relationship.owner_user_id))
    record_activity(db, relationship.owner_user_id, "helper_viewed_financial_health", relationship.id, f"{relationship.helper_name} viewed Financial Health", actor="helper")
    db.commit()
    return {"owner_name":db.get(User, relationship.owner_user_id).display_name,"financial_health":result}

@app.post("/api/v1/helper-access/{relationship_id}/assistance-requests")
def prepare_assistance_request(relationship_id:int, body:HelperAssistancePrepareIn, user:User=Depends(current_user),db:Session=Depends(get_db)):
    """A helper may prepare details, never authorize or transmit a payment."""
    from app.services.helper_mode_service import helper_access, record_activity
    relationship = helper_access(db, relationship_id, user.id, "prepare_transaction")
    if not relationship: raise HTTPException(403, "This helper cannot prepare transaction assistance.")
    request = HelperAssistanceRequest(owner_user_id=relationship.owner_user_id, helper_relationship_id=relationship.id, request_type="prepared_transaction", title=body.title.strip(), detail=body.detail.strip() if body.detail else None)
    db.add(request)
    record_activity(db, relationship.owner_user_id, "helper_prepared_transaction", relationship.id, f"{relationship.helper_name} prepared {request.title}", actor="helper")
    db.commit(); db.refresh(request)
    return {"id":request.id,"status":request.status,"notice":"Prepared for owner review. No payment has been sent."}

@app.get("/api/v1/helper-invitations")
def my_helper_invitations(user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Account-linked invitations only; external phone invitations expose no data."""
    rows = list(db.scalars(select(HelperRelationship).where(HelperRelationship.helper_user_id == user.id, HelperRelationship.status == "pending").order_by(HelperRelationship.invited_at.desc())))
    return {"items":[{"id":row.id,"owner_name":db.get(User, row.owner_user_id).display_name,"helper_name":row.helper_name,"relationship":row.relationship,"permissions":row.permissions,"invited_at":row.invited_at.isoformat()} for row in rows]}

@app.post("/api/v1/helper-invitations/{relationship_id}/accept")
def accept_helper_invitation(relationship_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.helper_mode_service import accept_invitation, output
    try: relationship = accept_invitation(db, relationship_id, user.id)
    except ValueError as error: raise HTTPException(409, str(error))
    if not relationship: raise HTTPException(404, "Invitation not found")
    return output(relationship)

@app.post("/api/v1/trusted-helper/request")
def create_helper_request(body:HelperRequestIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.trusted_helper_service import create_helper_request as _create_request
    request = _create_request(db, user.id, body.helper_id, body.message)
    return {"request_id":request.id,"status":request.status,"message":request.message,"created_at":request.created_at.isoformat()}
