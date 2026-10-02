"""Deterministic financial calculations. No LLM is used for accounting."""
from collections import defaultdict
from datetime import datetime, timedelta, date
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Transaction, User, Budget, SavingsGoal

EXPENSE_DIRECTIONS = {"expense", "out"}
def _tx(db: Session, user_id: int, start: datetime, end: datetime):
    return list(db.scalars(select(Transaction).where(Transaction.user_id == user_id, Transaction.timestamp >= start, Transaction.timestamp < end).order_by(Transaction.timestamp)).all())
def _money(txs, incoming: bool):
    return round(sum(t.amount for t in txs if (t.direction == "income") == incoming), 2)
def period_bounds(period="month"):
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) if period == "month" else now - timedelta(days=7)
    previous = start - (now - start)
    return now, start, previous
def spending_summary(db: Session, user_id: int, period="month"):
    now, start, previous = period_bounds(period)
    current, old = _tx(db,user_id,start,now), _tx(db,user_id,previous,start)
    by_cat, old_cat, merchants = defaultdict(float), defaultdict(float), defaultdict(float)
    for t in current:
        if t.direction == "expense": by_cat[t.category] += t.amount; merchants[t.merchant_name] += t.amount
    for t in old:
        if t.direction == "expense": old_cat[t.category] += t.amount
    total = sum(by_cat.values())
    categories = [{"category": k, "amount": round(v,2), "percentage": round(v/total*100,1) if total else 0,
                   "change_percent": round((v-old_cat[k])/old_cat[k]*100,1) if old_cat[k] else None} for k,v in sorted(by_cat.items(), key=lambda x:x[1], reverse=True)]
    growth = max(categories, key=lambda x: x["change_percent"] if x["change_percent"] is not None else -999, default=None)
    recurring = [t for t in current if t.is_recurring and t.direction == "expense"]
    unusual = [t for t in current if t.direction == "expense" and t.amount > max(1000, total/max(1,len(current))*2)]
    return {"period":period,"data_period":{"start":start.date().isoformat(),"end":now.date().isoformat()},"total_spending":round(total,2),"category_totals":categories,
      "biggest_category":categories[0]["category"] if categories else None,"fastest_growing_category":growth["category"] if growth else None,
      "frequent_merchants":[{"merchant":k,"amount":round(v,2)} for k,v in sorted(merchants.items(),key=lambda x:x[1],reverse=True)[:5]],
      "recurring_expenses":round(sum(t.amount for t in recurring),2),"unusual_expenses":[{"merchant":t.merchant_name,"amount":t.amount,"date":t.timestamp.date().isoformat()} for t in unusual[:5]],"source":"calculated_from_synthetic_demo_transactions"}

def health_score(db: Session, user: User):
    now,start,_=period_bounds(); txs=_tx(db,user.id,start,now); income=_money(txs,True); spend=_money(txs,False)
    budget=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active").order_by(Budget.id.desc())).first()
    savings=max(0,income-spend); ratio=savings/income if income else 0
    saving=round(min(30, max(0,ratio*120)),1); stability=round(max(0,20-min(20, spend/max(income,1)*14)),1)
    budget_score=round(25 if not budget else max(0,25*(1-spend/max(budget.total_limit,1)*.7)),1)
    buffer=round(min(15,user.account.balance/max(spend/4,1)*5),1); recurring=round(max(0,10-min(10,sum(t.amount for t in txs if t.is_recurring and t.direction=='expense')/max(income,1)*25)),1)
    score=round(saving+stability+budget_score+buffer+recurring)
    return {"score":score,"label":"Informational financial health — not a credit score","components":[{"name":"Saving consistency","score":saving,"max":30},{"name":"Spending stability","score":stability,"max":20},{"name":"Budget control","score":budget_score,"max":25},{"name":"Liquidity buffer","score":buffer,"max":15},{"name":"Recurring costs","score":recurring,"max":10}],"what_improved":"Positive monthly cash flow supports saving consistency." if savings>0 else "No positive cash flow was observed this period.","actions":["Set a small weekly savings transfer target", "Review recurring payments before month-end"],"source":"deterministic_calculation"}

def budget_recommendation(db: Session,user:User):
    now,start,prev=period_bounds(); current=_tx(db,user.id,start,now); history=_tx(db,user.id,prev,now)
    income=_money(history,True)/2; spend_by=defaultdict(float)
    for t in history:
        if t.direction=='expense': spend_by[t.category]+=t.amount/2
    fixed=sum(v for k,v in spend_by.items() if k in {"Bills","Rent","Subscriptions","Mobile Recharge"})
    free=max(0,income-sum(spend_by.values())); savings=round(max(300,min(income*.15,free*.65)),2)
    limits={k:round(v*1.03,2) for k,v in spend_by.items()}; total=round(max(sum(limits.values()), income-savings),2)
    return {"recommended_total_spending":total,"essential_budget":round(sum(v for k,v in limits.items() if k in {"Bills","Rent","Groceries","Transport","Healthcare","Education"}),2),"flexible_budget":round(sum(v for k,v in limits.items() if k not in {"Bills","Rent","Groceries","Transport","Healthcare","Education"}),2),"savings_target":savings,"category_limits":limits,"emergency_buffer":round(max(1000, income*.1),2),"confidence":"medium","reasoning":"Based on your recent income, recurring essentials, and observed category spending; it is not a generic budget rule.","period_income":round(income,2)}

def goal_plan(db:Session,user:User,goal:SavingsGoal):
    days=max(1,(goal.target_date-date.today()).days); months=max(1,days/30.44); remaining=max(0,goal.target_amount-goal.current_amount)
    rec_month=remaining/months; rec_week=remaining/(days/7); rec=budget_recommendation(db,user)
    feasible=rec_month <= rec["savings_target"]*1.15
    return {"goal_id":goal.id,"remaining_amount":round(remaining,2),"days_remaining":days,"recommended_weekly_contribution":round(rec_week,2),"recommended_monthly_contribution":round(rec_month,2),"feasible":feasible,"projected_completion_date":goal.target_date.isoformat() if feasible else None,"alternatives":[] if feasible else ["Extend the deadline",f"Reduce discretionary spending by about ৳{round(rec_month-rec['savings_target'],2)} monthly","Lower the target"],"basis":"historical free cash-flow and goal math"}

def forecast(db:Session,user:User,days:int=30):
    days=max(7,min(30,days)); now=datetime.now(); history=_tx(db,user.id,now-timedelta(days=60),now)
    daily_exp=sum(t.amount for t in history if t.direction=='expense')/60; daily_inc=sum(t.amount for t in history if t.direction=='income')/60
    recurring=[t for t in history if t.is_recurring and t.direction=='expense']
    expected_exp=round(daily_exp*days,2); expected_inc=round(daily_inc*days,2); closing=round(user.account.balance+expected_inc-expected_exp,2)
    upcoming=[]
    seen=set()
    for t in recurring:
        key=(t.merchant_name,t.amount)
        if key not in seen: upcoming.append({"merchant":t.merchant_name,"amount":t.amount,"expected_in_days":min(days, max(1,(t.timestamp.day-now.day)%30))});seen.add(key)
    return {"days":days,"expected_income":expected_inc,"expected_expenses":expected_exp,"expected_closing_balance":closing,"predicted_recurring_expenses":upcoming[:5],"risk_of_low_balance":"important" if closing<1000 else "attention" if closing<3000 else "info","confidence_range":{"low":round(expected_exp*.8,2),"high":round(expected_exp*1.2,2)},"explanation":"Rolling 60-day daily averages with detected recurring payments; this is a forecast, not an actual charge.","historical":False}

def run_out_analysis(db:Session,user:User):
    now,start,prev=period_bounds(); cur,old=_tx(db,user.id,start,now),_tx(db,user.id,prev,start)
    spend=spending_summary(db,user.id); current_exp=_money(cur,False); old_exp=_money(old,False); income=_money(cur,True)
    starting=cur[0].balance_before if cur else user.account.balance; weekly=defaultdict(float)
    for t in cur:
        if t.direction=='expense': weekly[(t.timestamp.day-1)//7+1]+=t.amount
    critical=max(weekly,key=weekly.get) if weekly else None
    largest=max((t for t in cur if t.direction=='expense'),key=lambda t:t.amount,default=None)
    return {"starting_balance":round(starting,2),"total_income":income,"total_expense":current_exp,"previous_period_expense":old_exp,"expense_change_percent":round((current_exp-old_exp)/old_exp*100,1) if old_exp else None,"largest_change":{"category":spend["fastest_growing_category"],"increase_percent":next((c["change_percent"] for c in spend["category_totals"] if c["category"]==spend["fastest_growing_category"]),None)},"largest_expense":largest.amount if largest else 0,"largest_expense_merchant":largest.merchant_name if largest else None,"critical_week":critical,"recurring_expenses":spend["recurring_expenses"],"week_by_week":[{"week":k,"expense":round(v,2)} for k,v in sorted(weekly.items())],"evidence_source":"calculated transaction records only"}
