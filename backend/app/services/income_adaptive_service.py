"""Income-Adaptive Coach service.

Analyzes variable income patterns for freelancers, gig workers, and irregular-income users.
All calculations are deterministic - LLM only explains the results.
"""
from decimal import Decimal
from statistics import pstdev
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Transaction, User
from app.services.analytics_service import _tx, _money, is_income, dec, amount


def calculate_income_adaptive(db: Session, user: User) -> dict:
    """Calculate income-adaptive insights for a user.

    For variable-income users (freelancers, small business owners, etc.),
    provides analysis of recent income patterns and savings recommendations.
    """
    from datetime import datetime, timedelta

    now = datetime.now()

    # Get last 30 days of transactions
    recent_30 = _tx(db, user.id, now - timedelta(days=30), now)
    recent_7 = _tx(db, user.id, now - timedelta(days=7), now)

    # Calculate income for different windows
    income_7_days = _money(recent_7, True)
    income_30_days = _money(recent_30, True)

    # Calculate weekly averages
    weeks = []
    for i in range(4):
        week_start = now - timedelta(days=(i + 1) * 7)
        week_end = now - timedelta(days=i * 7)
        week_tx = _tx(db, user.id, week_start, week_end)
        week_income = _money(week_tx, True)
        weeks.append(float(week_income))

    average_weekly_income = sum(weeks) / len(weeks) if weeks else 0
    income_variability = pstdev(weeks) / average_weekly_income if average_weekly_income > 0 else 0

    # Determine income pattern
    variable_personas = {"freelancer", "small business owner"}
    is_variable = user.persona in variable_personas or income_variability > 0.25

    income_pattern = "variable" if is_variable else "steady"

    # Calculate difference from average
    if average_weekly_income > 0:
        difference_percent = (float(income_7_days) - average_weekly_income) / average_weekly_income * 100
    else:
        difference_percent = 0

    # Get upcoming expenses
    from app.services.analytics_service import forecast
    fc = forecast(db, user, 14)
    upcoming_expenses = sum(
        Decimal(str(x["amount"]))
        for x in fc.get("predicted_recurring_expenses", [])
    )

    # Calculate suggested savings range
    # Based on income being above/below average and upcoming expenses
    recent_savings_capacity = max(Decimal("0"), dec(income_7_days) - upcoming_expenses)

    if difference_percent > 10:
        # Income above average - suggest saving a portion
        suggested_savings_min = float(recent_savings_capacity * Decimal("0.30"))
        suggested_savings_max = float(recent_savings_capacity * Decimal("0.50"))
        reason_codes = ["income_above_recent_average"]
    elif difference_percent < -10:
        # Income below average - be more conservative
        suggested_savings_min = float(recent_savings_capacity * Decimal("0.10"))
        suggested_savings_max = float(recent_savings_capacity * Decimal("0.25"))
        reason_codes = ["income_below_recent_average"]
    else:
        # Income roughly normal
        suggested_savings_min = float(recent_savings_capacity * Decimal("0.20"))
        suggested_savings_max = float(recent_savings_capacity * Decimal("0.40"))
        reason_codes = ["income_typical"]

    if upcoming_expenses < Decimal("2000"):
        reason_codes.append("low_upcoming_expenses")
    elif upcoming_expenses > Decimal("5000"):
        reason_codes.append("high_upcoming_expenses")

    # Build evidence
    evidence = [
        f"Income in last 7 days: ৳{amount(income_7_days):,.0f}",
        f"Average weekly income: ৳{average_weekly_income:,.0f}",
        f"4-week income variability: {income_variability * 100:.0f}%",
        f"Upcoming 14-day expenses: ৳{amount(upcoming_expenses):,.0f}",
    ]

    # Build explanation
    if difference_percent > 15:
        explanation = (
            f"Your income this week is approximately {abs(difference_percent):.0f}% "
            f"above your recent weekly average. "
        )
    elif difference_percent < -15:
        explanation = (
            f"Your income this week is approximately {abs(difference_percent):.0f}% "
            f"below your recent weekly average. "
        )
    else:
        explanation = (
            f"Your income this week is close to your typical weekly average. "
        )

    if upcoming_expenses < Decimal("2000"):
        explanation += "No major expense is expected during the next few days."
    elif upcoming_expenses > Decimal("5000"):
        explanation += "Several expenses are expected in the next 14 days."
    else:
        explanation += "Some expenses are expected in the next 14 days."

    return {
        "income_last_7_days": amount(income_7_days),
        "income_last_30_days": amount(income_30_days),
        "average_weekly_income": round(average_weekly_income, 2),
        "difference_percent": round(difference_percent, 2),
        "income_pattern": income_pattern,
        "income_variability_percent": round(income_variability * 100, 1),
        "upcoming_expenses": amount(upcoming_expenses),
        "suggested_savings_min": round(max(0, suggested_savings_min), 2),
        "suggested_savings_max": round(max(0, suggested_savings_max), 2),
        "reason_codes": reason_codes,
        "evidence": evidence,
        "explanation": explanation,
    }
