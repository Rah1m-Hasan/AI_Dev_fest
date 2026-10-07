"""Coverage for optional ML behavior and its deterministic safety net."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.ml.feature_engineering import FEATURE_NAMES, extract_spending_features
from app.ml.model_service import ModelService
from app.ml.synthetic_data import generate_synthetic_samples
from app.ml.train_models import train_models
from app.models import User
from app.services.safe_to_spend_service import calculate_safe_to_spend
from app.services.seed import seed


def test_synthetic_dataset_is_reproducible_and_behavior_labelled():
    first = generate_synthetic_samples(500, seed=42)
    second = generate_synthetic_samples(500, seed=42)
    assert first == second
    assert len(first) == 500
    assert {row["risk_level"] for row in first} == {"LOW", "MEDIUM", "HIGH"}
    assert all(row["next_7_day_spending"] > 0 and row["next_30_day_spending"] > 0 for row in first)


def test_feature_engineering_handles_malformed_transaction_data():
    now = datetime.now()
    features = extract_spending_features([
        {"timestamp": now.isoformat(), "amount": "220", "direction": "expense", "category": "Food", "transaction_type": "merchant_payment"},
        {"timestamp": "not-a-date", "amount": "bad", "direction": "expense"},
        {"timestamp": (now - timedelta(days=1)).isoformat(), "amount": 500, "direction": "income", "category": "Income", "transaction_type": "salary"},
        {"timestamp": (now - timedelta(days=2)).isoformat(), "amount": 999, "direction": "out", "category": "Transfers", "transaction_type": "transfer"},
    ], current_balance="1200")
    assert tuple(features) == FEATURE_NAMES
    assert features["total_spending_7"] == 220
    assert features["monthly_income"] == 500
    assert features["current_balance"] == 1200


@pytest.fixture(scope="module")
def trained_model_dir(tmp_path_factory):
    output = tmp_path_factory.mktemp("ml-models")
    train_models(sample_count=700, data_dir=output / "data", model_dir=output / "models")
    return output / "models"


def test_model_loading_spending_and_risk_predictions(trained_model_dir):
    service = ModelService(trained_model_dir)
    transactions = [
        {"timestamp": (datetime.now() - timedelta(days=day)).isoformat(), "amount": 200 + day * 3, "direction": "expense", "category": "Food", "transaction_type": "merchant_payment"}
        for day in range(1, 31)
    ] + [{"timestamp": (datetime.now() - timedelta(days=5)).isoformat(), "amount": 22000, "direction": "income", "category": "Income", "transaction_type": "salary"}]
    spending = service.spending_prediction(transactions, current_balance=8500)
    assert service.load() and spending and spending["source"] == "ml"
    assert spending["predicted_7_day_spending"] > 0
    risk = service.risk_prediction(transactions, current_balance=8500, expected_7_day_spending=spending["predicted_7_day_spending"])
    assert risk and risk["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert abs(sum(risk["probabilities"].values()) - 1) < .001


def test_missing_model_has_no_prediction_and_safe_to_spend_still_works(tmp_path, monkeypatch):
    assert ModelService(tmp_path).spending_prediction([], current_balance=1000) is None
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
        user = db.scalar(select(User).where(User.email == "demo.student@upay.local"))
        import app.services.safe_to_spend_service as safe_module
        monkeypatch.setattr(safe_module, "forecast", lambda *_args, **_kwargs: {"predicted_recurring_expenses": [], "source": "deterministic_fallback"})
        safe = calculate_safe_to_spend(db, user)
        assert safe["forecast_source"] == "deterministic_fallback"
        assert safe["forecasted_necessary_spending"] == 0
        assert safe["safe_to_spend"] >= 0


@pytest.mark.anyio
async def test_ml_api_shapes_and_metrics_endpoint(client):
    login = await client.post("/api/v1/auth/login", json={"email": "demo.student@upay.local"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    forecast = (await client.get("/api/v1/ml/forecast", headers=headers))
    risk = (await client.get("/api/v1/ml/risk", headers=headers))
    summary = (await client.get("/api/v1/ml/summary", headers=headers))
    metrics = (await client.get("/api/v1/ml/metrics", headers=headers))
    assert forecast.status_code == risk.status_code == summary.status_code == metrics.status_code == 200
    assert {"predicted_7_day_spending", "predicted_30_day_spending", "source"} <= forecast.json().keys()
    assert {"risk_level", "source"} <= risk.json().keys()
    assert {"predicted_7_day_spending", "financial_risk", "safe_to_spend", "money_runway_days"} <= summary.json().keys()
    assert "available" in metrics.json()
