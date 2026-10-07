"""Safe-to-Spend Assistant service.

Deterministic calculation of how much the user can safely spend.
All amounts are calculated in Python - LLM only explains the results.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import User
from app.services.analytics_service import forecast, budget_recommendation, dec, amount


def calculate_safe_to_spend(db: Session, user: User, days: int = 7) -> dict:
    """Calculate safe-to-spend amount deterministically.

    safe_to_spend = available_balance
                            - upcoming_committed_expenses
                            - recommended_reserve
    """
    days = max(1, min(30, days))

    # Get current balance
    available_balance = dec(user.account.balance)

    # Get upcoming expenses from forecast
    fc = forecast(db, user, days)
    upcoming_expenses = sum(
        Decimal(str(x["amount"]))
        for x in fc.get("predicted_recurring_expenses", [])
    )

    # Keep a small portion of the user's current savings plan aside as a
    # commitment.  This is deliberately a 7-day prorated estimate, not a
    # promise that the money has already moved.
    rec = budget_recommendation(db, user)
    recommended_reserve = dec(rec.get("emergency_buffer", 1000))
    reserved_savings = max(Decimal("0"), dec(rec.get("savings_target", 0))) * Decimal(days) / Decimal("30.44")

    # Include only the non-recurring part of a trained forecast. Known recurring
    # bills are already listed as commitments above, so subtracting both in full
    # would double-count the same obligation. The deterministic fallback keeps
    # the original calculation unchanged.
    forecasted_necessary_spending = Decimal("0")
    if fc.get("source") == "ml":
        forecasted_necessary_spending = max(Decimal("0"), dec(fc.get("expected_expenses", 0)) - upcoming_expenses)

    # Calculate safe to spend; reserves and commitments remain authoritative.
    safe_to_spend = max(
        Decimal("0"),
        available_balance - upcoming_expenses - recommended_reserve - reserved_savings - forecasted_necessary_spending
    )

    # Build breakdown
    breakdown = {
        "available_balance": amount(available_balance),
        "upcoming_committed_expenses": amount(upcoming_expenses),
        "recommended_reserve": amount(recommended_reserve),
        "reserved_savings": amount(reserved_savings),
        "forecasted_necessary_spending": amount(forecasted_necessary_spending),
        "safe_to_spend": amount(safe_to_spend),
    }

    # Build upcoming expense details
    upcoming_details = [
        {
            "name": x["merchant"],
            "amount": x["amount"],
            "due_date": x["expected_date"],
            "expected_in_days": x["expected_in_days"],
        }
        for x in fc.get("predicted_recurring_expenses", [])
    ]

    return {
        "current_balance": amount(available_balance),
        "upcoming_committed_expenses": amount(upcoming_expenses),
        "recommended_reserve": amount(recommended_reserve),
        "reserved_savings": amount(reserved_savings),
        "forecasted_necessary_spending": amount(forecasted_necessary_spending),
        "forecast_source": fc.get("source", "deterministic_fallback"),
        "safe_to_spend": amount(safe_to_spend),
        "days": days,
        "breakdown": breakdown,
        "upcoming_expenses": upcoming_details,
        "evidence": [
            f"Available balance: ৳{amount(available_balance):,.0f}",
            f"Upcoming committed expenses: ৳{amount(upcoming_expenses):,.0f}",
            f"Recommended reserve: ৳{amount(recommended_reserve):,.0f}",
            f"Savings commitment: ৳{amount(reserved_savings):,.0f}",
            f"Forecasted necessary spending: ৳{amount(forecasted_necessary_spending):,.0f}",
            f"Safe-to-spend: ৳{amount(safe_to_spend):,.0f}",
        ],
        "warning": None,
    }


def check_transaction_impact(
    db: Session,
    user: User,
    proposed_amount: float,
) -> dict:
    """Check if a proposed transaction would reduce balance below safe-to-spend threshold."""
    safe = calculate_safe_to_spend(db, user)

    current_balance = safe["current_balance"]
    proposed_amount_dec = Decimal(str(proposed_amount))
    fee = proposed_amount_dec * Decimal("0.005")  # 0.5% fee, minimum 5
    fee = max(Decimal("5"), fee)
    total = proposed_amount_dec + fee

    balance_after = current_balance - float(total)
    safe_to_spend_after = safe["safe_to_spend"] - float(total)

    warning = None
    if balance_after < 0:
        warning = "Insufficient balance for this transaction."
    elif safe_to_spend_after < 0:
        warning = "After this transaction your available balance may fall below the amount currently reserved for upcoming expenses."

    return {
        "proposed_amount": proposed_amount,
        "fee": amount(fee),
        "total": amount(total),
        "balance_after": amount(max(Decimal("0"), Decimal(str(balance_after)))),
        "safe_to_spend_before": safe["safe_to_spend"],
        "safe_to_spend_after": amount(max(Decimal("0"), Decimal(str(safe_to_spend_after)))),
        "would_exceed_safe_spend": safe_to_spend_after < 0,
        "warning": warning,
    }
