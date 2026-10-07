"""Bridge optional ML predictions into the established finance engine."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.feature_engineering import extract_spending_features
from app.ml.model_service import DEFAULT_MODEL_DIR, get_model_service
from app.models import Transaction, User


def _history(db: Session, user_id: int, days: int = 60) -> list[Transaction]:
    now = datetime.now()
    return list(db.scalars(select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.timestamp >= now - timedelta(days=days),
        Transaction.timestamp <= now,
    ).order_by(Transaction.timestamp)).all())


def _deterministic_forecast(transactions: list[Transaction], balance: float) -> dict:
    features = extract_spending_features(transactions, current_balance=balance)
    return {
        "predicted_7_day_spending": round(max(0.0, features["avg_daily_spending_30"] * 7), 2),
        "predicted_30_day_spending": round(max(0.0, features["avg_daily_spending_30"] * 30), 2),
        "model": "historical spending average",
        "source": "deterministic_fallback",
        "features": features,
    }


def get_spending_forecast(db: Session, user: User) -> dict:
    transactions = _history(db, user.id)
    balance = float(user.account.balance)
    prediction = get_model_service().spending_prediction(transactions, current_balance=balance)
    return prediction or _deterministic_forecast(transactions, balance)


def _deterministic_risk(forecast: dict) -> dict:
    features = forecast["features"]
    income = max(1.0, features["monthly_income"])
    expected = forecast["predicted_7_day_spending"]
    bills = min(features["recurring_expenses_30"], features["recurring_expenses_30"] * 7 / 30)
    projected = features["current_balance"] - expected - bills
    runway = features["current_balance"] / max(1.0, features["avg_daily_spending_30"])
    spending_ratio = features["total_spending_30"] / income
    reserve_ratio = features["current_balance"] / income
    if projected < income * .08 or runway < 6 or (spending_ratio > .94 and reserve_ratio < .28):
        level = "HIGH"
    elif projected < income * .28 or runway < 16 or spending_ratio > .78 or reserve_ratio < .48:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {"risk_level": level, "model": "deterministic risk rules", "source": "deterministic_fallback"}


def get_financial_risk(db: Session, user: User, forecast: dict | None = None) -> dict:
    forecast = forecast or get_spending_forecast(db, user)
    transactions = _history(db, user.id)
    result = get_model_service().risk_prediction(
        transactions,
        current_balance=float(user.account.balance),
        expected_7_day_spending=forecast["predicted_7_day_spending"],
    )
    return result or _deterministic_risk(forecast)


def get_metrics() -> dict:
    path = DEFAULT_MODEL_DIR / "model_metrics.json"
    try:
        with path.open(encoding="utf-8") as metrics_file:
            metrics = json.load(metrics_file)
        return {"available": True, **metrics}
    except (OSError, ValueError, TypeError):
        return {"available": False, "source": "model metrics unavailable"}


def get_ml_summary(db: Session, user: User) -> dict:
    """One dashboard-ready response. Safety values always come from existing services."""
    from app.services.analytics_service import forecast, money_runway
    from app.services.safe_to_spend_service import calculate_safe_to_spend

    spending = get_spending_forecast(db, user)
    risk = get_financial_risk(db, user, spending)
    deterministic_30 = forecast(db, user, 30)
    safe = calculate_safe_to_spend(db, user)
    runway = money_runway(db, user)
    expected_month_end_balance = round(
        float(user.account.balance) + float(deterministic_30["expected_income"]) - spending["predicted_30_day_spending"], 2
    )
    response = {
        "predicted_7_day_spending": spending["predicted_7_day_spending"],
        "predicted_30_day_spending": spending["predicted_30_day_spending"],
        "predicted_month_end_balance": expected_month_end_balance,
        "financial_risk": risk["risk_level"],
        "safe_to_spend": safe["safe_to_spend"],
        "safe_to_spend_per_day": round(safe["safe_to_spend"] / max(1, safe["days"]), 2),
        "money_runway_days": runway["days"],
        "forecast_source": spending["source"],
        "risk_source": risk["source"],
    }
    if risk.get("probabilities"):
        response["risk_probability"] = risk["probabilities"].get(risk["risk_level"], 0.0)
    return response
