"""Regression coverage for deterministic Learn and Offers personalisation."""
from sqlalchemy import select

from app.models import User
from app.services.learning_service import get_personalized_lessons
from app.services.offers_service import _update_preference, get_all_offers
from app.services.seed import seed
from app.db import Base, SessionLocal, engine


def demo_db():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed(db)
    return db


def test_learn_recommendations_are_persona_signals_not_names():
    db = demo_db()
    try:
        arif = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        samiha = db.scalar(select(User).where(User.email == "demo.freelancer@upay.local"))
        arif_featured, _ = get_personalized_lessons(db, arif)
        samiha_featured, _ = get_personalized_lessons(db, samiha)
        assert arif_featured and samiha_featured
        assert arif_featured[0][0].trigger_type != samiha_featured[0][0].trigger_type
        assert arif_featured[0][1] and samiha_featured[0][1]
    finally:
        db.close()


def test_offers_hide_behavioral_fit_when_personalization_is_off():
    db = demo_db()
    try:
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        personalised, _ = get_all_offers(db, user.id)
        assert personalised
        assert all(item["why_relevant"] for item in personalised)
        assert all(item["typical_purchase"] is not None for item in personalised)

        _update_preference(db, user.id, False)
        general, preferences = get_all_offers(db, user.id)
        assert preferences["personalized_offers_enabled"] is False
        assert all(item["fit_status"] is None for item in general)
        assert all(item.get("why_relevant") is None for item in general)
        _update_preference(db, user.id, True)
    finally:
        db.close()
