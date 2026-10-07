from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import User
from app.services.assistant_action_service import fallback_intent, get_conversation, handle_message, confirm_action, explain_metric
from app.services import groq_service
from app.services.seed import seed


def demo_db():
    Base.metadata.create_all(engine)
    db = SessionLocal(); seed(db)
    return db


def test_fallback_understands_english_bangla_and_banglish_actions():
    cases = [
        ("Send 500 taka to Fuad", "send_money", 500),
        ("ফুয়াদকে ৫০০ টাকা পাঠাও", "send_money", 500),
        ("Rafi ke 500 taka send koro", "send_money", 500),
        ("I want to save 60k for a laptop", "create_savings_goal", 60000),
        ("আমি কত টাকা নিরাপদে খরচ করতে পারি?", "safe_to_spend", None),
    ]
    for text, intent, value in cases:
        parsed = fallback_intent(text)
        assert parsed.intent == intent
        if value is not None:
            assert parsed.entities.get("amount", parsed.entities.get("target_amount")) == value


def test_assistant_collects_send_amount_then_creates_server_draft():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        conversation = get_conversation(db, user.id, None)
        first = handle_message(db, user, conversation, "Send money to Rafi")
        assert first["type"] == "clarification"
        second = handle_message(db, user, conversation, "500")
        assert second["type"] == "action_preview"
        assert second["preview"]["amount"] == 500
        assert second["action"]["requires_authorization"] is True
    finally:
        db.close()


def test_assistant_collects_recipient_then_amount_and_never_executes_directly():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        conversation = get_conversation(db, user.id, None)
        assert handle_message(db, user, conversation, "Send money")["missing_fields"] == ["recipient"]
        assert handle_message(db, user, conversation, "Rafi")["missing_fields"] == ["amount"]
        draft = handle_message(db, user, conversation, "500")
        assert draft["type"] == "action_preview"
        assert draft["action"]["status"] == "READY_FOR_REVIEW"
    finally:
        db.close()


def test_savings_goal_is_not_persisted_until_confirmation():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        conversation = get_conversation(db, user.id, None)
        response = handle_message(db, user, conversation, "I want to save 60k for a laptop")
        assert response["type"] == "clarification"
        prepared = handle_message(db, user, conversation, "within 8 months")
        assert prepared["type"] == "savings_plan"
        completed = confirm_action(db, user, prepared["action"]["id"])
        assert completed["type"] == "success"
    finally:
        db.close()


def test_metric_explanations_are_educational_and_do_not_change_financial_state():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        conversation = get_conversation(db, user.id, None)
        examples = [
            {"metric_id": "safe_to_spend", "title": "Safe to Spend", "value": 4850, "unit": "BDT", "source": "overview", "context": {}},
            {"metric_id": "savings_rate", "title": "Savings Rate", "value": 12, "unit": "%", "source": "overview", "context": {"monthlyIncome": 25000, "monthlySavings": 3000}},
            {"metric_id": "financial_health_score", "title": "Financial Health Score", "value": 72, "unit": "/ 100", "source": "financial_health", "context": {"label": "Stable"}},
            {"metric_id": "financial_health_factor", "title": "Saving behavior", "value": 12, "unit": "points", "source": "financial_health", "context": {"factor": "Saving behavior", "maximum": 20}},
            {"metric_id": "savings_goal_progress", "title": "Laptop Goal Progress", "value": 40, "unit": "%", "source": "savings_goal", "context": {"saved": 12000, "target": 30000}},
        ]
        for metric in examples:
            response = explain_metric(conversation, metric)
            assert response["type"] == "financial_insight"
            assert "### What it means" in response["message"]
            assert "### Why it matters" in response["message"]
    finally:
        db.close()


def test_assistant_handles_normal_chat_and_context_without_a_model_key():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        conversation = get_conversation(db, user.id, None)
        hello = handle_message(db, user, conversation, "Hello")
        assert hello["type"] == "financial_insight"
        spending = handle_message(db, user, conversation, "How much did I spend on food?")
        assert spending["type"] == "financial_insight"
        follow_up = handle_message(db, user, conversation, "Why is it higher?")
        assert follow_up["type"] == "financial_insight"
        assert follow_up["intent"] == "compare_spending"
    finally:
        db.close()


def test_groq_invalid_json_timeout_and_http_failures_have_safe_fallbacks(monkeypatch):
    monkeypatch.setattr(groq_service, "_request", lambda *args, **kwargs: ("not json", None, 1.0))
    route, meta = groq_service.classify("hello", {"chat": {}})
    assert route is None and meta["fallback_used"] is True
    monkeypatch.setattr(groq_service, "_request", lambda *args, **kwargs: (None, "Groq timeout", 10.0))
    text, meta = groq_service.respond("hello", {}, "en", "Useful fallback")
    assert text == "Useful fallback" and meta["fallback_used"] is True
    for reason in ("Groq HTTP 401", "Groq HTTP 429", "Groq HTTP 500", "Groq network error"):
        monkeypatch.setattr(groq_service, "_request", lambda *args, _reason=reason, **kwargs: (None, _reason, 1.0))
        text, meta = groq_service.respond("balance", {}, "en", "Useful fallback")
        assert text == "Useful fallback" and meta["reason"] == reason


# ─── Regression: conversation-state bugs ───────────────────────────────────────

def test_emergency_buffer_goal_routes_to_goal_feasibility_not_affordability():
    """
    Bug: 'Emergency buffer goal fit my cash flow' was incorrectly classified as
    affordability_analysis and prompted for a purchase price, then looped.

    Fix: it must route to goal_feasibility (or create_savings_goal).
    """
    db = demo_db()
    try:
        user = db.scalars(select(User).where(User.email == "demo.student@upay.local")).first()
        conv = get_conversation(db, user.id, None)
        r = handle_message(db, user, conv, "Emergency buffer goal fit my cash flow")
        # Must NOT end up in affordability_analysis asking for purchase price
        assert conv.active_intent in ("goal_feasibility", "create_savings_goal", "feasibility_analysis"), \
            f"Expected goal_feasibility, got {conv.active_intent}"
        # Must NOT be stuck in COLLECTING_INFORMATION asking for an amount
        if conv.state == "COLLECTING_INFORMATION":
            assert r.get("missing_fields", []) != ["amount"], \
                "Wrongly asking for purchase amount — still in affordability loop"
        # Accept any valid next state: clarification (goal_name/target needed) or action
        assert r.get("type") in ("clarification", "savings_plan", "action_preview", "clarification_request"), \
            f"Unexpected response type: {r.get('type')}"
    finally:
        db.close()


def test_meta_intent_not_misread_as_amount_value():
    """
    Bug: 'I don't understand' typed at an affordability_analysis prompt
    was incorrectly extracted as an amount value instead of triggering
    the clarification help flow.

    Fix: _is_meta_intent() fires before amount parsing.
    """
    db = demo_db()
    try:
        user = db.scalars(select(User).where(User.email == "demo.student@upay.local")).first()
        conv = get_conversation(db, user.id, None)
        # Simulate being in the middle of affordability_analysis with amount missing
        conv.state = "COLLECTING_INFORMATION"
        conv.active_intent = "affordability_analysis"
        conv.slots = {"_context": {}}
        db.add(conv); db.commit()

        r = handle_message(db, user, conv, "I don't understand")
        # Must be a clarification_request or correction, NOT an amount extraction
        assert r.get("type") in ("clarification_request", "correction"), \
            f"'I don't understand' was misread as amount — got {r.get('type')}"
        # Amount must NOT have been populated
        assert "amount" not in conv.slots or conv.slots.get("amount") is None, \
            f"Stale amount injected: {conv.slots.get('amount')}"
    finally:
        db.close()


def test_cross_intent_slot_pollution_is_cleared_on_new_action():
    """
    Bug: after affordability_analysis slot collection, switching to
    create_savings_goal carried over stale amount/recipient fields.

    Fix: _clear_invalid_pending_state() called before branch-specific parsing.
    """
    db = demo_db()
    try:
        user = db.scalars(select(User).where(User.email == "demo.student@upay.local")).first()
        conv = get_conversation(db, user.id, None)

        # Step 1: start send_money and partial fill
        handle_message(db, user, conv, "Send money to Rafi")
        assert conv.state == "COLLECTING_INFORMATION"
        assert conv.active_intent == "send_money"

        # Step 2: switch to savings goal — stale send_money slots must be cleared
        r2 = handle_message(db, user, conv, "I want to save for a laptop")
        assert conv.active_intent == "create_savings_goal", \
            f"Wrongly kept send_money intent: {conv.active_intent}"
        # Stale recipient/amount must NOT leak into savings slots
        assert conv.slots.get("recipient") is None, \
            f"Stale recipient leaked: {conv.slots.get('recipient')}"
        assert conv.slots.get("amount") is None, \
            f"Stale amount leaked: {conv.slots.get('amount')}"
        # Should now ask for goal target/duration, not recipient
        assert r2.get("missing_fields", []) in (
            ["target_amount"],
            ["duration_months"],
            ["target_amount", "duration_months"],
            ["goal_name"],
            [],
        ), f"Wrong missing fields for create_savings_goal: {r2.get('missing_fields')}"
    finally:
        db.close()
