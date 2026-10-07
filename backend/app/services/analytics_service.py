"""Deterministic financial calculations. No LLM is used for accounting."""
from collections import defaultdict
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from statistics import pstdev
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Transaction, User, Budget, SavingsGoal, GoalPlanSettings

TRANSFER_TYPES = {"transfer", "internal_transfer"}
ESSENTIAL_CATEGORIES = {"Bills", "Rent", "Groceries", "Transport", "Healthcare", "Education", "Mobile Recharge"}
FIXED_CATEGORIES = {"Bills", "Rent", "Subscriptions", "Mobile Recharge"}
ZERO = Decimal("0")

def dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))

def amount(value):
    return float(dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def is_income(t):
    return t.direction == "income" and t.transaction_type not in TRANSFER_TYPES

def is_spending(t):
    # Internal transfers change wallet location, not a user's spending total.
    return t.direction in {"expense", "out"} and t.transaction_type not in TRANSFER_TYPES and t.category != "Transfers"

def _tx(db: Session, user_id: int, start: datetime, end: datetime):
    return list(db.scalars(select(Transaction).where(Transaction.user_id == user_id, Transaction.timestamp >= start, Transaction.timestamp < end).order_by(Transaction.timestamp)).all())

def _money(txs, incoming: bool):
    predicate = is_income if incoming else is_spending
    return sum((dec(t.amount) for t in txs if predicate(t)), ZERO)

def period_bounds(period="month"):
    now = datetime.now()
    # Rolling equal windows prevent a two-day month-to-date being compared with a
    # full prior month, and keep the synthetic demo meaningful every day.
    start = now - timedelta(days=7 if period == "week" else 30)
    previous = start - timedelta(days=7 if period == "week" else 30)
    return now, start, previous
def spending_summary(db: Session, user_id: int, period="month"):
    now, start, previous = period_bounds(period)
    current, old = _tx(db,user_id,start,now), _tx(db,user_id,previous,start)
    by_cat, old_cat, merchants = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    for t in current:
        if is_spending(t): by_cat[t.category] += dec(t.amount); merchants[t.merchant_name] += dec(t.amount)
    for t in old:
        if is_spending(t): old_cat[t.category] += dec(t.amount)
    total = sum(by_cat.values(), ZERO)
    categories = [{"category": k, "amount": amount(v), "percentage": round(float(v/total*100),1) if total else 0,
                   "previous_amount": amount(old_cat[k]), "change_percent": round(float((v-old_cat[k])/old_cat[k]*100),1) if old_cat[k] else None} for k,v in sorted(by_cat.items(), key=lambda x:x[1], reverse=True)]
    growth = max(categories, key=lambda x: x["change_percent"] if x["change_percent"] is not None else -999, default=None)
    recurring = [t for t in current if t.is_recurring and is_spending(t)]
    expense_rows = [t for t in current if is_spending(t)]
    average = total / len(expense_rows) if expense_rows else ZERO
    unusual = [t for t in expense_rows if dec(t.amount) > max(Decimal("1000"), average*2)]
    return {"period":"last_7_days" if period == "week" else "last_30_days","data_period":{"start":start.date().isoformat(),"end":now.date().isoformat()},"total_spending":amount(total),"category_totals":categories,
      "biggest_category":categories[0]["category"] if categories else None,"fastest_growing_category":growth["category"] if growth else None,
      "frequent_merchants":[{"merchant":k,"amount":amount(v)} for k,v in sorted(merchants.items(),key=lambda x:x[1],reverse=True)[:5]],
      "recurring_expenses":amount(sum((dec(t.amount) for t in recurring), ZERO)),"unusual_expenses":[{"merchant":t.merchant_name,"amount":amount(t.amount),"date":t.timestamp.date().isoformat()} for t in unusual[:5]],"source":"calculated_from_synthetic_demo_transactions"}

def health_score(db: Session, user: User):
    now,start,_=period_bounds(); txs=_tx(db,user.id,start,now); income=_money(txs,True); spend=_money(txs,False)
    budget=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active").order_by(Budget.id.desc())).first()
    savings=max(ZERO,income-spend); ratio=savings/income if income else ZERO
    saving=min(Decimal("30"), ratio/Decimal("0.20")*Decimal("30"))
    weeks=[float(_money([t for t in txs if start+timedelta(days=i*7)<=t.timestamp<min(now,start+timedelta(days=(i+1)*7))],False)) for i in range(4)]
    mean=sum(weeks)/len(weeks) if weeks else 0; variation=pstdev(weeks)/mean if mean else 1
    stability=Decimal(str(max(0,min(20,20*(1-variation)))))
    utilization=spend/max(dec(budget.total_limit),Decimal("1")) if budget else None
    budget_score=Decimal("12.5") if utilization is None else (Decimal("25") if utilization<=Decimal("0.8") else max(ZERO,Decimal("25")-(utilization-Decimal("0.8"))*Decimal("62.5")))
    buffer=min(Decimal("15"),dec(user.account.balance)/max(spend/Decimal("4"),Decimal("1"))/Decimal("4")*Decimal("15"))
    recurring=max(ZERO,min(Decimal("10"),Decimal("10")-sum((dec(t.amount) for t in txs if t.is_recurring and is_spending(t)),ZERO)/max(income,Decimal("1"))*Decimal("25")))
    score=min(Decimal("100"),max(ZERO,saving+stability+budget_score+buffer+recurring))
    return {"score":round(float(score)),"label":"Stable" if score>=70 else "Needs attention" if score>=45 else "Build a buffer","disclaimer":"Informational only — not a credit score.","components":[{"name":"Saving behavior","score":round(float(saving),1),"max":30},{"name":"Cash-flow stability","score":round(float(stability),1),"max":20},{"name":"Budget adherence","score":round(float(budget_score),1),"max":25},{"name":"Liquidity buffer","score":round(float(buffer),1),"max":15},{"name":"Recurring expense management","score":round(float(recurring),1),"max":10}],"what_improved":"Positive cash flow supports saving behavior." if savings>0 else "Recent spending is using all or more of this period's income.","actions":["Set a small weekly savings target", "Review recurring payments before month-end"],"source":"deterministic_calculation"}

def budget_recommendation(db: Session,user:User):
    now=datetime.now(); history=_tx(db,user.id,now-timedelta(days=60),now)
    income=_money(history,True)/Decimal("2"); spend_by=defaultdict(lambda: ZERO)
    for t in history:
        if is_spending(t): spend_by[t.category]+=dec(t.amount)/Decimal("2")
    historical=sum(spend_by.values(),ZERO); fixed=sum((v for k,v in spend_by.items() if k in FIXED_CATEGORIES),ZERO)
    free=max(ZERO,income-historical)
    income_windows=[float(_money(_tx(db,user.id,now-timedelta(days=30*i),now-timedelta(days=30*(i-1))),True)) for i in (1,2)]
    variable=user.persona=="freelancer" or (pstdev(income_windows)/(sum(income_windows)/2) if sum(income_windows) else 1)>0.25
    savings=min(income*(Decimal("0.10") if variable else Decimal("0.15")),free*Decimal("0.65"))
    buffer=min(income*Decimal("0.10"),max(ZERO,free-savings)*Decimal("0.25")); spendable=max(ZERO,income-savings-buffer)
    limits={k:amount(spendable*v/historical) for k,v in spend_by.items()} if historical else {"Essential spending":amount(spendable)}
    if limits and historical:
        largest=max(limits,key=limits.get); limits[largest]=amount(dec(limits[largest])+spendable-sum((dec(v) for v in limits.values()),ZERO))
    total=sum((dec(v) for v in limits.values()),ZERO); essential=sum((dec(v) for k,v in limits.items() if k in ESSENTIAL_CATEGORIES),ZERO)
    return {"recommended_total_spending":amount(total),"essential_budget":amount(essential),"flexible_budget":amount(max(ZERO,total-essential)),"savings_target":amount(savings),"category_limits":limits,"buffer_contribution":amount(buffer),"emergency_buffer":amount(max(Decimal("1000"),income*Decimal("0.1"))),"income_stability":"variable" if variable else "steady","confidence":"medium" if len(history)>=15 else "low","reasoning":"Based on recent income, recurring essentials, observed spending, available buffer, and income stability — not a generic budget rule.","period_income":amount(income),"fixed_recurring_costs":amount(fixed),"allocation_check":{"income":amount(income),"spending":amount(total),"savings":amount(savings),"buffer":amount(buffer)}}

def goal_plan(db:Session,user:User,goal:SavingsGoal, *, target_amount=None, target_date=None, planned_monthly_amount=None):
    """Return an explainable plan. This never transfers money or changes the wallet."""
    target_amount = dec(target_amount if target_amount is not None else goal.target_amount)
    target_date = target_date or goal.target_date
    remaining=max(ZERO,target_amount-dec(goal.current_amount)); days=(target_date-date.today()).days
    settings = db.scalar(select(GoalPlanSettings).where(GoalPlanSettings.goal_id == goal.id))
    saved_plan = dec(settings.planned_monthly_amount) if settings and settings.planned_monthly_amount else None
    selected_plan = dec(planned_monthly_amount) if planned_monthly_amount is not None else saved_plan
    if goal.status == "paused":
        return {"goal_id":goal.id,"remaining_amount":amount(remaining),"days_remaining":max(0,days),"recommended_weekly_contribution":0,"recommended_monthly_contribution":0,"comfortable_weekly_low":0,"comfortable_weekly_high":0,"selected_monthly_contribution":amount(selected_plan) if selected_plan else None,"feasible":False,"status":"paused","projected_completion_date":None,"alternatives":[],"basis":"This goal is paused. Resume it when you are ready to set a saving pace."}
    if remaining==ZERO:
        return {"goal_id":goal.id,"remaining_amount":0,"days_remaining":max(0,days),"recommended_weekly_contribution":0,"recommended_monthly_contribution":0,"comfortable_weekly_low":0,"comfortable_weekly_high":0,"selected_monthly_contribution":amount(selected_plan) if selected_plan else None,"feasible":True,"status":"completed","projected_completion_date":date.today().isoformat(),"alternatives":[],"basis":"Goal amount is already funded."}
    if days<=0:
        return {"goal_id":goal.id,"remaining_amount":amount(remaining),"days_remaining":0,"recommended_weekly_contribution":0,"recommended_monthly_contribution":0,"comfortable_weekly_low":0,"comfortable_weekly_high":0,"selected_monthly_contribution":amount(selected_plan) if selected_plan else None,"feasible":False,"status":"deadline_passed","projected_completion_date":None,"alternatives":["Extend the deadline","Lower the target","Review discretionary spending"],"basis":"The target date has passed."}
    rec_month=remaining/(Decimal(days)/Decimal("30.44")); rec_week=remaining/(Decimal(days)/Decimal("7")); rec=budget_recommendation(db,user)
    available=dec(rec["savings_target"]); feasible=available>ZERO and rec_month<=available; gap=max(ZERO,rec_month-available)
    pace = selected_plan if selected_plan and selected_plan > ZERO else available
    completion = date.today() + timedelta(days=round(float(remaining / pace * Decimal("30.44")))) if pace > ZERO else None
    status = "on_track" if feasible else "needs_adjustment"
    return {"goal_id":goal.id,"remaining_amount":amount(remaining),"days_remaining":days,"recommended_weekly_contribution":amount(rec_week),"recommended_monthly_contribution":amount(rec_month),"comfortable_weekly_low":amount(max(ZERO, available * Decimal("0.75") / Decimal("4.345"))),"comfortable_weekly_high":amount(max(ZERO, available / Decimal("4.345"))),"selected_monthly_contribution":amount(selected_plan) if selected_plan else None,"feasible":feasible,"status":status,"projected_completion_date":completion.isoformat() if completion else None,"alternatives":[] if feasible else ["Extend the deadline",f"Reduce discretionary spending by about ৳{amount(gap):,.0f} monthly","Lower the target"],"basis":"Historical free cash flow and goal math; this does not create a transfer."}

def forecast(db:Session,user:User,days:int=30):
    days=max(7,min(30,days)); now=datetime.now(); history=_tx(db,user.id,now-timedelta(days=60),now)
    daily_exp=_money(history,False)/Decimal("60")
    income_rows=[t for t in history if is_income(t)]
    variable=user.persona in {"freelancer","small business owner"}
    next_income_date=None
    if variable:
        # Irregular income is deliberately discounted rather than assumed in full.
        expected_inc=_money(history,True)/Decimal("60")*Decimal(days)*Decimal("0.70")
    else:
        typical_income=sum((dec(t.amount) for t in income_rows),ZERO)/max(1,len(income_rows))
        next_income_date=(now.replace(day=1,hour=10,minute=0,second=0,microsecond=0)+timedelta(days=32)).replace(day=1)
        expected_inc=typical_income if (next_income_date.date()-now.date()).days<=days else ZERO
    recurring=[t for t in history if t.is_recurring and is_spending(t)]
    # The model is optional. When its artifact is unavailable, this remains the
    # original rolling deterministic estimate and every downstream feature works.
    forecast_source="deterministic_fallback"
    expected_exp=daily_exp*days
    try:
        from app.ml.model_service import get_model_service
        prediction=get_model_service().spending_prediction(history,current_balance=float(user.account.balance))
        if prediction:
            expected_exp=dec(prediction["predicted_7_day_spending"] if days==7 else prediction["predicted_30_day_spending"]*days/30)
            forecast_source="ml"
    except Exception:
        pass
    closing=dec(user.account.balance)+expected_inc-expected_exp
    upcoming=[]
    seen=set()
    for t in recurring:
        key=(t.merchant_name,dec(t.amount))
        if key not in seen:
            next_date=now.replace(day=min(t.timestamp.day,28),hour=9,minute=0,second=0,microsecond=0)
            if next_date<=now: next_date=(next_date.replace(day=1)+timedelta(days=32)).replace(day=min(t.timestamp.day,28))
            in_days=(next_date.date()-now.date()).days
            if 0<in_days<=days: upcoming.append({"merchant":t.merchant_name,"amount":amount(t.amount),"expected_in_days":in_days,"expected_date":next_date.date().isoformat()})
            seen.add(key)
    # ``history`` already contains the entire 60-day window. Re-querying the
    # database once per day made one dashboard request issue hundreds of SQL
    # statements through its nested calculations, which left the web UI in its
    # loading state on a remote serverless database. Keep the same windows but
    # calculate them in memory from that single result set.
    daily_values = []
    for i in range(60):
        day_start = now - timedelta(days=i + 1)
        day_end = now - timedelta(days=i)
        daily_values.append(float(_money(
            (row for row in history if day_start <= row.timestamp < day_end),
            False,
        )))
    mean=sum(daily_values)/60; variation=pstdev(daily_values)/mean if mean else 1; factor=min(Decimal("0.35"),max(Decimal("0.15"),Decimal(str(variation))))
    return {"days":days,"expected_income":amount(expected_inc),"expected_income_date":next_income_date.date().isoformat() if next_income_date and expected_inc else None,"expected_expenses":amount(expected_exp),"expected_closing_balance":amount(closing),"predicted_recurring_expenses":sorted(upcoming,key=lambda x:x["expected_in_days"])[:5],"risk_of_low_balance":"important" if closing<Decimal("1000") else "attention" if closing<Decimal("3000") else "info","confidence":"low" if variation>1 or variable else "medium" if variation>.45 else "high","confidence_range":{"low":amount(expected_exp*(Decimal("1")-factor)),"high":amount(expected_exp*(Decimal("1")+factor))},"explanation":"ML-enhanced spending estimate when a trained local model is available; otherwise rolling 60-day spending averages and observed recurring-payment timing.","historical":False,"source":forecast_source}

def run_out_analysis(db:Session,user:User):
    now,start,prev=period_bounds(); cur,old=_tx(db,user.id,start,now),_tx(db,user.id,prev,start)
    spend=spending_summary(db,user.id); current_exp=_money(cur,False); old_exp=_money(old,False); income=_money(cur,True)
    starting=dec(cur[0].balance_before) if cur else dec(user.account.balance); weekly=defaultdict(lambda: ZERO)
    for t in cur:
        if is_spending(t): weekly[min(5,(t.timestamp-start).days//7+1)]+=dec(t.amount)
    critical=max(weekly,key=weekly.get) if weekly else None
    largest=max((t for t in cur if is_spending(t)),key=lambda t:dec(t.amount),default=None)
    changed=next((c for c in spend["category_totals"] if c["category"]==spend["fastest_growing_category"]),None)
    return {"period":{"start":start.date().isoformat(),"end":now.date().isoformat(),"days":30},"transactions_analyzed":len(cur),"starting_balance":amount(starting),"total_income":amount(income),"total_expense":amount(current_exp),"net_cashflow":amount(income-current_exp),"previous_period_expense":amount(old_exp),"expense_change_percent":round(float((current_exp-old_exp)/old_exp*100),1) if old_exp else None,"largest_category_increase":{"category":changed["category"],"current":changed["amount"],"previous":changed["previous_amount"],"change_percent":changed["change_percent"]} if changed else None,"highest_spend_week":{"week":critical,"amount":amount(weekly[critical])} if critical else None,"large_transactions":[{"merchant":largest.merchant_name,"amount":amount(largest.amount),"date":largest.timestamp.date().isoformat(),"category":largest.category}] if largest else [],"recurring_expenses":spend["recurring_expenses"],"unusual_spending":spend["unusual_expenses"],"week_by_week":[{"week":k,"expense":amount(v)} for k,v in sorted(weekly.items())],"evidence_source":"calculated transaction records only"}


def spending_comparison(db: Session, user: User):
    """An explicit current-versus-previous-window comparison for UI and coach tools."""
    summary = spending_summary(db, user.id)
    changes = []
    for category in summary["category_totals"]:
        current, previous = dec(category["amount"]), dec(category["previous_amount"])
        difference = current - previous
        changes.append({
            "category": category["category"],
            "current": amount(current),
            "previous": amount(previous),
            "difference": amount(difference),
            "change_percent": category["change_percent"],
            "direction": "up" if difference > 0 else "down" if difference < 0 else "flat",
        })
    changes.sort(key=lambda item: abs(item["difference"]), reverse=True)
    leading = next((x for x in changes if x["difference"] > 0), None)
    summary_text = (
        f"Most additional spending came from {leading['category']}, rather than a general rise across every category."
        if leading else "There was no material category increase in the current comparison window."
    )
    return {"period": summary["data_period"], "categories": changes, "summary": summary_text,
            "source": "calculated current and previous 30-day transaction windows"}


def safe_to_save(db: Session, user: User, days: int = 7):
    """Conservative, non-transfer allocation guidance. It never moves money."""
    days = max(1, min(30, days))
    fc = forecast(db, user, days)
    rec = budget_recommendation(db, user)
    safety_buffer = max(dec(rec["emergency_buffer"]), dec(user.account.balance) * Decimal("0.08"))
    available = dec(user.account.balance)
    expected_bills = sum((dec(x["amount"]) for x in fc["predicted_recurring_expenses"]), ZERO)
    # The rolling forecast already contains recurring history. Remove the known
    # upcoming bills from that estimate before presenting them as a separate
    # explainable line item, otherwise they would be counted twice.
    typical_spending = max(ZERO, dec(fc["expected_expenses"]) - expected_bills)
    liquidity_after_needs = max(ZERO, available + dec(fc["expected_income"]) - expected_bills - typical_spending - safety_buffer)
    # A large wallet balance is not the same as disposable cash flow. Cap the
    # period guidance at the savings capacity already derived by the budget
    # model, prorated to this horizon. This keeps the result conservative for
    # irregular income and for users whose recent spending consumed all income.
    disposable_cash_flow_cap = max(ZERO, dec(rec["savings_target"])) * Decimal(days) / Decimal("30.44")
    flexibility = min(liquidity_after_needs, disposable_cash_flow_cap)
    # Range intentionally communicates forecast uncertainty rather than a precise promise.
    low = (flexibility * Decimal("0.75")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    high = flexibility.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return {"period_days": days, "low": amount(low), "high": amount(high), "recommended": amount((low + high) / 2),
            "breakdown": {"available_balance": amount(available), "expected_income": fc["expected_income"],
                          "upcoming_bills": amount(expected_bills), "typical_spending": amount(typical_spending),
                          "safety_buffer": amount(safety_buffer), "liquidity_after_needs": amount(liquidity_after_needs),
                          "disposable_cash_flow_cap": amount(disposable_cash_flow_cap), "estimated_flexibility": amount(flexibility)},
            "label": "Demo allocation only — this does not move money.",
            "basis": "Available balance, rolling spending forecast, observed recurring payments, a safety buffer, and recent disposable cash flow."}


def money_runway(db: Session, user: User):
    fc = forecast(db, user, 30)
    fc14 = forecast(db, user, 14)
    daily_outflow = dec(fc["expected_expenses"]) / Decimal("30")
    buffer = max(Decimal("1000"), dec(user.account.balance) * Decimal("0.08"))
    now = datetime.now().date()
    history=_tx(db,user.id,datetime.now()-timedelta(days=60),datetime.now()); income_rows=[t for t in history if is_income(t)]
    typical_income=sum((dec(t.amount) for t in income_rows),ZERO)/max(1,len(income_rows)); variable=user.persona in {"freelancer","small business owner"}
    projected=dec(user.account.balance); days=90
    for offset in range(1,91):
        projected-=daily_outflow
        day=now+timedelta(days=offset)
        if not variable and day.day==1: projected+=typical_income
        elif variable: projected+=(_money(history,True)/Decimal("60"))*Decimal("0.70")
        if projected<buffer:
            days=offset-1; break
    fourteen_day_expenses = fc14["expected_expenses"]
    fourteen_day_income = fc14["expected_income"]
    fourteen_day_balance = amount(dec(user.account.balance) + dec(fourteen_day_income) - dec(fourteen_day_expenses))
    return {"days": days, "projected_until": (now + timedelta(days=days)).isoformat(), "today_balance": amount(user.account.balance),
            "expected_30_day_expenses": fc["expected_expenses"], "expected_30_day_income": fc["expected_income"],
            "expected_14_day_expenses": fourteen_day_expenses, "expected_14_day_income": fourteen_day_income,
            "expected_14_day_balance": fourteen_day_balance,
            "buffer": amount(buffer), "upcoming": fc["predicted_recurring_expenses"], "confidence": fc["confidence"],
            "label": "Forecast — based on recent spending pace and observed recurring expenses, not a guarantee."}


def money_story(db: Session, user: User):
    now, start, _ = period_bounds()
    rows = _tx(db, user.id, start, now)
    events = []
    for row in rows:
        if is_income(row):
            events.append({"date": row.timestamp.date().isoformat(), "type": "income", "title": "Income received", "detail": row.merchant_name, "amount": amount(row.amount)})
    unusual = spending_summary(db, user.id)["unusual_expenses"]
    for row in unusual[:3]:
        events.append({"date": row["date"], "type": "spike", "title": "A larger purchase stood out", "detail": row["merchant"], "amount": row["amount"]})
    for recurring in forecast(db, user, 14)["predicted_recurring_expenses"][:3]:
        events.append({"date": recurring["expected_date"], "type": "upcoming", "title": "Recurring payment expected", "detail": recurring["merchant"], "amount": recurring["amount"]})
    comparison = spending_comparison(db, user)
    leading = next((item for item in comparison["categories"] if item["difference"] > 0), None)
    if leading:
        events.append({"date": now.date().isoformat(), "type": "change", "title": f"{leading['category']} spending changed", "detail": f"{leading['change_percent']:+.0f}% compared with the prior 30 days" if leading["change_percent"] is not None else "Higher than the prior period", "amount": leading["difference"]})
    income = _money(rows, True); spending = _money(rows, False); net = income - spending
    events.append({"date": now.date().isoformat(), "type": "net", "title": "30-day net cash flow", "detail": "Income minus spending", "amount": amount(net)})
    events.sort(key=lambda item: item["date"])
    return {"period": {"start": start.date().isoformat(), "end": now.date().isoformat()}, "events": events[-7:],
            "today": {"date": now.date().isoformat(), "balance": amount(user.account.balance)},
            "source": "transaction events and observed recurring-payment timing"}


def money_pulse(db: Session, user: User):
    comparison = spending_comparison(db, user)
    runway = money_runway(db, user)
    safe = safe_to_save(db, user)
    growing = next((x for x in comparison["categories"] if x["difference"] > 0), None)
    if user.persona == "student":
        growing = next((x for x in comparison["categories"] if x["category"] in {"Food","Transport"} and x["difference"] > 0), growing)
    status = "Watch spending" if runway["days"] < 10 else "Tight" if runway["days"] < 20 else "Stable"
    if user.persona == "freelancer" and status == "Stable": status = "Watch spending"
    if user.persona == "student" and growing and growing["category"] in {"Food","Transport"} and status == "Stable": status = "Watch spending"
    why = []
    if growing: why.append({"label": f"{growing['category']} changed", "detail": f"{growing['change_percent']:+.0f}% vs. prior period" if growing["change_percent"] is not None else f"+৳{growing['difference']:,.0f}"})
    if runway["upcoming"]: why.append({"label": f"{len(runway['upcoming'])} recurring payment{'s' if len(runway['upcoming']) != 1 else ''} coming", "detail": f"৳{sum(x['amount'] for x in runway['upcoming']):,.0f} expected"})
    if user.persona == "freelancer":
        text = f"Your balance is healthy now, but irregular income makes the next few weeks less predictable. {growing['category'] + ' changed most this period.' if growing else ''}"
    elif user.persona == "student" and growing:
        text = f"Your month-end balance needs attention mainly because {growing['category']} increased. Your recent pace still leaves an estimated {runway['days']}-day runway."
    else:
        text = (f"Your spending is {status.lower()} overall. " +
                (f"{growing['category']} changed most in the current period, " if growing else "Your category mix has been fairly steady, ") +
                f"and your current balance may comfortably cover about {runway['days']} days at the recent pace.")
    next_step = (f"An estimated ৳{safe['low']:,.0f}–৳{safe['high']:,.0f} may be flexible this week while preserving the calculated buffer."
                 if safe["high"] > 0 else
                 "Recent cash flow does not show a comfortable amount to move into savings this week.")
    return {"status": status, "headline": text, "text": text, "drivers": comparison["categories"][:2], "why": why,
            "next": next_step,
            "money_runway_days": runway["days"], "runway_days": runway["days"], "confidence": runway["confidence"],
            "source": "deterministic transaction, forecast, and buffer calculations"}


def simulate_scenario(db: Session, user: User, kind: str, amount_value: Decimal, days: int = 30, *, category: str | None = None, event_date: date | None = None, description: str | None = None):
    """Build a deterministic, in-memory financial scenario.

    This deliberately only reads the account and transaction history.  The
    timeline is calculated from the same rolling spending and observed-income
    assumptions used by ``forecast``; nothing is added to the database.
    """
    from app.services.safe_to_spend_service import calculate_safe_to_spend

    amount_value = max(ZERO, dec(amount_value))
    days = max(7, min(90, days))
    now = datetime.now()
    history = _tx(db, user.id, now - timedelta(days=60), now)
    daily_spend = _money(history, False) / Decimal("60")
    income_rows = [row for row in history if is_income(row)]
    variable_income = user.persona in {"freelancer", "small business owner"}
    typical_income = sum((dec(row.amount) for row in income_rows), ZERO) / Decimal(max(1, len(income_rows)))
    variable_daily_income = _money(history, True) / Decimal("60") * Decimal("0.70")
    safe_before = calculate_safe_to_spend(db, user)
    runway_before = money_runway(db, user)
    monthly = spending_summary(db, user.id)
    active_budget = db.scalars(select(Budget).where(Budget.user_id == user.id, Budget.status == "active").order_by(Budget.id.desc())).first()
    active_goal = db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == user.id, SavingsGoal.status == "active").order_by(SavingsGoal.target_date)).first()
    goal_before = goal_plan(db, user, active_goal) if active_goal else None

    # A selected future date never changes the account today. Purchases dated
    # outside the chosen horizon are still represented as a planned event.
    scheduled_offset = 0
    if event_date and kind in {"purchase", "unexpected_expense", "save_more"}:
        scheduled_offset = max(0, (event_date - now.date()).days)

    def project(project_days: int, test_amount: Decimal = amount_value):
        """Return paired daily balances without mutating the user's state."""
        baseline = dec(user.account.balance)
        simulated = dec(user.account.balance)
        rows = []
        runway_day = project_days
        balance_runway_day = project_days
        buffer = max(Decimal("1000"), dec(user.account.balance) * Decimal("0.08"))
        for offset in range(0, project_days + 1):
            if offset:
                baseline -= daily_spend
                simulated -= daily_spend
                day = now.date() + timedelta(days=offset)
                if variable_income:
                    baseline += variable_daily_income
                    simulated += variable_daily_income
                elif day.day == 1:
                    baseline += typical_income
                    # A delayed salary appears later, rather than vanishing.
                    if kind == "income_delay":
                        # Do not add it yet. The matching delayed date below
                        # adds the same observed income back when in range.
                        pass
                    else:
                        simulated += typical_income
                if kind == "income_delay" and not variable_income:
                    # Income that was due on the first arrives after the chosen delay.
                    source_day = day - timedelta(days=int(test_amount))
                    if source_day.day == 1 and offset > int(test_amount):
                        simulated += typical_income
                if kind == "reduce_spending":
                    simulated += test_amount / Decimal("7")
            if kind in {"purchase", "unexpected_expense", "save_more"} and offset == scheduled_offset:
                simulated -= test_amount
            if offset and baseline < buffer and balance_runway_day == project_days:
                balance_runway_day = offset - 1
            if offset and simulated < buffer and runway_day == project_days:
                runway_day = offset - 1
            rows.append({"day": offset, "date": (now.date() + timedelta(days=offset)).isoformat(), "current_balance": amount(baseline), "scenario_balance": amount(simulated)})
        return rows, max(0, balance_runway_day), max(0, runway_day)

    timeline, baseline_runway, scenario_runway = project(days)
    # Runway is assessed on a wider horizon than the selected chart.
    _, baseline_runway_90, scenario_runway_90 = project(90)
    ending = timeline[-1]
    immediate_impact = amount_value if kind in {"purchase", "unexpected_expense", "save_more"} and scheduled_offset == 0 else ZERO
    if kind == "income_delay":
        immediate_impact = ZERO
    safe_after = max(ZERO, dec(safe_before["safe_to_spend"]) - immediate_impact)
    if kind == "reduce_spending":
        safe_after = dec(safe_before["safe_to_spend"]) + amount_value

    monthly_change = (
        amount_value if kind in {"purchase", "unexpected_expense"}
        else -amount_value * Decimal("30") / Decimal("7") if kind == "reduce_spending"
        else ZERO
    )
    monthly_before = dec(monthly["total_spending"])
    monthly_after = max(ZERO, monthly_before + monthly_change)
    budget_before = dec(active_budget.total_limit) - monthly_before if active_budget else None
    budget_after = budget_before - monthly_change if budget_before is not None else None

    # Goal math is a projection only.  A save-more scenario hypothetically
    # increases the goal fund; one-off costs reduce the available saving pace.
    goal_impact = None
    if active_goal and goal_before:
        goal_current = dec(active_goal.current_amount)
        goal_after_amount = min(dec(active_goal.target_amount), goal_current + amount_value) if kind == "save_more" else goal_current
        current_progress = float(goal_current / max(dec(active_goal.target_amount), Decimal("1")) * Decimal("100"))
        scenario_progress = float(goal_after_amount / max(dec(active_goal.target_amount), Decimal("1")) * Decimal("100"))
        baseline_pace = max(dec(goal_before["selected_monthly_contribution"] or 0), dec(goal_before["recommended_monthly_contribution"]), Decimal("1"))
        pace_change = amount_value if kind == "reduce_spending" else -amount_value if kind in {"purchase", "unexpected_expense", "save_more"} else ZERO
        scenario_pace = max(Decimal("1"), baseline_pace + pace_change)
        goal_remaining = max(ZERO, dec(active_goal.target_amount) - goal_after_amount)
        complete_after = date.today() + timedelta(days=round(float(goal_remaining / scenario_pace * Decimal("30.44"))))
        goal_impact = {
            "name": active_goal.name, "current_progress": round(current_progress, 1), "scenario_progress": round(scenario_progress, 1),
            "current_completion": goal_before.get("projected_completion_date"), "scenario_completion": complete_after.isoformat(),
            "outlook": "improved" if scenario_pace > baseline_pace or goal_after_amount > goal_current else "at_risk" if scenario_pace < baseline_pace else "unchanged",
        }

    balance_delta = dec(ending["scenario_balance"]) - dec(ending["current_balance"])
    balance_ratio = abs(balance_delta) / max(dec(user.account.balance), Decimal("1"))
    impact_level = "high" if safe_after == ZERO or scenario_runway_90 < max(7, runway_before["days"] * .55) or balance_ratio >= Decimal("0.45") else "moderate" if balance_ratio >= Decimal("0.15") or scenario_runway_90 < runway_before["days"] else "low"
    health_before = health_score(db, user)
    health_delta = min(Decimal("25"), balance_ratio * Decimal("30"))
    if kind == "reduce_spending": health_delta = -min(Decimal("12"), amount_value / max(monthly_before, Decimal("1")) * Decimal("12"))
    health_after = max(0, min(100, int(round(health_before["score"] - float(health_delta)))))
    label = {"purchase": "spend", "unexpected_expense": "cover an unexpected expense", "reduce_spending": "spend less", "save_more": "set aside more savings", "income_delay": "delay income"}.get(kind, "make this change")
    explanation = (
        f"If you {label} by ৳{amount_value:,.0f}, your estimated runway changes from {baseline_runway_90} days to {scenario_runway_90} days."
        if kind != "income_delay" else f"If income arrives {int(amount_value)} days later, the estimate tests whether your current money can cover the gap."
    )
    alternatives = []
    if kind in {"purchase", "unexpected_expense"}:
        for ratio, text in ((Decimal("0.67"), "Spend less instead"), (Decimal("0.8"), "Choose a lower-cost option")):
            alternative_amount = (amount_value * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            alt_timeline, _, alt_runway = project(90, alternative_amount)
            alternatives.append({"label": text, "amount": amount(alternative_amount), "runway_days": alt_runway, "projected_balance": alt_timeline[min(days, len(alt_timeline) - 1)]["scenario_balance"]})

    # Legacy summary fields remain for existing API consumers; the structured
    # snapshots above are the source used by the redesigned Scenario Lab.
    baseline_forecast = forecast(db, user, 30)
    legacy_projected = dec(baseline_forecast["expected_closing_balance"]) - monthly_change
    return {
        "kind": kind, "amount": amount(amount_value), "days": days, "category": category, "description": description,
        "projected_balance": amount(legacy_projected), "baseline_balance": baseline_forecast["expected_closing_balance"],
        "difference": amount(legacy_projected - dec(baseline_forecast["expected_closing_balance"])),
        "current": {"balance": amount(user.account.balance), "safe_to_spend": safe_before["safe_to_spend"], "runway_days": baseline_runway_90, "monthly_spending": amount(monthly_before), "health_score": health_before["score"]},
        "projected": {"balance": ending["scenario_balance"], "safe_to_spend": amount(safe_after), "runway_days": scenario_runway_90, "monthly_spending": amount(monthly_after), "health_score": health_after},
        "deltas": {"balance": amount(balance_delta), "safe_to_spend": amount(safe_after - dec(safe_before["safe_to_spend"])), "runway_days": scenario_runway_90 - baseline_runway_90, "monthly_spending": amount(monthly_after - monthly_before), "health_score": health_after - health_before["score"]},
        "timeline": timeline, "timeline_runway": {"current": baseline_runway, "scenario": scenario_runway},
        "goal_impact": goal_impact,
        "budget_impact": {"has_budget": bool(active_budget), "before_remaining": amount(budget_before) if budget_before is not None else None, "after_remaining": amount(budget_after) if budget_after is not None else None, "exceeded_by": amount(max(ZERO, -budget_after)) if budget_after is not None else None},
        "impact_level": impact_level, "explanation": explanation, "alternatives": alternatives,
        "warning": "You can still explore this scenario, but the hypothetical expense is greater than your currently available balance." if kind in {"purchase", "unexpected_expense"} and amount_value > dec(user.account.balance) else None,
        "disclaimer": "Simulation only — no changes will be made to your account.",
        "basis": "Deterministic projection from your current balance, rolling 60-day spending, observed income timing, budget, goal, and safe-to-spend calculations.",
    }
