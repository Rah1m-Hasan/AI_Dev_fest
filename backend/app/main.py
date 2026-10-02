from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from collections import defaultdict
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import Base,engine,get_db
from app.models import User,Transaction,Budget,SavingsGoal,Notification,CategoryFeedback
from app.schemas import LoginIn,BudgetIn,GoalIn,ChatIn,CategoryCorrection
from app.api.deps import current_user
from app.services.auth import create_token
from app.services.seed import seed
from app.services.analytics_service import spending_summary,health_score,budget_recommendation,goal_plan,forecast,run_out_analysis,period_bounds
from app.services.groq_service import explain

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    db=next(get_db()); seed(db); db.close(); yield
app=FastAPI(title="Upay AI Financial Coach",version="1.0.0",lifespan=lifespan,description="Synthetic-data concept prototype. Not an official upay service.")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

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
def me(user:User=Depends(current_user)): return {"id":user.id,"email":user.email,"display_name":user.display_name,"persona":user.persona,"preferred_language":user.preferred_language,"balance":user.account.balance}

@app.get("/api/v1/dashboard/summary")
def dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    now,start,_=period_bounds(); tx=list(db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.timestamp>=start).order_by(Transaction.timestamp.desc())).all())
    income=sum(t.amount for t in tx if t.direction=="income"); expense=sum(t.amount for t in tx if t.direction=="expense")
    sp=spending_summary(db,user.id); b=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active").order_by(Budget.id.desc())).first(); fc=forecast(db,user,14)
    weekly=defaultdict(float)
    for t in tx:
        if t.direction=="expense":weekly[f"W{(t.timestamp.day-1)//7+1}"]+=t.amount
    return {"disclaimer":"Concept prototype — synthetic demo data, not an official production upay service.","balance":user.account.balance,"this_month":{"income":round(income,2),"spending":round(expense,2),"savings":round(income-expense,2)},"budget":{"limit":b.total_limit if b else 0,"used":round(expense,2),"utilization":round(expense/b.total_limit*100,1) if b else 0},"health":health_score(db,user),"spending_breakdown":sp["category_totals"],"weekly_spend":[{"week":k,"amount":round(v,2)} for k,v in sorted(weekly.items())],"recent_transactions":[transaction_out(t) for t in tx[:6]],"ai_insight":{"title":"Calculated spending insight","text":f"{sp['biggest_category'] or 'No category'} is your largest spending category this period.","basis":"deterministic transaction aggregation"},"forecast":fc}

def transaction_out(t): return {"id":t.id,"merchant_name":t.merchant_name,"category":t.category,"amount":t.amount,"direction":t.direction,"transaction_type":t.transaction_type,"timestamp":t.timestamp.isoformat(),"is_recurring":t.is_recurring,"description":t.description,"source":t.source}
@app.get("/api/v1/transactions")
def transactions(category:str|None=None, direction:str|None=None, q:str|None=None,page:int=1,page_size:int=20,user:User=Depends(current_user),db:Session=Depends(get_db)):
    query=select(Transaction).where(Transaction.user_id==user.id)
    if category: query=query.where(Transaction.category==category)
    if direction: query=query.where(Transaction.direction==direction)
    if q: query=query.where(Transaction.merchant_name.ilike(f"%{q[:80]}%"))
    rows=list(db.scalars(query.order_by(Transaction.timestamp.desc()).offset((max(1,page)-1)*min(page_size,100)).limit(min(page_size,100))).all())
    return {"items":[transaction_out(t) for t in rows],"page":page,"page_size":min(page_size,100)}
@app.get("/api/v1/transactions/categories")
def categories(): return {"categories":["Food","Transport","Shopping","Bills","Education","Healthcare","Entertainment","Subscriptions","Groceries","Mobile Recharge","Cash Out","Transfers","Rent","Other"]}
@app.get("/api/v1/transactions/{transaction_id}")
def transaction(transaction_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(Transaction,transaction_id)
    if not t or t.user_id!=user.id: raise HTTPException(404,"Transaction not found")
    return transaction_out(t)
@app.patch("/api/v1/transactions/{transaction_id}/category")
def correct_category(transaction_id:int,body:CategoryCorrection,user:User=Depends(current_user),db:Session=Depends(get_db)):
    t=db.get(Transaction,transaction_id)
    if not t or t.user_id!=user.id: raise HTTPException(404,"Transaction not found")
    db.add(CategoryFeedback(transaction_id=t.id,user_id=user.id,old_category=t.category,new_category=body.category.strip()));t.category=body.category.strip();db.commit();return transaction_out(t)
@app.get("/api/v1/transactions/summary")
def tx_summary(user:User=Depends(current_user),db:Session=Depends(get_db)): return spending_summary(db,user.id)

@app.get("/api/v1/analytics/spending")
def spending(period:str="month",user:User=Depends(current_user),db:Session=Depends(get_db)): return spending_summary(db,user.id,period if period in {"month","week"} else "month")
@app.get("/api/v1/analytics/cashflow")
def cashflow(user:User=Depends(current_user),db:Session=Depends(get_db)):
    now,start,_=period_bounds(); rows=list(db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.timestamp>=start)).all());return {"income":sum(t.amount for t in rows if t.direction=='income'),"expense":sum(t.amount for t in rows if t.direction=='expense'),"net":sum(t.amount if t.direction=='income' else -t.amount for t in rows),"source":"calculated"}
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
    q=body.question.lower(); evidence=run_out_analysis(db,user) if any(x in q for x in ["low","run out","where","spend","খরচ","টাকা"]) else {"budget":budget_recommendation(db,user),"forecast":forecast(db,user,14),"health":health_score(db,user)}
    result=await explain("run_out" if "total_expense" in evidence else "chat",evidence,body.question,body.language)
    return {"answer":result,"intent":"spending_analysis" if "total_expense" in evidence else "financial_guidance","structured_context":evidence,"safety":"Informational guidance only; no transfers, lending, or financial eligibility decisions."}
@app.get("/api/v1/coach/insights")
def insights(user:User=Depends(current_user),db:Session=Depends(get_db)):
    s=spending_summary(db,user.id); return {"insights":[{"type":"spending","severity":"attention","observation":f"{s['biggest_category']} is your largest category this month.","evidence":{"total":s['total_spending']},"suggested_action":"Consider a weekly category target.","confidence":"high"},{"type":"recurring","severity":"info","observation":f"Recurring expenses total ৳{s['recurring_expenses']:,.0f}.","evidence":{"amount":s['recurring_expenses']},"suggested_action":"Review whether each recurring payment is still useful.","confidence":"high"}]}

@app.get("/api/v1/budgets/recommendation")
def budget_rec(user:User=Depends(current_user),db:Session=Depends(get_db)): return budget_recommendation(db,user)
@app.get("/api/v1/budgets/current")
def current_budget(user:User=Depends(current_user),db:Session=Depends(get_db)):
    b=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active").order_by(Budget.id.desc())).first()
    if not b:return None
    spend=spending_summary(db,user.id)["total_spending"];return {"id":b.id,"total_limit":b.total_limit,"categories":b.categories,"used":spend,"remaining":round(b.total_limit-spend,2),"status":b.status}
@app.post("/api/v1/budgets")
def create_budget(body:BudgetIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    db.query(Budget).filter(Budget.user_id==user.id,Budget.status=="active").update({"status":"replaced"}); start=date.today().replace(day=1);b=Budget(user_id=user.id,total_limit=body.total_limit,categories=body.categories,start_date=start,end_date=(start+timedelta(days=32)).replace(day=1)-timedelta(days=1));db.add(b);db.commit();db.refresh(b);return {"id":b.id,"total_limit":b.total_limit,"categories":b.categories}
@app.put("/api/v1/budgets/{budget_id}")
def update_budget(budget_id:int,body:BudgetIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    b=db.get(Budget,budget_id)
    if not b or b.user_id!=user.id:raise HTTPException(404,"Budget not found")
    b.total_limit=body.total_limit;b.categories=body.categories;db.commit();return {"id":b.id,"total_limit":b.total_limit,"categories":b.categories}

@app.get("/api/v1/goals")
def goals(user:User=Depends(current_user),db:Session=Depends(get_db)): return {"items":[{"id":g.id,"name":g.name,"target_amount":g.target_amount,"current_amount":g.current_amount,"target_date":g.target_date.isoformat(),"status":g.status,"progress_percent":round(g.current_amount/g.target_amount*100,1),"plan":goal_plan(db,user,g)} for g in user.goals]}
@app.post("/api/v1/goals")
def create_goal(body:GoalIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    g=SavingsGoal(user_id=user.id,name=body.goal_name.strip(),target_amount=body.target_amount,current_amount=body.optional_current_savings,target_date=body.deadline);db.add(g);db.commit();db.refresh(g);return {"id":g.id,"name":g.name,"plan":goal_plan(db,user,g)}
@app.get("/api/v1/goals/{goal_id}")
def get_goal(goal_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    g=db.get(SavingsGoal,goal_id)
    if not g or g.user_id!=user.id:raise HTTPException(404,"Goal not found")
    return {"id":g.id,"name":g.name,"target_amount":g.target_amount,"current_amount":g.current_amount,"target_date":g.target_date.isoformat(),"plan":goal_plan(db,user,g)}
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
    data=[{"id":"budget","severity":"attention" if b and spend/b.total_limit>.7 else "info","title":"Budget check","body":f"You have used {spend/b.total_limit*100:.0f}% of your monthly budget." if b else "Create a budget to receive progress alerts."}]
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
    sp=spending_summary(db,user.id,period);return {"period":period,"spending":sp,"health":health_score(db,user),"forecast":forecast(db,user,14),"observations":[f"{sp['biggest_category']} is the largest category.",f"Recurring costs total ৳{sp['recurring_expenses']:,.0f}.","Figures are calculated from synthetic demo data."],"ai_summary":{"provider":"deterministic","text":f"Your {period}ly expense total is ৳{sp['total_spending']:,.0f}. Review the category breakdown before making changes."}}
@app.get("/api/v1/learning/recommended")
def learning(user:User=Depends(current_user),db:Session=Depends(get_db)):return {"lessons":[{"id":"weekly-budget","title":"How weekly budgeting can help","trigger_reason":"Your calculated spending can vary week to week.","duration_minutes":3,"content":"A weekly target makes a monthly budget easier to notice and adjust.","action":"Try a weekly food target."},{"id":"buffer","title":"Why a small emergency buffer matters","trigger_reason":"Forecasts include uncertainty.","duration_minutes":2,"content":"A buffer can help absorb ordinary timing differences in expenses.","action":"Set aside a small optional amount."}]}
@app.post("/api/v1/learning/{lesson_id}/complete")
def lesson_complete(lesson_id:str,user:User=Depends(current_user)):return {"lesson_id":lesson_id,"completed":True}
@app.get("/api/v1/offers/recommended")
def offers(user:User=Depends(current_user),db:Session=Depends(get_db)):return {"opt_in":True,"offers":[{"id":"groceries-weekend","merchant":"Shwapno","category":"Groceries","title":"10% weekend groceries offer","terms":"Valid until Saturday; minimum spend ৳800.","why":"You have synthetic-demo grocery activity in this category. This is shown for relevance, not to encourage a new purchase."}]}
@app.patch("/api/v1/offers/preferences")
def offers_pref(enabled:bool=True,user:User=Depends(current_user)):return {"personalized_offers_enabled":enabled}
