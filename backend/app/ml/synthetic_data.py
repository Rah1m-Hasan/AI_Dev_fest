"""Reproducible, behavior-based synthetic training data for lightweight models."""
from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

from app.ml.feature_engineering import FEATURE_NAMES, RISK_FEATURE_NAMES, build_risk_features


BEHAVIORS: dict[str, dict[str, float]] = {
    "low_income_student": {"income": 13000, "spend": .82, "balance": .32, "bills": .12, "weekend": .31, "volatility": .42, "frequency": 22},
    "salaried_employee": {"income": 42000, "spend": .62, "balance": .72, "bills": .20, "weekend": .20, "volatility": .18, "frequency": 28},
    "irregular_income_worker": {"income": 30000, "spend": .71, "balance": .42, "bills": .17, "weekend": .24, "volatility": .48, "frequency": 24},
    "high_spender": {"income": 50000, "spend": .96, "balance": .20, "bills": .15, "weekend": .33, "volatility": .40, "frequency": 38},
    "disciplined_saver": {"income": 48000, "spend": .48, "balance": 1.28, "bills": .19, "weekend": .17, "volatility": .14, "frequency": 20},
    "frequent_cash_out": {"income": 35000, "spend": .76, "balance": .38, "bills": .16, "weekend": .23, "volatility": .30, "frequency": 32},
    "high_bills": {"income": 55000, "spend": .73, "balance": .48, "bills": .35, "weekend": .18, "volatility": .20, "frequency": 23},
    "weekend_heavy": {"income": 39000, "spend": .68, "balance": .55, "bills": .14, "weekend": .44, "volatility": .32, "frequency": 30},
    "stable_spender": {"income": 36000, "spend": .59, "balance": .78, "bills": .18, "weekend": .21, "volatility": .10, "frequency": 25},
    "volatile_spender": {"income": 44000, "spend": .79, "balance": .29, "bills": .16, "weekend": .28, "volatility": .62, "frequency": 27},
}


def _positive(value: float) -> float:
    return round(max(0.0, value), 2)


def _risk_label(features: dict[str, float], expected_7: float) -> str:
    """Conceptual labels derived from cash pressure, never random classes."""
    balance = features["current_balance"]
    monthly_income = max(1.0, features["monthly_income"])
    obligations = features["recurring_expenses_30"] * 7.0 / 30.0
    projected = balance - expected_7 - obligations
    runway = balance / max(1.0, features["avg_daily_spending_30"])
    spending_ratio = features["total_spending_30"] / monthly_income
    reserve_ratio = balance / monthly_income
    if projected < monthly_income * .08 or runway < 6 or (spending_ratio > .94 and reserve_ratio < .28):
        return "HIGH"
    if projected < monthly_income * .28 or runway < 16 or spending_ratio > .78 or reserve_ratio < .48:
        return "MEDIUM"
    return "LOW"


def generate_synthetic_samples(sample_count: int = 8000, seed: int = 42) -> list[dict[str, Any]]:
    """Generate compact rows with financially meaningful target relationships."""
    if sample_count < 100:
        raise ValueError("sample_count must be at least 100")
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    profiles = list(BEHAVIORS.items())
    for index in range(sample_count):
        behavior_name, profile = profiles[index % len(profiles)]
        income = _positive(rng.gauss(profile["income"], profile["income"] * .16))
        spend_ratio = max(.30, min(1.10, rng.gauss(profile["spend"], .07)))
        monthly_spending = _positive(income * spend_ratio)
        trend = max(-.38, min(.48, rng.gauss(0.05 if behavior_name in {"high_spender", "volatile_spender"} else 0, profile["volatility"] * .34)))
        total_7 = _positive(monthly_spending * 7 / 30 * (1 + trend))
        previous_7 = _positive(monthly_spending * 7 / 30 * (1 - trend * .7))
        previous_30 = _positive(monthly_spending * rng.uniform(.82, 1.13))
        balance = _positive(income * rng.gauss(profile["balance"], .15))
        recurring = _positive(income * rng.gauss(profile["bills"], .035))
        transaction_count = max(3, int(rng.gauss(profile["frequency"], 5)))
        avg_tx = _positive(monthly_spending / transaction_count)
        weekend_ratio = max(.08, min(.62, rng.gauss(profile["weekend"], .05)))
        cash_out_ratio = .28 if behavior_name == "frequent_cash_out" else rng.uniform(.01, .12)
        feature = {
            "avg_daily_spending_7": total_7 / 7,
            "avg_daily_spending_30": monthly_spending / 30,
            "total_spending_7": total_7,
            "total_spending_30": monthly_spending,
            "transaction_count_7": max(1, round(transaction_count * 7 / 30)),
            "transaction_count_30": transaction_count,
            "average_transaction_amount": avg_tx,
            "maximum_recent_transaction": _positive(avg_tx * rng.uniform(2.2, 7.0)),
            "current_balance": balance,
            "monthly_income": income,
            "cash_out_spending_30": _positive(monthly_spending * cash_out_ratio),
            "send_money_spending_30": _positive(monthly_spending * rng.uniform(.01, .11)),
            "shopping_spending_30": _positive(monthly_spending * rng.uniform(.07, .24)),
            "food_spending_30": _positive(monthly_spending * rng.uniform(.18, .36)),
            "bills_spending_30": recurring,
            "mobile_recharge_spending_30": _positive(income * rng.uniform(.006, .025)),
            "recurring_expenses_30": recurring,
            "weekday_daily_spending": _positive(monthly_spending * (1 - weekend_ratio) / 22),
            "weekend_spending_ratio": weekend_ratio,
            "days_since_income": rng.randint(0, 35 if behavior_name == "irregular_income_worker" else 24),
            "previous_7_day_spending": previous_7,
            "previous_30_day_spending": previous_30,
            "spending_trend": trend,
            "balance_to_spending_ratio": balance / max(1, monthly_spending),
            "spending_volatility": max(.03, rng.gauss(profile["volatility"], .06)),
        }
        # The target follows observed pace, trend, bills and a small controlled noise term.
        next_7 = _positive((feature["avg_daily_spending_30"] * 7 * (1 + trend * .55) + recurring * 7 / 30) * rng.gauss(1, .055))
        next_30 = _positive((monthly_spending * (1 + trend * .35) + recurring * .10) * rng.gauss(1, .045))
        risk = build_risk_features(feature, next_7)
        rows.append({**{name: _positive(feature[name]) if name != "spending_trend" else round(feature[name], 6) for name in FEATURE_NAMES},
                     "next_7_day_spending": next_7, "next_30_day_spending": next_30,
                     "risk_level": _risk_label(feature, next_7), "behavior": behavior_name,
                     **{f"risk__{name}": risk[name] for name in RISK_FEATURE_NAMES}})
    return rows


def save_synthetic_dataset(rows: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else [*FEATURE_NAMES, "next_7_day_spending", "next_30_day_spending", "risk_level"]
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path
