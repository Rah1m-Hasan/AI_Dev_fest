"""Deterministic, consent-safe synthetic Bangladeshi MFS demo data generator."""
import random
from decimal import Decimal
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User,UserPhone,Account,Transaction,Budget,SavingsGoal,Notification,TrustedContact,TrustedHelper,HelperRelationship,HelperActivity,FinancialLesson,Offer

MERCHANTS={"Food":["Bhojon Express","Cafe Dhaka","Pathao Food"],"Groceries":["Shwapno","Meena Bazar","Agora"],"Transport":["Pathao","Uber","Metro Rail"],"Bills":["DESCO","WASA","BTCL"],"Mobile Recharge":["Grameenphone","Robi"],"Entertainment":["Star Cineplex","Bioscope"],"Shopping":["Daraz","Aarong"],"Education":["DIU Fees","Bookworm"],"Healthcare":["Popular Diagnostic","Pharmacy"],"Subscriptions":["Spotify","Google One"],"Cash Out":["Agent Cash Out"]}
PERSONAS=[("demo.student@upay.local","Arif Rahman","student",12000,10500),("demo.salary@upay.local","Nadia Islam","salaried worker",38000,22000),("demo.freelancer@upay.local","Samiha Noor","freelancer",30000,15000),("demo.business@upay.local","Rafi Ahmed","small business owner",52000,30000)]
DEMO_PHONES={"demo.student@upay.local":"01712345678","demo.salary@upay.local":"01887654321","demo.freelancer@upay.local":"01987654321","demo.business@upay.local":"01612345678"}
def trusted_contact(**kwargs):
    phone = kwargs["phone_number"]
    kwargs.update(normalized_phone="880" + phone[1:] if phone.startswith("0") else phone, verification_status="verified", verified_at=datetime.utcnow(), is_trusted=True)
    return TrustedContact(**kwargs)
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
            if user.email in DEMO_PHONES and not db.scalar(select(UserPhone.id).where(UserPhone.user_id == user.id)):
                db.add(UserPhone(user_id=user.id, phone=DEMO_PHONES[user.email]))
            if rafi and rafi.relationship == "Son":
                rafi.relationship = "Brother"
            if not db.scalar(select(TrustedContact.id).where(TrustedContact.user_id == user.id).limit(1)):
                if user.persona == "student":
                    db.add_all([
                        trusted_contact(user_id=user.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi"),
                        trusted_contact(user_id=user.id,name="Mim Akter",phone_number="01812345678",relationship="Daughter",nickname="Mim"),
                        trusted_contact(user_id=user.id,name="Rahman",phone_number="01912345678",relationship="Landlord"),
                    ])
                elif user.persona == "salaried worker":
                    db.add_all([
                        trusted_contact(user_id=user.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi"),
                        trusted_contact(user_id=user.id,name="Samiha",phone_number="01887654321",relationship="Sibling",nickname="Samiha"),
                    ])
                elif user.persona == "freelancer":
                    db.add_all([
                        trusted_contact(user_id=user.id,name="Arif Rahman",phone_number="01712345678",relationship="Brother",nickname="Arif"),
                        trusted_contact(user_id=user.id,name="Nadia",phone_number="01812345678",relationship="Friend",nickname="Nadia"),
                    ])
            if user.persona == "student" and not db.scalar(select(TrustedHelper.id).where(TrustedHelper.user_id == user.id).limit(1)):
                db.add(TrustedHelper(user_id=user.id,helper_name="Mim Akter",relationship="Daughter",phone="01812345678",can_view_pending_transaction=True,can_receive_alerts=True,can_view_balance=False,can_view_history=False,can_initiate=False))
            if user.persona == "student" and not db.scalar(select(HelperRelationship.id).where(HelperRelationship.owner_user_id == user.id).limit(1)):
                helper = HelperRelationship(owner_user_id=user.id, helper_name="Mim Akter", helper_phone="01812345678", relationship="Daughter", status="active", permissions=["explain_financial_info","guide_navigation","view_alerts","view_financial_health"])
                db.add(helper); db.flush()
                db.add_all([HelperActivity(owner_user_id=user.id, helper_relationship_id=helper.id, actor="owner", event_type="helper_invited", detail="Invitation sent to Mim Akter"), HelperActivity(owner_user_id=user.id, helper_relationship_id=helper.id, actor="helper", event_type="helper_accepted", detail="Mim Akter accepted the invitation")])
        _ensure_offer_learning_links(db)
        db.commit()
        return
    rng=random.Random(2026); now=datetime.now().replace(second=0,microsecond=0)
    for email,name,persona,income,starting in PERSONAS:
        u=User(email=email,display_name=name,persona=persona); db.add(u);db.flush(); db.add(UserPhone(user_id=u.id,phone=DEMO_PHONES[email])); balance=Decimal(str(starting))
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
            db.add(trusted_contact(user_id=u.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi"))
            db.add(trusted_contact(user_id=u.id,name="Mim Akter",phone_number="01812345678",relationship="Child",nickname="Mim"))
            db.add(trusted_contact(user_id=u.id,name="Rahman",phone_number="01912345678",relationship="Landlord"))
            db.add(TrustedHelper(user_id=u.id,helper_name="Mim Akter",relationship="Daughter",phone="01812345678",can_view_pending_transaction=True,can_receive_alerts=True,can_view_balance=False,can_view_history=False,can_initiate=False))
            helper=HelperRelationship(owner_user_id=u.id,helper_name="Mim Akter",helper_phone="01812345678",relationship="Daughter",status="active",permissions=["explain_financial_info","guide_navigation","view_alerts","view_financial_health"])
            db.add(helper);db.flush();db.add_all([HelperActivity(owner_user_id=u.id,helper_relationship_id=helper.id,actor="owner",event_type="helper_invited",detail="Invitation sent to Mim Akter"),HelperActivity(owner_user_id=u.id,helper_relationship_id=helper.id,actor="helper",event_type="helper_accepted",detail="Mim Akter accepted the invitation")])
        elif persona == "salaried worker":
            db.add(trusted_contact(user_id=u.id,name="Rafi Ahmed",phone_number="01712345678",relationship="Brother",nickname="Rafi"))
            db.add(trusted_contact(user_id=u.id,name="Samiha",phone_number="01887654321",relationship="Sibling",nickname="Samiha"))
        elif persona == "freelancer":
            db.add(trusted_contact(user_id=u.id,name="Arif Rahman",phone_number="01712345678",relationship="Brother",nickname="Arif"))
            db.add(trusted_contact(user_id=u.id,name="Nadia",phone_number="01812345678",relationship="Friend",nickname="Nadia"))

    # --- Seed Lessons ---
    if not db.scalars(select(FinancialLesson.id).limit(1)).first():
        _seed_lessons(db)

    # --- Seed Offers ---
    if not db.scalars(select(Offer.id).limit(1)).first():
        _seed_offers(db)

    _ensure_offer_learning_links(db)

    db.commit()

def _ensure_offer_learning_links(db):
    """Keep the offer-to-learning connection explicit in both fresh and demo DBs."""
    lesson = db.scalar(select(FinancialLesson).where(FinancialLesson.title == "Minimum Spend vs Real Savings"))
    if not lesson:
        lesson = FinancialLesson(
            title="Minimum Spend vs Real Savings",
            summary="A discount helps only when it fits a purchase you already planned.",
            content="""A discount is not automatically a saving. It only reduces the cost of something you already planned to buy.\n\nIf an offer needs a minimum spend of ৳800 and your normal purchase is ৳715, spending more just to qualify means your total out-of-pocket cost goes up. The discount may make the larger purchase cheaper than its full price, but it does not make it cheaper than your original plan.\n\nA useful check is simple: compare the offer minimum with the amount you were already going to spend. If the planned amount is below the minimum, skip the offer unless your plan has genuinely changed.""",
            content_bn="ছাড় তখনই সাশ্রয় যখন আপনি আগে থেকেই সেই খরচ করার পরিকল্পনা করেছিলেন। ন্যূনতম খরচ পূরণ করতে অতিরিক্ত ব্যয় করলে মোট খরচ বাড়তে পারে।",
            category="Money Basics", difficulty="beginner", duration_minutes=2,
            personalized_section="Compare every offer with your usual purchase before changing what you planned to spend.",
            personalized_section_bn="খরচের পরিকল্পনা বদলানোর আগে অফারটি আপনার স্বাভাবিক কেনাকাটার সঙ্গে তুলনা করুন।",
            quiz={"question": "When is a minimum-spend offer most likely to help?", "options": [{"key": "A", "text": "When you spend more just to qualify"}, {"key": "B", "text": "When your planned purchase already meets the minimum"}], "correct_key": "B"},
            trigger_type="budgeting", trigger_rule={"type": "always"}, active=True,
        )
        db.add(lesson)
        db.flush()
    offers = list(db.scalars(select(Offer).where(Offer.min_spend.isnot(None), Offer.learning_lesson_id.is_(None))))
    for offer in offers:
        offer.learning_lesson_id = lesson.id

def _seed_lessons(db):
    lessons = [
        # === BUDGETING ===
        FinancialLesson(
            title="Why Weekly Grocery Limits Beat Monthly Budgets",
            summary="Smaller targets help you notice overspending earlier.",
            content="""Monthly budgets deal in large numbers that are hard to feel in daily life. When you set a monthly grocery target of ৳8,000, it is easy to reach the 20th with no awareness of how much room is left.\n\nA weekly target divides that same ৳8,000 into roughly ৳2,000 per week. This makes it easier to notice, around day three or four, whether you are on track.\n\nIf you overspend in week one, you still have weeks two, three, and four to adjust. A monthly budget tells you only at the end of the month — when it is too late to act.\n\nPractical step: Pick one category where you often overspend. Divide your monthly target by four. Check your spending each Friday to see if you are on pace.""",
            content_bn="মাসিক বাজেটে বড় সংখ্যা মোকাবেলা করা কঠিন। সাপ্তাহিক লক্ষ্য বিভাজন করলে খরচ আগেই বোঝা যায়।",
            category="Budgeting", difficulty="beginner", duration_minutes=2,
            personalized_section="Your grocery spending has increased recently. A weekly target could help you spot overspending before the month ends.",
            personalized_section_bn="আপনার মুদি খরচ সম্প্রতি বেড়েছে। সাপ্তাহিক লক্ষ্য সেট করলে মাস শেষ হওয়ার আগেই বোঝা যাবে।",
            quiz={"question": "Which is easier to notice sooner?", "options": [{"key": "A", "text": "A monthly budget only"}, {"key": "B", "text": "A smaller weekly spending target"}, {"key": "C", "text": "A daily spending journal"}, {"key": "D", "text": "Bank statement at month end"}], "correct_key": "B"},
            trigger_type="high_grocery",
            trigger_rule={"type": "spending_change", "category": "Groceries", "min_change_percent": 15},
            active=True,
        ),
        FinancialLesson(
            title="Managing Money When Income Changes Every Month",
            summary="Plan around your lowest month, not your highest.",
            content="""When your income is the same every month, budgeting is straightforward: subtract your expenses, save the rest. Variable income makes that harder.\n\nOne month you earn ৳30,000, the next ৳18,000. If you spend as if you always earn ৳30,000, the low month will catch up with you.\n\nA simple approach: identify your lowest typical month. Build a budget around that number. When you earn more, put the surplus into a buffer before it feels available to spend.\n\nThis buffer absorbs the difference between high and low months so your daily spending stays consistent.""",
            content_bn="ভেরিয়েবল আয়ে, সবচেয়ে কম আয়ের মাসকে ভিত্তি করে পরিকল্পনা করুন। বেশি আয় হলে সঞ্চয় করুন।",
            category="Budgeting", difficulty="intermediate", duration_minutes=3,
            personalized_section="Your income varies month to month. Budgeting around a lower month keeps spending steady even when earnings dip.",
            personalized_section_bn="আপনার আয় মাসে মাসে ওঠানামা করে। কম আয়ের মাসকে ভিত্তি করে বাজেট করলে খরচ স্থির থাকে।",
            quiz={"question": "When income varies, what should you budget around?", "options": [{"key": "A", "text": "Your highest earning month"}, {"key": "B", "text": "Your average monthly income"}, {"key": "C", "text": "Your lowest typical month"}, {"key": "D", "text": "Last month's actual spending"}], "correct_key": "C"},
            trigger_type="variable_income",
            trigger_rule={"type": "income_stability", "value": "variable"},
            active=True,
        ),
        FinancialLesson(
            title="The 50/30/20 Rule Made Simple",
            summary="A simple split: needs, wants, and savings.",
            content="""The 50/30/20 rule divides your after-income into three parts.\n\n50% for needs: rent, utilities, groceries, transport — the things you cannot avoid.\n\n30% for wants: dining out, entertainment, subscriptions — nice-to-have spending.\n\n20% for savings: emergency buffer, goal fund, retirement.\n\nThis is a starting point, not a strict law. If needs take 60%, that is a signal to look at rent or transport costs. If savings fall to 10%, that is a signal to review discretionary spending.\n\nThe value of the framework is that it forces you to name what each taka is doing. Money that is not assigned a job tends to disappear.""",
            content_bn="৫০/৩০/২০ নিয়ম: প্রয়োজন, ইচ্ছা, এবং সঞ্চয় — প্রতিটি টাকাকে একটি কাজ দিন।",
            category="Budgeting", difficulty="beginner", duration_minutes=2,
            personalized_section="A budget framework helps any persona, especially when income and spending fluctuate across months.",
            personalized_section_bn="বাজেটের কাঠামো যেকোনো আয়ের পরিস্থিতিতে কাজ করে।",
            quiz={"question": "In 50/30/20, what does the 20% represent?", "options": [{"key": "A", "text": "Essential spending"}, {"key": "B", "text": "Entertainment and dining"}, {"key": "C", "text": "Savings and debt repayment"}, {"key": "D", "text": "Emergency repairs"}], "correct_key": "C"},
            trigger_type="budgeting",
            trigger_rule={"type": "always"},
            active=True,
        ),

        # === SAVING ===
        FinancialLesson(
            title="Why a Small Emergency Buffer Changes Everything",
            summary="Even ৳2,000 saved prevents small crises from becoming big ones.",
            content="""An emergency buffer is not about covering a job loss. It is about handling the small surprises that happen every month: a phone charger breaking, a medical bill, a urgente travel need.\n\nWithout a buffer, these small surprises go on a credit card or get covered by skipping another bill. That creates a chain of debt that is hard to stop.\n\nA buffer of just ৳2,000–৳5,000 stops this chain. It will not cover a major crisis, but it handles the ordinary ones that happen most often.\n\nThe goal is not to save a lot quickly. The goal is to stop small problems from getting bigger.""",
            content_bn="জরুরি বাফার বড় সংকট নয়, ছোট চমক মোকাবেলা করার জন্য। এমনকি ২,০০০ টাকাও ছোট সমস্যা বড় হতে বাধা দেয়।",
            category="Saving", difficulty="beginner", duration_minutes=2,
            personalized_section="Your financial health score is currently below 50, which means a small buffer could make a meaningful difference in handling surprise expenses.",
            personalized_section_bn="আপনার ফাইন্যান্সিয়াল হেলথ স্কোর এখন ৫০-এর নিচে। একটি ছোট বাফার দিয়ে শুরু করুন।",
            quiz={"question": "What is the primary purpose of an emergency buffer?", "options": [{"key": "A", "text": "Covering job loss for months"}, {"key": "B", "text": "Handling small surprise expenses before they compound"}, {"key": "C", "text": "Funding a vacation"}, {"key": "D", "text": "Paying rent early"}], "correct_key": "B"},
            trigger_type="low_emergency",
            trigger_rule={"type": "health_score", "max": 50},
            active=True,
        ),
        FinancialLesson(
            title="Saving Consistently Beats Saving Big Amounts",
            summary="৳100 a week builds more than ৳4,000 once a year.",
            content="""The instinct is to save when there is money left at the end of the month. This rarely works because there is almost never money left.\n\nConsistent saving means moving a small amount to savings the moment income arrives — before it has a chance to be spent. This is called paying yourself first.\n\nSaving ৳200 every time you get paid, even if you only get paid twice a month, means ৳400 a month or ৳4,800 a year. That is ৳4,800 that would otherwise not exist.\n\nThe amount is less important than the habit. Small regular saving builds momentum in a way that large occasional saving does not.""",
            content_bn="নিয়মিত সঞ্চয় করাই সবচেয়ে কার্যকর। বেতন পাওয়ার সাথে সাথেই সঞ্চয় করুন, খরচের আগে।",
            category="Saving", difficulty="beginner", duration_minutes=2,
            personalized_section="You have an active savings goal. Consistent small contributions are more effective than waiting to save a large amount.",
            personalized_section_bn="আপনার একটি সক্রিয় সঞ্চয় লক্ষ্য আছে। ছোট নিয়মিত অবদানই সবচেয়ে কার্যকর।",
            quiz={"question": "What does 'paying yourself first' mean?", "options": [{"key": "A", "text": "Buying what you want before bills"}, {"key": "B", "text": "Moving money to savings before it can be spent"}, {"key": "C", "text": "Paying off your highest interest debt"}, {"key": "D", "text": "Saving whatever is left at month end"}], "correct_key": "B"},
            trigger_type="savings_goal",
            trigger_rule={"type": "has_active_goal"},
            active=True,
        ),
        FinancialLesson(
            title="What Interest Costs More: The True Price of Cash Out",
            summary="An agent cash-out fee of 1.85% is actually much more expensive than it sounds.",
            content="""Mobile financial services charge around 1.85% to cash out, with a minimum of ৳15. This sounds small.\n\nBut if you withdraw ৳500 to avoid carrying a balance, the 1.85% charge is only ৳9.25 — the minimum ৳15 applies instead. That ৳15 on ৳500 is effectively a 3% fee.\n\nOver a year, if you cash out twice a month, that is ৳360 in fees — money that did not buy anything.\n\nThe alternative: use merchant payments when possible. Buying directly from a store, paying a bill through the app, or sending money to a shop keeps the value in your account rather than paying to convert it to cash.""",
            content_bn="ক্যাশ আউট ফি বছরে ৳৩৬০+ হতে পারে। মার্চেন্ট পেমেন্ট এই খরচ এড়ায়।",
            category="Saving", difficulty="intermediate", duration_minutes=2,
            personalized_section="You have made multiple cash-out transactions recently. Each withdrawal carries a fee that merchant payments would avoid.",
            personalized_section_bn="আপনি সম্প্রতি একাধিক ক্যাশ আউট করেছেন। প্রতিটি উইথড্রয়াল ফি বহন করে।",
            quiz={"question": "Why is a 1.85% cash-out fee often worse than it sounds?", "options": [{"key": "A", "text": "It compounds daily"}, {"key": "B", "text": "The minimum fee makes small withdrawals proportionally expensive"}, {"key": "C", "text": "It is charged monthly"}, {"key": "D", "text": "It applies only to amounts over ৳1,000"}], "correct_key": "B"},
            trigger_type="frequent_cashout",
            trigger_rule={"type": "cash_out_count", "min_count": 3},
            active=True,
        ),

        # === MFS BASICS ===
        FinancialLesson(
            title="Send Money Basics: bKash to Any Number",
            summary="Sending money takes seconds and costs less than going to an agent.",
            content="""Sending money through a mobile financial service app costs ৳5–৳10 per transaction, depending on the amount. Going to an agent and cashing out to deliver cash physically costs 1.85% of the amount.\n\nIf you need to send ৳500 to someone, the app costs ৳5. An agent round-trip could cost ৳15–৳25 in combined fees.\n\nBeyond cost, sending through the app is faster and creates a digital record that protects both parties. There is no risk of a counterfeit note and no need to travel.\n\nThe PIN protects every transaction. Never share it, and never let someone else hold the phone during a transaction.""",
            content_bn="অ্যাপে টাকা পাঠানো এজেন্টের চেয়ে দ্রুত, সস্তা এবং নিরাপদ। পিন কখনো শেয়ার করবেন না।",
            category="MFS Basics", difficulty="beginner", duration_minutes=2,
            personalized_section="As a new or occasional MFS user, knowing when to use the app versus an agent can save you significant fees over time.",
            personalized_section_bn="নতুন ব্যবহারকারী হিসেবে, অ্যাপ বনাম এজেন্ট কখন ব্যবহার করবেন তা জানা গুরুত্বপূর্ণ।",
            quiz={"question": "What is a key advantage of sending money through the app over an agent?", "options": [{"key": "A", "text": "Faster cash availability for the recipient"}, {"key": "B", "text": "Lower cost and a digital transaction record"}, {"key": "C", "text": "No PIN required for transactions"}, {"key": "D", "text": "Works without internet connection"}], "correct_key": "B"},
            trigger_type="new_mfs",
            trigger_rule={"type": "persona", "value": "student"},
            active=True,
        ),
        FinancialLesson(
            title="Cash Out vs. Merchant Payment: The Hidden Cost of Withdrawing",
            summary="Every cash-out has a cost. Merchant payments have none.",
            content="""When you pay a merchant directly through the app, there is no fee. When you withdraw cash and pay in person, there is.\n\nA ৳1,000 purchase at a merchant costs ৳1,000. A ৳1,000 withdrawal plus a ৳1,000 payment in cash costs ৳1,000 plus ৳18.50 (1.85% minimum ৳15).\n\nThe difference is small per transaction but compounds over time. Someone who cashes out twice a week spends roughly ৳1,800 a year in fees that a merchant payment would have avoided.\n\nThe exception is when you genuinely need cash. But if the end goal is to buy something from a store, the merchant payment is the better path.""",
            content_bn="মার্চেন্ট পেমেন্টে কোনো ফি নেই, ক্যাশ আউটে আছে। ১০০০ টাকা ক্যাশ আউটে ১৮.৫০ টাকা লস।",
            category="MFS Basics", difficulty="beginner", duration_minutes=2,
            personalized_section="Using merchant payments instead of cash-out for purchases could save you roughly ৳1,800 per year in fees.",
            personalized_section_bn="ক্রয়ের জন্য মার্চেন্ট পেমেন্ট ব্যবহার করলে বছরে ১,৮০০ টাকার বেশি সাশ্রয় হতে পারে।",
            quiz={"question": "What is the main cost of an agent cash-out compared to a merchant payment?", "options": [{"key": "A", "text": "Time spent traveling to the agent"}, {"key": "B", "text": "A percentage-based fee that merchant payments do not charge"}, {"key": "C", "text": "Risk of counterfeit notes"}, {"key": "D", "text": "Delayed transaction confirmation"}], "correct_key": "B"},
            trigger_type="frequent_cashout",
            trigger_rule={"type": "cash_out_count", "min_count": 2},
            active=True,
        ),

        # === DIGITAL SAFETY ===
        FinancialLesson(
            title="PIN Safety: The One Habit That Protects Everything",
            summary="Your PIN is the key to your money. Keep it to yourself.",
            content="""Mobile financial services protect your account with a PIN that you enter before every transaction. That PIN is the only barrier between your money and anyone who gets hold of your phone.\n\nThe most common mistake is sharing the PIN with a family member or friend who is trying to help. If they have your PIN and your phone, they have full access to your balance.\n\nNo genuine service — not the app support, not a call center — will ever ask for your PIN. Anyone who asks for it is attempting fraud.\n\nBasic PIN hygiene: use 4–6 digits, change it occasionally, never write it down, never enter it on someone else's request, and never share it over the phone.""",
            content_bn="পিন আপনার টাকার একমাত্র সুরক্ষা। কেউই আপনার পিন জানতে চাইবে না — এটা প্রতারণা।",
            category="Digital Safety", difficulty="beginner", duration_minutes=2,
            personalized_section="PIN safety is fundamental regardless of your financial situation or account balance.",
            personalized_section_bn="পিন সুরক্ষা যেকোনো আর্থিক পরিস্থিতিতে মৌলিক — আপনার টাকার একমাত্র সুরক্ষা।",
            quiz={"question": "Who might legitimately ask for your MFS PIN?", "options": [{"key": "A", "text": "Customer support representative calling you"}, {"key": "B", "text": "A family member helping you set up"}, {"key": "C", "text": "Nobody — genuine services never ask for it"}, {"key": "D", "text": "A delivery person confirming your identity"}], "correct_key": "C"},
            trigger_type="digital_safety",
            trigger_rule={"type": "always"},
            active=True,
        ),
        FinancialLesson(
            title="Recognizing and Avoiding MFS Scams",
            summary="Scammers create urgency. Real services do not.",
            content="""MFS scams generally follow one of three patterns.\n\nThe prize scam: you receive a message saying you have won money and need to send a small fee to claim it. No genuine prize requires you to pay to receive it.\n\nThe urgent family scam: a message pretending to be a family member in trouble and needing money immediately. Verify by calling them directly before sending anything.\n\nThe KYC update scam: a message saying your account will be suspended unless you verify with your PIN. Your actual provider will never ask for your PIN via SMS or link.\n\nThe common thread is urgency. Scammers want you to act before you think. Real services create calm, not panic.""",
            content_bn="প্রতারণায় জরুরিতা তৈরি করা হয়। আসল সার্ভিস কখনো জরুরি অবস্থা তৈরি করে না।",
            category="Digital Safety", difficulty="beginner", duration_minutes=2,
            personalized_section="All users benefit from understanding common scam patterns before encountering them.",
            personalized_section_bn="সবাইকে প্রতারণার কৌশল জানা উচিত।",
            quiz={"question": "What is a common trait of MFS scam messages?", "options": [{"key": "A", "text": "They come from your bank's official number"}, {"key": "B", "text": "They offer a real prize with a claim fee"}, {"key": "C", "text": "They create urgency to prevent careful thinking"}, {"key": "D", "text": "They ask you to call a verified support number"}], "correct_key": "C"},
            trigger_type="digital_safety",
            trigger_rule={"type": "always"},
            active=True,
        ),
    ]
    db.add_all(lessons)


def _seed_offers(db):
    from datetime import date, timedelta
    today = date.today()
    offers = [
        # === GROCERIES ===
        Offer(
            title="Weekend Grocery Savings",
            terms="8% off grocery purchases. This demo offer has ended.",
            terms_bn="মুদি কেনাকাটায় ৮% ছাড়। এই ডেমো অফারটি শেষ হয়েছে।",
            category="Groceries", active=True,
            min_spend=700.0, discount_percent=8.0, max_discount=120.0,
            typical_merchant="Shwapno", expiry_date=today - timedelta(days=3),
            eligibility_notes="Expired demo offer.", learning_lesson_id=None,
        ),
        Offer(
            title="Shwapno 10% Off Groceries",
            terms="Get 10% off your grocery purchase at Shwapno stores. Minimum spend ৳800. Maximum saving ৳150. Valid on weekdays.",
            terms_bn="শ্বাপনোতে ১০% ছাড়। সর্বনিম্ন খরচ ৮০০ টাকা।",
            category="Groceries", active=True,
            min_spend=800.0, discount_percent=10.0, max_discount=150.0,
            typical_purchase=715.0, typical_merchant="Shwapno",
            expiry_date=today + timedelta(days=30),
            eligibility_notes="Valid at all Shwapno outlets. Not valid on Friday.",
            learning_lesson_id=None,
        ),
        Offer(
            title="Meena Bazar 5% Cashback on Groceries",
            terms="5% cashback on grocery purchases above ৳1,000 at Meena Bazar. Maximum cashback ৳75 per transaction.",
            terms_bn="মীনা বাজারে ৫% ক্যাশব্যাক। সর্বনিম্ন খরচ ১,০০০ টাকা।",
            category="Groceries", active=True,
            min_spend=1000.0, discount_percent=5.0, max_discount=75.0,
            typical_purchase=900.0, typical_merchant="Meena Bazar",
            expiry_date=today + timedelta(days=21),
            eligibility_notes="Valid on all days at Meena Bazar outlets.",
            learning_lesson_id=None,
        ),
        Offer(
            title="Agora Extra Savings Day",
            terms="Every Tuesday at Agora: 8% off on all grocery items. Minimum spend ৳1,200.",
            terms_bn="প্রতি মঙ্গলবার আগোরায় ৮% ছাড়। সর্বনিম্ন খরচ ১,২০০ টাকা।",
            category="Groceries", active=True,
            min_spend=1200.0, discount_percent=8.0, max_discount=200.0,
            typical_purchase=950.0, typical_merchant="Agora",
            expiry_date=today + timedelta(days=45),
            eligibility_notes="Tuesday only at all Agora outlets.",
            learning_lesson_id=None,
        ),

        # === BILLS ===
        Offer(
            title="DESCO Bill Pay — ৳50 Cashback",
            terms="Pay your DESCO electricity bill through the app and get ৳50 cashback. Minimum bill amount ৳1,000.",
            terms_bn="অ্যাপে ডেসকো বিল পে করে ৳৫০ ক্যাশব্যাক পান।",
            category="Bills", active=True,
            min_spend=1000.0, discount_fixed=50.0, max_discount=50.0,
            typical_purchase=850.0, typical_merchant="DESCO",
            expiry_date=today + timedelta(days=60),
            eligibility_notes="Only for DESCO bill payments made through the app. One cashback per bill payment.",
            learning_lesson_id=None,
        ),
        Offer(
            title="WASA Bill Pay — No Convenience Fee",
            terms="Pay WASA bills with zero convenience fee this month. No minimum amount required.",
            terms_bn="এই মাসে ওয়াসা বিল পেতে কোনো কনভেনিয়েন্স ফি নেই।",
            category="Bills", active=True,
            min_spend=None, discount_percent=100.0, max_discount=None,
            typical_purchase=650.0, typical_merchant="WASA",
            expiry_date=today + timedelta(days=15),
            eligibility_notes="Fee waiver only; no cashback. Applies to WASA bills only.",
            learning_lesson_id=None,
        ),
        Offer(
            title="BTCL Landline Bill — ৳30 Off",
            terms="Pay BTCL landline or internet bills and get ৳30 off. Minimum bill ৳500.",
            terms_bn="বিটিসিএল বিল পে করে ৳৩০ ছাড় পান। সর্বনিম্ন বিল ৫০০ টাকা।",
            category="Bills", active=True,
            min_spend=500.0, discount_fixed=30.0, max_discount=30.0,
            typical_purchase=550.0, typical_merchant="BTCL",
            expiry_date=today + timedelta(days=30),
            eligibility_notes="Applies to BTCL landline and internet bills only.",
            learning_lesson_id=None,
        ),

        # === TRANSPORT ===
        Offer(
            title="Pathao — 15% Off First 3 Rides",
            terms="15% off your first 3 Pathao rides this month. Maximum discount ৳40 per ride.",
            terms_bn="এই মাসে প্রথম ৩টি পাথাও রাইডে ১৫% ছাড়।",
            category="Transport", active=True,
            min_spend=200.0, discount_percent=15.0, max_discount=40.0,
            typical_purchase=130.0, typical_merchant="Pathao",
            expiry_date=today + timedelta(days=20),
            eligibility_notes="New and existing Pathao users. Capped at 3 rides per user.",
            learning_lesson_id=None,
        ),
        Offer(
            title="Uber — ৳25 Off Every 5th Ride",
            terms="Get ৳25 off your 5th Uber ride in a month. Minimum fare ৳150.",
            terms_bn="প্রতি ৫ম উবার রাইডে ৳২৫ ছাড়। সর্বনিম্ন ভাড়া ১৫০ টাকা।",
            category="Transport", active=True,
            min_spend=150.0, discount_fixed=25.0, max_discount=25.0,
            typical_purchase=180.0, typical_merchant="Uber",
            expiry_date=today + timedelta(days=30),
            eligibility_notes="Counts all Uber rides in a calendar month.",
            learning_lesson_id=None,
        ),

        # === MOBILE RECHARGE ===
        Offer(
            title="Grameenphone — 5% Extra Talktime",
            terms="Get 5% extra talktime on every Grameenphone recharge of ৳100 or more.",
            terms_bn="প্রতিটি গ্রামীণফোন রিচার্জে ৫% এক্সট্রা টকটাইম।",
            category="Recharge", active=True,
            min_spend=100.0, discount_percent=5.0, max_discount=None,
            typical_purchase=50.0, typical_merchant="Grameenphone",
            expiry_date=today + timedelta(days=60),
            eligibility_notes="Applies to all GP prepaid recharges.",
            learning_lesson_id=None,
        ),
        Offer(
            title="Robi — Double Data on ৳200+ Recharge",
            terms="Recharge ৳200 or more on Robi and get double data offer. Valid for 7 days.",
            terms_bn="রোবিতে ৳২০০+ রিচার্জে ডাবল ডেটা।",
            category="Recharge", active=True,
            min_spend=200.0, discount_percent=100.0, max_discount=None,
            typical_purchase=100.0, typical_merchant="Robi",
            expiry_date=today + timedelta(days=25),
            eligibility_notes="Double data valid for 7 days after recharge. Applies to Robi prepaid only.",
            learning_lesson_id=None,
        ),

        # === SHOPPING ===
        Offer(
            title="Daraz 20% Off Fashion",
            terms="20% off fashion items on Daraz. Minimum spend ৳1,500. Maximum discount ৳300.",
            terms_bn="দারাজে ফ্যাশন আইটেমে ২০% ছাড়। সর্বনিম্ন খরচ ১,৫০০ টাকা।",
            category="Shopping", active=True,
            min_spend=1500.0, discount_percent=20.0, max_discount=300.0,
            typical_purchase=1200.0, typical_merchant="Daraz",
            expiry_date=today + timedelta(days=14),
            eligibility_notes="Fashion category only. Limited to one use per user.",
            learning_lesson_id=None,
        ),
        Offer(
            title="Aarong — 10% Off Traditional Wear",
            terms="10% off Aarong traditional wear and handicrafts. Minimum spend ৳2,000.",
            terms_bn="আরঙ্গে ঐতিহ্যবাহী পোশাকে ১০% ছাড়। সর্বনিম্ন খরচ ২,০০০ টাকা।",
            category="Shopping", active=True,
            min_spend=2000.0, discount_percent=10.0, max_discount=500.0,
            typical_purchase=1800.0, typical_merchant="Aarong",
            expiry_date=today + timedelta(days=40),
            eligibility_notes="In-store and online. Traditional wear and handicrafts category only.",
            learning_lesson_id=None,
        ),

        # === ENTERTAINMENT ===
        Offer(
            title="Star Cineplex — ৳100 Off on Tickets",
            terms="Get ৳100 off on movie tickets at Star Cineplex. Minimum ticket purchase ৳350.",
            terms_bn="স্টার সিনেপ্লেক্সে টিকিটে ৳১০০ ছাড়। সর্বনিম্ন টিকিট ৩৫০ টাকা।",
            category="Entertainment", active=True,
            min_spend=350.0, discount_fixed=100.0, max_discount=100.0,
            typical_purchase=400.0, typical_merchant="Star Cineplex",
            expiry_date=today + timedelta(days=18),
            eligibility_notes="Valid on standard screenings only. Not valid on premium formats.",
            learning_lesson_id=None,
        ),
        Offer(
            title="Bioscope — 1 Month Free Subscription",
            terms="Sign up for Bioscope and get 1 month free on any paid plan. No minimum spend.",
            terms_bn="বায়োস্কোপে যোগ দিন এবং যেকোনো পেইড প্ল্যানে ১ মাস বিনামূল্যে পান।",
            category="Entertainment", active=True,
            min_spend=None, discount_percent=100.0, max_discount=None,
            typical_purchase=199.0, typical_merchant="Bioscope",
            expiry_date=today + timedelta(days=30),
            eligibility_notes="New subscribers only. Free month applies to the first billing cycle.",
            learning_lesson_id=None,
        ),
    ]
    db.add_all(offers)
