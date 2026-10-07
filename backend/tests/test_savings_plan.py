from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import User
from app.services.assistant_action_service import fallback_intent, get_conversation, handle_message
from app.services.savings_plan_service import add_calendar_months, calculate_savings_plan
from app.services.seed import seed


def demo_db():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed(db)
    return db


@pytest.mark.parametrize(("message", "target", "months", "goal"), [
    ("save 2000 tk in 2 months for TV", 2000, 2, "TV"),
    ("save 2k for TV in 2 months", 2000, 2, "TV"),
    ("TV er jonno 2 mashe 2000 taka save korte chai", 2000, 2, "TV"),
    ("2 month er moddhe 2k save korte chai TV er jonno", 2000, 2, "TV"),
    ("আমি ২০ হাজার টাকা ২ মাসে টিভির জন্য সেভ করতে চাই", 20000, 2, "টিভি"),
])
def test_savings_entity_extraction_keeps_money_and_duration_separate(message, target, months, goal):
    parsed = fallback_intent(message)
    assert parsed.intent == "create_savings_goal"
    assert parsed.entities["target_amount"] == target
    assert parsed.entities["duration_months"] == months
    assert parsed.entities["goal_name"] == goal


@pytest.mark.parametrize("target,current,months,expected_remaining,expected_monthly", [
    ("2000", "0", 2, "2000", "1000"),
    ("20000", "0", 2, "20000", "10000"),
    ("12000", "0", 6, "12000", "2000"),
    ("20000", "5000", 3, "15000", "5000"),
    ("10000", "0", 3, "10000", "3334"),  # whole-taka-up prevents underfunding
])
def test_authoritative_savings_calculation(target, current, months, expected_remaining, expected_monthly):
    result = calculate_savings_plan(
        goal_name="Test",
        target_amount=Decimal(target),
        current_amount=Decimal(current),
        duration_months=months,
        today=date(2026, 10, 7),
    )
    assert result.remaining_amount == Decimal(expected_remaining)
    assert result.required_monthly_contribution == Decimal(expected_monthly)
    assert result.deadline == add_calendar_months(date(2026, 10, 7), months)


def test_exact_regression_request_returns_typed_savings_plan_preview():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        response = handle_message(db, user, get_conversation(db, user.id, None), "i want to save 2000tk in 2 months for tc")
        preview = response["preview"]
        assert response["type"] == "savings_plan"
        assert preview["goal_name"] == "TC"
        assert preview["target_amount"] == 2000
        assert preview["duration_months"] == 2
        assert preview["required_monthly_contribution"] == 1000
        assert preview["deadline"] == add_calendar_months(date.today(), 2).isoformat()
        assert "recommended_monthly_contribution" not in preview
        assert {field["key"]: field["value_type"] for field in preview["display_fields"]} == {
            "goal_name": "text", "target_amount": "currency", "duration_months": "months",
            "deadline": "date", "required_monthly_contribution": "currency",
            "affordable_monthly_contribution": "currency",
        }
    finally:
        db.close()


def test_new_intent_clears_collecting_savings_slots():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        conversation = get_conversation(db, user.id, None)
        assert handle_message(db, user, conversation, "save 2000 tk for TV")["type"] == "clarification"
        response = handle_message(db, user, conversation, "send 1000 tk to Rafi")
        assert response["type"] in {"action_preview", "selection"}
        assert response["type"] != "savings_plan"
        if response["type"] == "action_preview":
            assert response["action"]["name"] == "send_money"
            assert response["preview"]["amount"] == 1000
    finally:
        db.close()


@pytest.mark.parametrize("message", ["save 0 tk in 2 months", "save 2000 tk in 0 months", "save -500 tk in 2 months"])
def test_invalid_savings_inputs_do_not_create_a_plan(message):
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        response = handle_message(db, user, get_conversation(db, user.id, None), message)
        assert response["type"] in {"clarification", "error"}
    finally:
        db.close()
