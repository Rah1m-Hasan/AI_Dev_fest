"""Deterministic, consent-safe synthetic Bangladeshi MFS demo data generator."""
import random
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User,Account,Transaction,Budget,SavingsGoal,Notification

MERCHANTS={"Food":["Bhojon Express","Cafe Dhaka","Pathao Food"],"Groceries":["Shwapno","Meena Bazar","Agora"],"Transport":["Pathao","Uber","Metro Rail"],"Bills":["DESCO","WASA","BTCL"],"Mobile Recharge":["Grameenphone","Robi"],"Entertainment":["Star Cineplex","Bioscope"],"Shopping":["Daraz","Aarong"],"Education":["DIU Fees","Bookworm"],"Healthcare":["Popular Diagnostic","Pharmacy"],"Subscriptions":["Spotify","Google One"],"Cash Out":["Agent Cash Out"]}
PERSONAS=[("demo.student@upay.local","Arif Rahman","student",12000,10500),("demo.salary@upay.local","Nadia Islam","salaried worker",38000,22000),("demo.freelancer@upay.local","Samiha Noor","freelancer",30000,15000),("demo.business@upay.local","Rafi Ahmed","small business owner",52000,30000)]
def seed(db:Session):
    if db.scalar(select(User.id).limit(1)): return
    random.seed(2026); now=datetime.now()
    for email,name,persona,income,starting in PERSONAS:
        u=User(email=email,display_name=name,persona=persona); db.add(u);db.flush(); balance=float(starting)
        account=Account(user_id=u.id,balance=balance); db.add(account)
        for day_back in range(90,0,-1):
            d=now-timedelta(days=day_back)
            # regular income
            if d.day in (1,2) and (persona != "freelancer" or random.random()>.35):
                amount=income if persona!="freelancer" else random.randint(10000,22000); before=balance;balance+=amount
                db.add(Transaction(user_id=u.id,merchant_name="Salary / Client payment",category="Income",amount=amount,direction="income",transaction_type="salary",timestamp=d.replace(hour=10),balance_before=before,balance_after=balance,description="Synthetic demo income"))
            # student has intentional late month pressure + rising food spend in current month
            categories=["Food","Food","Groceries","Transport","Mobile Recharge","Bills","Entertainment","Shopping"]
            if d.weekday()>=5: categories += ["Food","Entertainment"]
            for _ in range(random.randint(0,2)):
                cat=random.choice(categories); base={"Food":210,"Groceries":900,"Transport":130,"Mobile Recharge":250,"Bills":700,"Entertainment":500,"Shopping":1200}[cat]
                multiplier=1.35 if (persona=="student" and d.month==now.month and cat in {"Food","Transport"}) else 1
                amount=round(random.uniform(.65,1.35)*base*multiplier,2); before=balance; balance-=amount
                db.add(Transaction(user_id=u.id,merchant_name=random.choice(MERCHANTS[cat]),category=cat,amount=amount,direction="expense",transaction_type="merchant_payment",timestamp=d.replace(hour=random.randint(8,22),minute=random.randint(0,59)),balance_before=before,balance_after=balance,description="Synthetic demo transaction"))
            if d.day in (5,20):
                cat="Subscriptions";amount=199 if d.day==5 else 120;before=balance;balance-=amount
                db.add(Transaction(user_id=u.id,merchant_name=random.choice(MERCHANTS[cat]),category=cat,amount=amount,direction="expense",transaction_type="subscription",timestamp=d.replace(hour=9),balance_before=before,balance_after=balance,is_recurring=True,description="Synthetic recurring payment"))
            if d.day==10:
                amount=850 if persona=="student" else 1600;before=balance;balance-=amount
                db.add(Transaction(user_id=u.id,merchant_name="DESCO",category="Bills",amount=amount,direction="expense",transaction_type="bill_payment",timestamp=d.replace(hour=11),balance_before=before,balance_after=balance,is_recurring=True,description="Synthetic utility bill"))
        account.balance=round(max(300,balance),2)
        start=now.replace(day=1).date(); db.add(Budget(user_id=u.id,total_limit=income*.72, start_date=start,end_date=(start+timedelta(days=31)).replace(day=1)-timedelta(days=1),categories={"Food":income*.16,"Transport":income*.09,"Groceries":income*.14,"Bills":income*.1,"Entertainment":income*.06}))
        db.add(SavingsGoal(user_id=u.id,name="Laptop Fund" if persona=="student" else "Emergency buffer",target_amount=30000 if persona=="student" else 50000,current_amount=5000 if persona=="student" else 12000,target_date=date.today()+timedelta(days=180)))
        db.add(Notification(user_id=u.id,title="Synthetic demo data",body="This prototype uses generated transactions, not production upay data.",severity="info"))
    db.commit()
