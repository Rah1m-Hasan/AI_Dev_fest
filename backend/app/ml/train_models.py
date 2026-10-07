"""Manual training entry point: ``python -m app.ml.train_models``."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ml.feature_engineering import FEATURE_NAMES, RISK_FEATURE_NAMES
from app.ml.synthetic_data import generate_synthetic_samples, save_synthetic_dataset


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = PACKAGE_DIR / "data"
DEFAULT_MODEL_DIR = PACKAGE_DIR / "models"


def train_models(*, sample_count: int = 8000, seed: int = 42, data_dir: Path | None = None, model_dir: Path | None = None) -> dict[str, Any]:
    """Generate data, train compact CPU models, and persist real holdout metrics."""
    try:
        import joblib
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, mean_absolute_error, precision_score, r2_score, recall_score, root_mean_squared_error, roc_auc_score
        from sklearn.model_selection import train_test_split
    except ImportError as error:  # Makes a missing optional dependency explicit to manual users.
        raise RuntimeError("scikit-learn and joblib are required to train the optional ML models") from error

    data_dir = data_dir or DEFAULT_DATA_DIR
    model_dir = model_dir or DEFAULT_MODEL_DIR
    rows = generate_synthetic_samples(sample_count=sample_count, seed=seed)
    dataset_path = save_synthetic_dataset(rows, data_dir / "synthetic_financial_training.csv")
    x = np.array([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
    y_spending = np.array([[row["next_7_day_spending"], row["next_30_day_spending"]] for row in rows], dtype=float)
    y_risk = np.array([row["risk_level"] for row in rows])
    indices = np.arange(sample_count)
    train_idx, test_idx = train_test_split(indices, test_size=.20, random_state=42, stratify=y_risk)
    spending = RandomForestRegressor(n_estimators=90, max_depth=14, min_samples_leaf=3, n_jobs=-1, random_state=42)
    spending.fit(x[train_idx], y_spending[train_idx])
    predicted_spending = spending.predict(x[test_idx])
    classifier_x = np.array([[row[f"risk__{name}"] for name in RISK_FEATURE_NAMES] for row in rows], dtype=float)
    classifier = RandomForestClassifier(n_estimators=110, max_depth=14, min_samples_leaf=2, class_weight="balanced", n_jobs=-1, random_state=42)
    classifier.fit(classifier_x[train_idx], y_risk[train_idx])
    predicted_risk = classifier.predict(classifier_x[test_idx])
    risk_probabilities = classifier.predict_proba(classifier_x[test_idx])
    labels = ["LOW", "MEDIUM", "HIGH"]
    spending_7 = {
        "mae": round(float(mean_absolute_error(y_spending[test_idx, 0], predicted_spending[:, 0])), 4),
        "rmse": round(float(root_mean_squared_error(y_spending[test_idx, 0], predicted_spending[:, 0])), 4),
        "r2": round(float(r2_score(y_spending[test_idx, 0], predicted_spending[:, 0])), 6),
    }
    spending_30 = {
        "mae": round(float(mean_absolute_error(y_spending[test_idx, 1], predicted_spending[:, 1])), 4),
        "rmse": round(float(root_mean_squared_error(y_spending[test_idx, 1], predicted_spending[:, 1])), 4),
        "r2": round(float(r2_score(y_spending[test_idx, 1], predicted_spending[:, 1])), 6),
    }
    risk_metrics: dict[str, Any] = {
        "accuracy": round(float(accuracy_score(y_risk[test_idx], predicted_risk)), 6),
        "precision": round(float(precision_score(y_risk[test_idx], predicted_risk, average="weighted", zero_division=0)), 6),
        "recall": round(float(recall_score(y_risk[test_idx], predicted_risk, average="weighted", zero_division=0)), 6),
        "f1": round(float(f1_score(y_risk[test_idx], predicted_risk, average="weighted", zero_division=0)), 6),
        "confusion_matrix": confusion_matrix(y_risk[test_idx], predicted_risk, labels=labels).tolist(),
        "labels": labels,
        "classification_report": classification_report(y_risk[test_idx], predicted_risk, labels=labels, output_dict=True, zero_division=0),
    }
    try:
        risk_metrics["roc_auc"] = round(float(roc_auc_score(y_risk[test_idx], risk_probabilities, labels=classifier.classes_, multi_class="ovr", average="weighted")), 6)
    except ValueError:
        risk_metrics["roc_auc"] = None
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": spending, "feature_names": FEATURE_NAMES, "targets": ("next_7_day_spending", "next_30_day_spending"), "algorithm": "RandomForestRegressor"}, model_dir / "spending_forecast.joblib", compress=3)
    joblib.dump({"model": classifier, "feature_names": RISK_FEATURE_NAMES, "algorithm": "RandomForestClassifier"}, model_dir / "risk_classifier.joblib", compress=3)
    metrics = {
        "training_samples": sample_count,
        "test_samples": len(test_idx),
        "test_split": 0.20,
        "random_state": 42,
        "dataset": str(dataset_path.name),
        "spending_forecast": {**spending_7, "next_7_days": spending_7, "next_30_days": spending_30, "algorithm": "RandomForestRegressor", "features": list(FEATURE_NAMES)},
        "risk_classifier": {**risk_metrics, "algorithm": "RandomForestClassifier", "features": list(RISK_FEATURE_NAMES)},
    }
    with (model_dir / "model_metrics.json").open("w", encoding="utf-8") as output:
        json.dump(metrics, output, indent=2, default=float)
    return metrics


if __name__ == "__main__":
    result = train_models()
    print(json.dumps({"training_samples": result["training_samples"], "spending_forecast": result["spending_forecast"]["next_7_days"], "risk_classifier": {key: result["risk_classifier"][key] for key in ("accuracy", "precision", "recall", "f1", "roc_auc")}}, indent=2))
