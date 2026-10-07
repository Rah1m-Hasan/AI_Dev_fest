"""Deterministic learning/lesson service. No LLM for financial calculations."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import User, FinancialLesson, LessonProgress, Transaction, SavingsGoal
from app.services.analytics_service import spending_comparison, health_score, money_runway, spending_summary, period_bounds, is_spending, _tx, _money, dec, amount


def _get_user_signals(db: Session, user: User) -> dict:
    """Collect all deterministic signals for a user."""
    comparison = spending_comparison(db, user)
    health = health_score(db, user)
    runway = money_runway(db, user)
    summary = spending_summary(db, user.id)
    goals = list(db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == user.id, SavingsGoal.status == "active")).all())

    # Frequent cash-out detection
    now, start, _ = period_bounds()
    txs = _tx(db, user.id, start, now)
    cash_out_count = sum(1 for t in txs if is_spending(t) and t.category == "Cash Out")

    # Variable income detection
    budget_rec = {"income_stability": "steady"}
    from app.services.analytics_service import budget_recommendation
    budget_rec = budget_recommendation(db, user)

    return {
        "comparison": comparison,
        "health": health,
        "runway": runway,
        "summary": summary,
        "goals": goals,
        "cash_out_count": cash_out_count,
        "income_stability": budget_rec.get("income_stability", "steady"),
    }


def _match_triggers(lesson: FinancialLesson, signals: dict, user: User) -> tuple[bool, str | None]:
    """Return (matched, trigger_reason) for a lesson given user signals."""
    rule = lesson.trigger_rule or {}
    trigger_type = lesson.trigger_type

    if trigger_type == "high_grocery":
        comp = signals["comparison"]
        for cat in comp["categories"]:
            if cat["category"] == "Groceries" and cat["change_percent"] is not None and cat["change_percent"] >= 15:
                return True, f"Your grocery spending is up {cat['change_percent']:.0f}% compared with the previous period."
        return False, None

    if trigger_type == "high_food":
        comp = signals["comparison"]
        for cat in comp["categories"]:
            if cat["category"] == "Food" and cat["change_percent"] is not None and cat["change_percent"] >= 15:
                return True, f"Your food spending increased {cat['change_percent']:.0f}% compared with last month."
        return False, None

    if trigger_type == "high_transport":
        comp = signals["comparison"]
        for cat in comp["categories"]:
            if cat["category"] == "Transport" and cat["change_percent"] is not None and cat["change_percent"] >= 20:
                return True, f"Transport costs are up {cat['change_percent']:.0f}% recently."
        return False, None

    if trigger_type == "low_emergency":
        if signals["health"]["score"] < 50:
            return True, f"Your financial health score is {signals['health']['score']} — building a buffer can help."
        if signals["runway"]["days"] < 20:
            return True, f"Your balance covers about {signals['runway']['days']} days at current spending pace."
        return False, None

    if trigger_type == "frequent_cashout":
        if signals["cash_out_count"] >= 3:
            return True, f"You've made {signals['cash_out_count']} cash-out transactions in the last 30 days."
        return False, None

    if trigger_type == "new_mfs":
        # Show to users who haven't made many MFS transactions
        if user.persona == "student":
            return True, "As a student, knowing MFS basics helps you manage your daily money moves."
        return False, None

    if trigger_type == "savings_goal":
        if signals["goals"]:
            return True, f"You have an active savings goal — consistent saving habits can help reach it faster."
        return False, None

    if trigger_type == "variable_income":
        if signals["income_stability"] == "variable":
            return True, "Your income varies month to month — planning around the low end helps."
        return False, None

    if trigger_type == "digital_safety":
        # Show to everyone once
        return True, "Protecting your account and PIN is fundamental to financial safety."

    if trigger_type == "budgeting":
        # General budgeting lesson — show to anyone
        return True, "A budget helps you know where your money goes each month."

    if trigger_type == "saving_habit":
        # Show to anyone with a health score
        return True, "Small, regular savings build up over time without feeling painful."

    return False, None


def get_all_lessons(db: Session, category: str | None = None) -> list[FinancialLesson]:
    q = select(FinancialLesson).where(FinancialLesson.active == True)
    if category and category != "all":
        q = q.where(FinancialLesson.category == category)
    q = q.order_by(FinancialLesson.id)
    return list(db.scalars(q).all())


def get_personalized_lessons(db: Session, user: User) -> tuple[list[tuple[FinancialLesson, str | None]], list[tuple[FinancialLesson, str | None]]]:
    """Return (featured, for_you) tuples of (lesson, trigger_reason)."""
    all_lessons = get_all_lessons(db)
    signals = _get_user_signals(db, user)

    matched = []
    for lesson in all_lessons:
        matched_flag, reason = _match_triggers(lesson, signals, user)
        if matched_flag:
            matched.append((lesson, reason))

    # The order is deterministic. A behaviour change should lead, then a
    # practical next step, then durable foundations such as safety.
    priority = {
        "high_grocery": 1, "high_food": 1, "high_transport": 1,
        "frequent_cashout": 2, "low_emergency": 2, "savings_goal": 3,
        "variable_income": 3, "new_mfs": 4, "budgeting": 5,
        "saving_habit": 6, "digital_safety": 7,
    }
    matched.sort(key=lambda item: (priority.get(item[0].trigger_type, 99), item[0].id))

    # Featured = highest-priority deterministic signal. Keep the following
    # cards compact so the recommendation remains the visual focus.
    featured = matched[:1] if matched else []
    for_you = matched[1:6] if len(matched) > 1 else []
    return featured, for_you


def get_lesson_detail(db: Session, lesson_id: int, user_id: int) -> tuple[FinancialLesson | None, LessonProgress | None, str | None]:
    lesson = db.scalars(select(FinancialLesson).where(FinancialLesson.id == lesson_id)).first()
    if not lesson:
        return None, None, None

    progress = db.scalars(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id
        )
    ).first()

    # Compute trigger reason
    from sqlalchemy import select as sa_select
    user_obj = db.scalars(select(User).where(User.id == user_id)).first()
    if user_obj:
        signals = _get_user_signals(db, user_obj)
        _, reason = _match_triggers(lesson, signals, user_obj)
    else:
        reason = None

    return lesson, progress, reason


def start_lesson(db: Session, user_id: int, lesson_id: int) -> LessonProgress:
    existing = db.scalars(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id
        )
    ).first()

    if existing:
        if existing.started_at is None:
            existing.started_at = datetime.utcnow()
        db.commit()
        return existing

    progress = LessonProgress(user_id=user_id, lesson_id=lesson_id, started_at=datetime.utcnow())
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def complete_lesson(db: Session, user_id: int, lesson_id: int, quiz_answer: str | None = None) -> tuple[LessonProgress, int | None]:
    progress = db.scalars(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id
        )
    ).first()

    lesson = db.scalars(select(FinancialLesson).where(FinancialLesson.id == lesson_id)).first()
    quiz_score = None
    if lesson and quiz_answer and lesson.quiz:
        correct = lesson.quiz.get("correct_key") if isinstance(lesson.quiz, dict) else None
        quiz_score = 1 if quiz_answer == correct else 0

    if progress:
        progress.completed_at = datetime.utcnow()
        progress.quiz_score = quiz_score
    else:
        progress = LessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            quiz_score=quiz_score
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return progress, quiz_score


def get_progress_summary(db: Session, user_id: int) -> list[dict]:
    """Return per-category completion counts."""
    rows = db.execute(
        select(
            FinancialLesson.category,
            func.count(FinancialLesson.id).label("total")
        )
        .where(FinancialLesson.active == True)
        .group_by(FinancialLesson.category)
    ).all()

    completed_rows = dict(db.execute(
        select(
            FinancialLesson.category,
            func.count(LessonProgress.id).label("completed")
        )
        .join(LessonProgress, LessonProgress.lesson_id == FinancialLesson.id)
        .where(LessonProgress.user_id == user_id, LessonProgress.completed_at.isnot(None))
        .group_by(FinancialLesson.category)
    ).all())

    result = []
    for row in rows:
        cat = row[0]
        total = row[1]
        result.append({
            "category": cat,
            "completed": completed_rows.get(cat, 0),
            "total": total
        })
    return result


def get_user_completed_lesson_ids(db: Session, user_id: int) -> set[int]:
    rows = db.scalars(
        select(LessonProgress.lesson_id).where(
            LessonProgress.user_id == user_id,
            LessonProgress.completed_at.isnot(None)
        )
    ).all()
    return set(rows)


def get_user_started_lesson_ids(db: Session, user_id: int) -> set[int]:
    rows = db.scalars(
        select(LessonProgress.lesson_id).where(
            LessonProgress.user_id == user_id,
            LessonProgress.started_at.isnot(None)
        )
    ).all()
    return set(rows)
