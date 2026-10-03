from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from collections import defaultdict
import re
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db import Base,engine,get_db
from app.models import User,Transaction,Budget,SavingsGoal,Notification,CategoryFeedback
from app.schemas import LoginIn,BudgetIn,GoalIn,ChatIn,CategoryCorrection,ScenarioIn,IntentIn,SendMoneyIn,TrustedContactIn,TrustedHelperIn,HelperRequestIn
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
def scenario(body:ScenarioIn,user:User=Depends(current_user),db:Session=Depends(get_db)): return simulate_scenario(db,user,body.kind,body.amount,body.days)

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

@app.get("/api/v1/goals")
def goals(user:User=Depends(current_user),db:Session=Depends(get_db)): return {"items":[{"id":g.id,"name":g.name,"target_amount":amount(g.target_amount),"current_amount":amount(g.current_amount),"target_date":g.target_date.isoformat(),"status":g.status,"progress_percent":min(100,round(float(g.current_amount/g.target_amount*100),1)),"plan":goal_plan(db,user,g)} for g in db.scalars(select(SavingsGoal).where(SavingsGoal.user_id==user.id).order_by(SavingsGoal.target_date))]}
@app.post("/api/v1/goals")
def create_goal(body:GoalIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    g=SavingsGoal(user_id=user.id,name=body.goal_name.strip(),target_amount=body.target_amount,current_amount=body.optional_current_savings,target_date=body.deadline);db.add(g);db.commit();db.refresh(g);return {"id":g.id,"name":g.name,"plan":goal_plan(db,user,g)}
@app.get("/api/v1/goals/{goal_id}")
def get_goal(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    g=db.get(SavingsGoal,goal_id)
    if not g or g.user_id!=user.id:raise HTTPException(404,"Goal not found")
    return {"id":g.id,"name":g.name,"target_amount":amount(g.target_amount),"current_amount":amount(g.current_amount),"target_date":g.target_date.isoformat(),"plan":goal_plan(db,user,g)}
@app.get("/api/v1/goals/{goal_id}/plan")
def get_goal_plan(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    g=db.get(SavingsGoal,goal_id)
    if not g or g.user_id!=user.id:raise HTTPException(404,"Goal not found")
    return goal_plan(db,user,g)

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
@app.get("/api/v1/learning/recommended")
def learning(user:User=Depends(current_user),db:Session=Depends(get_db)):
    comparison=spending_comparison(db,user); leading=next((x for x in comparison["categories"] if x["difference"]>0),None)
    trigger=f"{leading['category']} spending changed {leading['change_percent']:+.0f}% compared with the previous period." if leading and leading["change_percent"] is not None else "Your calculated spending varies from week to week."
    return {"lessons":[{"id":"weekly-budget","title":"Why weekly limits can be easier than monthly budgets","trigger_reason":trigger,"duration_minutes":2,"content":"Monthly numbers are hard to feel day to day. A weekly target can make changes easier to notice.","action":"Try a weekly category target."},{"id":"buffer","title":"Why a small emergency buffer matters","trigger_reason":f"Your forecast confidence is {money_runway(db,user)['confidence']}.","duration_minutes":2,"content":"A buffer can absorb ordinary timing differences between income and expenses.","action":"Review your safe-to-save range first."}]}
@app.post("/api/v1/learning/{lesson_id}/complete")
def lesson_complete(lesson_id:str,user:User=Depends(current_user)):return {"lesson_id":lesson_id,"completed":True}
@app.get("/api/v1/offers/recommended")
def offers(user:User=Depends(current_user),db:Session=Depends(get_db)):
    now,start,_=period_bounds(); rows=list(db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.timestamp>=start,Transaction.category=="Groceries")).all()); purchases=[t for t in rows if is_spending(t)]; typical=sum((dec(t.amount) for t in purchases),dec(0))/max(1,len(purchases)); saving=typical*dec("0.10")
    items=[] if not purchases else [{"id":"groceries-weekend","merchant":"Shwapno","category":"Groceries","title":"10% grocery offer","terms":"Concept upay offer; minimum spend ৳800.","typical_purchase":amount(typical),"potential_saving":amount(saving),"purchase_count":len(purchases),"why":f"You made {len(purchases)} grocery purchases in the last 30 days."}]
    return {"opt_in":True,"offers":items,"disclaimer":"If you were already planning this purchase, the offer may reduce the cost."}
@app.patch("/api/v1/offers/preferences")
def offers_pref(enabled:bool=True,user:User=Depends(current_user)):return {"personalized_offers_enabled":enabled}

# === NEW AI FINANCIAL COACH ENDPOINTS ===

@app.post("/api/v1/coach/parse-intent")
async def coach_parse_intent(body:IntentIn,user:User=Depends(current_user)):
    """Parse user message into structured intent using deterministic fallback."""
    from app.services.intent_service import parse_intent
    intent = parse_intent(body.question)
    return {"intent":intent.intent,"recipient_query":intent.recipient_query,"amount":intent.amount,"currency":intent.currency,"confidence":intent.confidence,"language":intent.language}

@app.get("/api/v1/trusted-contacts")
def trusted_contacts(user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import get_trusted_contacts
    from app.services.relationship_service import classify_relationship
    contacts = get_trusted_contacts(db, user.id)
    items=[]
    for c in contacts:
        history=classify_relationship(db,user.id,c,c.name)
        trust_label = "Trusted" if c.is_trusted else ("Known" if history.previous_transaction_count else "Needs verification")
        items.append({"id":c.id,"name":c.name,"phone_number":c.phone_number,"relationship":c.relationship,"nickname":c.nickname,"is_trusted":c.is_trusted,"trust_label":trust_label,"last_transfer_amount":history.last_transaction_amount,"last_transfer_date":history.last_transaction_date})
    return {"items":items}

@app.post("/api/v1/trusted-contacts")
def create_trusted_contact(body:TrustedContactIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import add_trusted_contact
    contact = add_trusted_contact(db, user.id, body.name, body.phone_number, body.relationship, body.nickname, body.is_trusted)
    return {"id":contact.id,"name":contact.name,"phone_number":contact.phone_number,"relationship":contact.relationship,"nickname":contact.nickname,"is_trusted":contact.is_trusted}

@app.delete("/api/v1/trusted-contacts/{contact_id}")
def delete_trusted_contact(contact_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.recipient_service import remove_trusted_contact
    if remove_trusted_contact(db, contact_id, user.id):
        return {"deleted":True}
    raise HTTPException(404,"Contact not found")

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
    recipient_id:int|None=None,
    recipient_name:str="",
    recipient_phone:str|None=None,
    amount:float=0,
    reference:str|None=None,
    user:User=Depends(current_user),
    db:Session=Depends(get_db)
):
    from app.services.transaction_draft_service import create_draft, get_draft_summary
    from app.services.relationship_service import classify_relationship
    from app.services.safe_to_spend_service import calculate_safe_to_spend
    from app.services.recipient_service import get_trusted_contacts

    if amount <= 0:
        raise HTTPException(400,"Amount must be greater than zero")

    contacts = get_trusted_contacts(db, user.id)
    contact = next((c for c in contacts if c.id == recipient_id), None) if recipient_id else None
    rel_info = classify_relationship(db, user.id, contact, recipient_name, amount)
    safe_before = calculate_safe_to_spend(db, user)
    draft = create_draft(db, user.id, recipient_id, recipient_name, recipient_phone, amount, reference)
    return get_draft_summary(db, draft, user, rel_info, safe_before)

@app.get("/api/v1/transactions/draft/active")
def get_active_draft(user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.transaction_draft_service import get_active_draft, get_draft_summary
    from app.services.safe_to_spend_service import calculate_safe_to_spend
    from app.services.relationship_service import classify_relationship
    draft = get_active_draft(db, user.id)
    if not draft:
        return {"has_active_draft":False}
    from app.models import TrustedContact
    contact = db.get(TrustedContact, draft.recipient_id) if draft.recipient_id else None
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
    from app.services.trusted_helper_service import get_trusted_helpers
    helpers = get_trusted_helpers(db, user.id)
    return {"items":[{"id":h.id,"helper_name":h.helper_name,"relationship":h.relationship,"phone":h.phone,"can_view_pending_transaction":h.can_view_pending_transaction,"can_receive_alerts":h.can_receive_alerts,"can_view_balance":h.can_view_balance,"can_view_history":h.can_view_history,"can_initiate":h.can_initiate} for h in helpers]}

@app.post("/api/v1/trusted-helpers")
def create_trusted_helper(body:TrustedHelperIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.trusted_helper_service import add_trusted_helper
    helper = add_trusted_helper(db, user.id, body.helper_name, body.relationship, body.phone, body.can_view_pending_transaction, body.can_receive_alerts, body.can_view_balance, body.can_view_history, body.can_initiate)
    return {"id":helper.id,"helper_name":helper.helper_name,"relationship":helper.relationship,"phone":helper.phone,"can_view_pending_transaction":helper.can_view_pending_transaction,"can_receive_alerts":helper.can_receive_alerts,"can_view_balance":helper.can_view_balance,"can_view_history":helper.can_view_history,"can_initiate":helper.can_initiate}

@app.delete("/api/v1/trusted-helpers/{helper_id}")
def delete_trusted_helper(helper_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.trusted_helper_service import remove_trusted_helper
    if remove_trusted_helper(db, helper_id, user.id):
        return {"deleted":True}
    raise HTTPException(404,"Helper not found")

@app.post("/api/v1/trusted-helper/request")
def create_helper_request(body:HelperRequestIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from app.services.trusted_helper_service import create_helper_request as _create_request
    request = _create_request(db, user.id, body.helper_id, body.message)
    return {"request_id":request.id,"status":request.status,"message":request.message,"created_at":request.created_at.isoformat()}
