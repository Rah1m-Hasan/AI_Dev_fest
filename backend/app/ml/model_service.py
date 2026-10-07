"""Cached runtime model loading with safe, non-ML failure behavior."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from app.ml.feature_engineering import FEATURE_NAMES, RISK_FEATURE_NAMES, build_risk_features, extract_spending_features


DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "models"


class ModelService:
    def __init__(self, model_dir: Path | None = None):
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self._spending_bundle: dict[str, Any] | None = None
        self._risk_bundle: dict[str, Any] | None = None
        self._loaded = False

    def load(self) -> bool:
        """Load local artifacts once. Any failure means normal fallback behavior."""
        if self._loaded:
            return self.available
        self._loaded = True
        try:
            import joblib
            spending = self.model_dir / "spending_forecast.joblib"
            risk = self.model_dir / "risk_classifier.joblib"
            if spending.exists():
                bundle = joblib.load(spending)
                if tuple(bundle.get("feature_names", ())) == FEATURE_NAMES:
                    self._spending_bundle = bundle
            if risk.exists():
                bundle = joblib.load(risk)
                if tuple(bundle.get("feature_names", ())) == RISK_FEATURE_NAMES:
                    self._risk_bundle = bundle
        except Exception:
            self._spending_bundle = None
            self._risk_bundle = None
        return self.available

    @property
    def available(self) -> bool:
        return self._spending_bundle is not None and self._risk_bundle is not None

    def spending_prediction(self, transactions: Iterable[Any], *, current_balance: float, monthly_income: float | None = None) -> dict[str, Any] | None:
        self.load()
        if self._spending_bundle is None:
            return None
        try:
            features = extract_spending_features(transactions, current_balance=current_balance, monthly_income=monthly_income)
            vector = [[features[name] for name in FEATURE_NAMES]]
            predicted = self._spending_bundle["model"].predict(vector)[0]
            return {
                "predicted_7_day_spending": round(max(0.0, float(predicted[0])), 2),
                "predicted_30_day_spending": round(max(0.0, float(predicted[1])), 2),
                "model": "RandomForestRegressor",
                "source": "ml",
                "features": features,
            }
        except Exception:
            return None

    def risk_prediction(self, transactions: Iterable[Any], *, current_balance: float, expected_7_day_spending: float, monthly_income: float | None = None) -> dict[str, Any] | None:
        self.load()
        if self._risk_bundle is None:
            return None
        try:
            spending = extract_spending_features(transactions, current_balance=current_balance, monthly_income=monthly_income)
            features = build_risk_features(spending, expected_7_day_spending)
            model = self._risk_bundle["model"]
            probabilities = model.predict_proba([[features[name] for name in RISK_FEATURE_NAMES]])[0]
            probability_map = {str(label): round(float(value), 4) for label, value in zip(model.classes_, probabilities)}
            level = str(model.predict([[features[name] for name in RISK_FEATURE_NAMES]])[0])
            return {"risk_level": level, "probabilities": probability_map, "model": "RandomForestClassifier", "source": "ml", "features": features}
        except Exception:
            return None


@lru_cache(maxsize=1)
def get_model_service() -> ModelService:
    return ModelService()
