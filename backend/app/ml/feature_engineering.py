"""Defensive, dependency-light transaction feature engineering."""
from __future__ import annotations

from datetime import datetime, timedelta
from math import isfinite
from statistics import pstdev
from typing import Any, Iterable


FEATURE_NAMES = (
    "avg_daily_spending_7",
    "avg_daily_spending_30",
    "total_spending_7",
    "total_spending_30",
    "transaction_count_7",
    "transaction_count_30",
    "average_transaction_amount",
    "maximum_recent_transaction",
    "current_balance",
    "monthly_income",
    "cash_out_spending_30",
    "send_money_spending_30",
    "shopping_spending_30",
    "food_spending_30",
    "bills_spending_30",
    "mobile_recharge_spending_30",
    "recurring_expenses_30",
    "weekday_daily_spending",
    "weekend_spending_ratio",
    "days_since_income",
    "previous_7_day_spending",
    "previous_30_day_spending",
    "spending_trend",
    "balance_to_spending_ratio",
    "spending_volatility",
)

RISK_FEATURE_NAMES = FEATURE_NAMES + (
    "expected_7_day_spending",
    "spending_to_income_ratio",
    "balance_runway_days",
    "emergency_reserve_ratio",
    "bills_due_next_7_days",
    "cash_out_ratio",
)


def _value(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _number(value: Any) -> float:
    try:
        result = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return result if isfinite(result) else 0.0


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _is_income(row: Any) -> bool:
    direction = str(_value(row, "direction", "")).lower()
    transaction_type = str(_value(row, "transaction_type", "")).lower()
    return direction == "income" and transaction_type not in {"transfer", "internal_transfer"}


def _is_spending(row: Any) -> bool:
    direction = str(_value(row, "direction", "")).lower()
    transaction_type = str(_value(row, "transaction_type", "")).lower()
    category = str(_value(row, "category", "")).lower()
    return direction in {"expense", "out"} and transaction_type not in {"transfer", "internal_transfer"} and category != "transfers"


def _normalised_rows(transactions: Iterable[Any], now: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in transactions or []:
        timestamp = _timestamp(_value(row, "timestamp"))
        if timestamp is None or timestamp > now + timedelta(days=1):
            continue
        rows.append({
            "timestamp": timestamp,
            "amount": max(0.0, _number(_value(row, "amount"))),
            "category": str(_value(row, "category", "")).strip().lower(),
            "transaction_type": str(_value(row, "transaction_type", "")).strip().lower(),
            "is_recurring": bool(_value(row, "is_recurring", False)),
            "income": _is_income(row),
            "spending": _is_spending(row),
        })
    return rows


def extract_spending_features(
    transactions: Iterable[Any],
    *,
    current_balance: float | int | None = None,
    monthly_income: float | int | None = None,
    now: datetime | None = None,
) -> dict[str, float]:
    """Return a fixed, finite feature dictionary from ORM rows or mappings.

    Missing/malformed records are ignored, rather than making a dashboard request
    fail.  Spending windows use calendar-day lookbacks relative to ``now``.
    """
    now = now or datetime.now()
    rows = _normalised_rows(transactions, now)
    spending = [row for row in rows if row["spending"]]
    incomes = [row for row in rows if row["income"]]

    def in_days(row: dict[str, Any], start_days: int, end_days: int = 0) -> bool:
        age = (now - row["timestamp"]).total_seconds() / 86400
        return end_days <= age < start_days

    def spend_total(days: int, end_days: int = 0) -> float:
        return sum(row["amount"] for row in spending if in_days(row, days, end_days))

    def spend_rows(days: int, end_days: int = 0) -> list[dict[str, Any]]:
        return [row for row in spending if in_days(row, days, end_days)]

    last_7 = spend_rows(7)
    last_30 = spend_rows(30)
    total_7 = sum(row["amount"] for row in last_7)
    total_30 = sum(row["amount"] for row in last_30)
    previous_7 = spend_total(14, 7)
    previous_30 = spend_total(60, 30)
    daily_values = [
        sum(row["amount"] for row in last_30 if row["timestamp"].date() == (now - timedelta(days=offset)).date())
        for offset in range(30)
    ]
    weekday_total = sum(row["amount"] for row in last_30 if row["timestamp"].weekday() < 5)
    weekend_total = sum(row["amount"] for row in last_30 if row["timestamp"].weekday() >= 5)
    income_30 = sum(row["amount"] for row in incomes if in_days(row, 30))
    latest_income = max((row["timestamp"] for row in incomes if row["timestamp"] <= now), default=None)
    balance = _number(current_balance)
    resolved_income = _number(monthly_income) if monthly_income is not None else income_30
    category_total = lambda names: sum(row["amount"] for row in last_30 if row["category"] in names)
    cash_out = category_total({"cash out", "cashout"})
    send_money = category_total({"send money", "transfers"}) + sum(
        row["amount"] for row in last_30 if "send" in row["transaction_type"]
    )
    avg_daily_30 = total_30 / 30.0
    previous_daily = previous_7 / 7.0
    feature_values = {
        "avg_daily_spending_7": total_7 / 7.0,
        "avg_daily_spending_30": avg_daily_30,
        "total_spending_7": total_7,
        "total_spending_30": total_30,
        "transaction_count_7": float(len(last_7)),
        "transaction_count_30": float(len(last_30)),
        "average_transaction_amount": total_30 / max(1, len(last_30)),
        "maximum_recent_transaction": max((row["amount"] for row in last_30), default=0.0),
        "current_balance": balance,
        "monthly_income": resolved_income,
        "cash_out_spending_30": cash_out,
        "send_money_spending_30": send_money,
        "shopping_spending_30": category_total({"shopping"}),
        "food_spending_30": category_total({"food", "groceries"}),
        "bills_spending_30": category_total({"bills", "rent", "subscriptions"}),
        "mobile_recharge_spending_30": category_total({"mobile recharge", "mobile_recharge"}),
        "recurring_expenses_30": sum(row["amount"] for row in last_30 if row["is_recurring"]),
        "weekday_daily_spending": weekday_total / 22.0,
        "weekend_spending_ratio": weekend_total / max(1.0, total_30),
        "days_since_income": float(min(90, (now - latest_income).days)) if latest_income else 90.0,
        "previous_7_day_spending": previous_7,
        "previous_30_day_spending": previous_30,
        "spending_trend": (total_7 / 7.0 - previous_daily) / max(1.0, previous_daily),
        "balance_to_spending_ratio": balance / max(1.0, total_30),
        "spending_volatility": pstdev(daily_values) / max(1.0, avg_daily_30),
    }
    return {name: round(max(-1_000_000_000.0, min(1_000_000_000.0, _number(feature_values[name]))), 6) for name in FEATURE_NAMES}


def build_risk_features(spending_features: dict[str, float], expected_7_day_spending: float) -> dict[str, float]:
    """Add short-term liquidity ratios used by the risk classifier."""
    values = {name: _number(spending_features.get(name)) for name in FEATURE_NAMES}
    expected = max(0.0, _number(expected_7_day_spending))
    income = values["monthly_income"]
    avg_daily = max(0.01, values["avg_daily_spending_30"])
    bills_due = min(values["recurring_expenses_30"], values["recurring_expenses_30"] * 7.0 / 30.0)
    values.update({
        "expected_7_day_spending": expected,
        "spending_to_income_ratio": values["total_spending_30"] / max(1.0, income),
        "balance_runway_days": min(365.0, values["current_balance"] / avg_daily),
        "emergency_reserve_ratio": values["current_balance"] / max(1.0, income),
        "bills_due_next_7_days": bills_due,
        "cash_out_ratio": values["cash_out_spending_30"] / max(1.0, values["total_spending_30"]),
    })
    return {name: round(_number(values[name]), 6) for name in RISK_FEATURE_NAMES}
