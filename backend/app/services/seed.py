"""Deterministic, consent-safe synthetic Bangladeshi MFS demo data generator."""
import random
from decimal import Decimal
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User,Account,Transaction,Budget,SavingsGoal,Notification,TrustedContact,TrustedHelper

MERCHANTS={"Food":["Bhojon Express","Cafe Dhaka","Pathao Food"],"Groceries":["Shwapno","Meena Bazar","Agora"],"Transport":["Pathao","Uber","Metro Rail"],"Bills":["DESCO","WASA","BTCL"],"Mobile Recharge":["Grameenphone","Robi"],"Entertainment":["Star Cineplex","Bioscope"],"Shopping":["Daraz","Aarong"],"Education":["DIU Fees","Bookworm"],"Healthcare":["Popular Diagnostic","Pharmacy"],"Subscriptions":["Spotify","Google One"],"Cash Out":["Agent Cash Out"]}
PERSONAS=[("demo.student@upay.local","Arif Rahman","student",12000,10500),("demo.salary@upay.local","Nadia Islam","salaried worker",38000,22000),("demo.freelancer@upay.local","Samiha Noor","freelancer",30000,15000),("demo.business@upay.local","Rafi Ahmed","small business owner",52000,30000)]
def seed(db:Session):
    existing_users = list(db.scalars(select(User)))
    if existing_users:
        # Existing developer databases may predate the human-centered payment
        # entities. Backfill only the safe, synthetic demo contacts needed by
        # the UI; never rewrite accounts or transaction history.
        for user in existing_users:
            # Keep the showcase contact consistent with the documented demo
            # story. This touches synthetic contact metadata only.
            rafi = db.scalar(select(TrustedContact).where(TrustedContact.user_id == user.id, TrustedContact.name == "Rafi Ahmed"))
            if rafi and rafi.relationship == "Son":
                rafi.relationship = "Brother"
            if not db.scalar(select(TrustedContact.id).where(TrustedContact.user_id == user.id).limit(1)):
                if user.persona == "student":
                    db.add_all([
                        TrustedContact(user_id=user.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi",is_trusted=True),
                        TrustedContact(user_id=user.id,name="Mim Akter",phone_number="01812345678",relationship="Daughter",nickname="Mim",is_trusted=True),
                        TrustedContact(user_id=user.id,name="Rahman",phone_number="01912345678",relationship="Landlord",is_trusted=True),
                    ])
                elif user.persona == "salaried worker":
                    db.add_all([
                        TrustedContact(user_id=user.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi",is_trusted=True),
                        TrustedContact(user_id=user.id,name="Samiha",phone_number="01887654321",relationship="Sister",nickname="Samiha",is_trusted=True),
                    ])
                elif user.persona == "freelancer":
                    db.add_all([
                        TrustedContact(user_id=user.id,name="Arif Rahman",phone_number="01712345678",relationship="Brother",nickname="Arif",is_trusted=True),
                        TrustedContact(user_id=user.id,name="Nadia",phone_number="01812345678",relationship="Friend",nickname="Nadia",is_trusted=True),
                    ])
            if user.persona == "student" and not db.scalar(select(TrustedHelper.id).where(TrustedHelper.user_id == user.id).limit(1)):
                db.add(TrustedHelper(user_id=user.id,helper_name="Mim Akter",relationship="Daughter",phone="01812345678",can_view_pending_transaction=True,can_receive_alerts=True,can_view_balance=False,can_view_history=False,can_initiate=False))
        db.commit()
        return
    rng=random.Random(2026); now=datetime.now().replace(second=0,microsecond=0)
    for email,name,persona,income,starting in PERSONAS:
        u=User(email=email,display_name=name,persona=persona); db.add(u);db.flush(); balance=Decimal(str(starting))
        account=Account(user_id=u.id,balance=balance); db.add(account)
        for day_back in range(90,0,-1):
            d=now-timedelta(days=day_back)
            # regular income
            if (persona != "freelancer" and d.day == 1) or (persona == "freelancer" and d.day in (4,15,25) and rng.random()>.25):
                amount=Decimal(str(income if persona!="freelancer" else rng.randint(7000,17000))); before=balance;balance+=amount
                db.add(Transaction(user_id=u.id,merchant_name="Salary / Client payment",category="Income",amount=amount,direction="income",transaction_type="salary",timestamp=d.replace(hour=10),balance_before=before,balance_after=balance,description="Synthetic demo income"))
            # student has intentional late month pressure + rising food spend in current month
            categories=["Food","Food","Groceries","Transport","Mobile Recharge","Bills","Entertainment","Shopping"]
            if d.weekday()>=5: categories += ["Food","Entertainment"]
            for _ in range(rng.randint(0,2)):
                cat=rng.choice(categories); base={"Food":210,"Groceries":900,"Transport":130,"Mobile Recharge":250,"Bills":700,"Entertainment":500,"Shopping":1200}[cat]
                # This pressure belongs to the generated records, not a hard-coded explanation.
                multiplier=1.65 if (persona=="student" and d.day>=22 and cat in {"Food","Transport"}) else 1
                raw=Decimal(str(round(rng.uniform(.65,1.35)*base*multiplier,2)))
                amount=min(raw,max(Decimal("0"),balance-Decimal("300")))
                if amount <= 0: continue
                before=balance; balance-=amount
                db.add(Transaction(user_id=u.id,merchant_name=rng.choice(MERCHANTS[cat]),category=cat,amount=amount,direction="expense",transaction_type="merchant_payment",timestamp=d.replace(hour=rng.randint(8,22),minute=rng.randint(0,59)),balance_before=before,balance_after=balance,description="Synthetic demo transaction"))
            if d.day in (5,20):
                cat="Subscriptions";amount=Decimal("199" if d.day==5 else "120")
                if balance-amount>=Decimal("300"):
                    before=balance;balance-=amount
                    db.add(Transaction(user_id=u.id,merchant_name=rng.choice(MERCHANTS[cat]),category=cat,amount=amount,direction="expense",transaction_type="subscription",timestamp=d.replace(hour=9),balance_before=before,balance_after=balance,is_recurring=True,description="Synthetic recurring payment"))
            if d.day==10:
                amount=Decimal("850" if persona=="student" else "1600")
                if balance-amount>=Decimal("300"):
                    before=balance;balance-=amount
                    db.add(Transaction(user_id=u.id,merchant_name="DESCO",category="Bills",amount=amount,direction="expense",transaction_type="bill_payment",timestamp=d.replace(hour=11),balance_before=before,balance_after=balance,is_recurring=True,description="Synthetic utility bill"))
        # Merchant and recurring events are generated independently. Rebuild the
        # running ledger in timestamp order so every balance_before/after value
        # agrees with the account's final balance.
        db.flush()
        running_balance=Decimal(str(starting))
        rows=list(db.scalars(select(Transaction).where(Transaction.user_id==u.id).order_by(Transaction.timestamp,Transaction.id)))
        for transaction in rows:
            transaction.balance_before=running_balance
            running_balance += Decimal(str(transaction.amount)) if transaction.direction=="income" else -Decimal(str(transaction.amount))
            transaction.balance_after=running_balance
        account.balance=running_balance
        start=(now-timedelta(days=29)).date(); db.add(Budget(user_id=u.id,total_limit=income*.72, start_date=start,end_date=now.date(),categories={"Food":income*.16,"Transport":income*.09,"Groceries":income*.14,"Bills":income*.1,"Entertainment":income*.06}))
        db.add(SavingsGoal(user_id=u.id,name="Laptop Fund" if persona=="student" else "Emergency buffer",target_amount=30000 if persona=="student" else 50000,current_amount=5000 if persona=="student" else 12000,target_date=date.today()+timedelta(days=180)))
        db.add(Notification(user_id=u.id,title="Synthetic demo data",body="This prototype uses generated transactions, not production upay data.",severity="info"))
        # Add trusted contacts
        if persona == "student":
            db.add(TrustedContact(user_id=u.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi",is_trusted=True))
            db.add(TrustedContact(user_id=u.id,name="Mim Akter",phone_number="01812345678",relationship="Daughter",nickname="Mim",is_trusted=True))
            db.add(TrustedContact(user_id=u.id,name="Rahman",phone_number="01912345678",relationship="Landlord",is_trusted=True))
            db.add(TrustedHelper(user_id=u.id,helper_name="Mim Akter",relationship="Daughter",phone="01812345678",can_view_pending_transaction=True,can_receive_alerts=True,can_view_balance=False,can_view_history=False,can_initiate=False))
        elif persona == "salaried worker":
            db.add(TrustedContact(user_id=u.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi",is_trusted=True))
            db.add(TrustedContact(user_id=u.id,name="Samiha",phone_number="01887654321",relationship="Sister",nickname="Samiha",is_trusted=True))
        elif persona == "freelancer":
            db.add(TrustedContact(user_id=u.id,name="Arif Rahman",phone_number="01712345678",relationship="Brother",nickname="Arif",is_trusted=True))
            db.add(TrustedContact(user_id=u.id,name="Nadia",phone_number="01812345678",relationship="Friend",nickname="Nadia",is_trusted=True))
    db.commit()
