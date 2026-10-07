"""Authoritative, deterministic savings-goal calculations.

Natural-language providers may identify a target or timeline, but they never
calculate contribution amounts or feasibility.  All callers should use this
module so a goal has one financial interpretation everywhere in the product.
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, ROUND_CEILING

from app.schemas import SavingsGoalEntities, SavingsPlanResult


ZERO = Decimal("0")
WHOLE_TAKA = Decimal("1")


def add_calendar_months(start: date, months: int) -> date:
    """Move by calendar months while preserving the day when possible."""
    target_month_index = start.month - 1 + months
    year = start.year + target_month_index // 12
    month = target_month_index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def months_for_deadline(start: date, deadline: date) -> int:
    """A conservative whole-month saving horizon for an explicit deadline."""
    days = (deadline - start).days
    if days <= 0:
        raise ValueError("deadline must be in the future")
    # This is only used when a user supplied a date rather than a month count.
    # Ceiling keeps a partial final month from silently underfunding the goal.
    return max(1, int((Decimal(days) / Decimal("30.44")).to_integral_value(rounding=ROUND_CEILING)))


def _whole_taka_up(value: Decimal) -> Decimal:
    return value.quantize(WHOLE_TAKA, rounding=ROUND_CEILING)


def calculate_savings_plan(
    *,
    target_amount: Decimal,
    current_amount: Decimal = ZERO,
    duration_months: int | None = None,
    deadline: date | None = None,
    monthly_capacity: Decimal | None = None,
    goal_name: str = "Savings goal",
    today: date | None = None,
) -> SavingsPlanResult:
    """Calculate a savings plan with Decimal arithmetic and whole-taka-up pace.

    ``required_monthly_contribution`` is always what it takes to fund the
    remaining amount.  ``affordable_monthly_contribution`` is separately
    supplied by a deterministic cash-flow calculation and is never relabelled
    as the required pace.
    """
    today = today or date.today()
    entities = SavingsGoalEntities(
        goal_name=goal_name.strip() or "Savings goal",
        target_amount=target_amount,
        current_amount=current_amount,
        duration_months=duration_months,
        deadline=deadline,
    )
    resolved_months = entities.duration_months
    resolved_deadline = entities.deadline
    if resolved_months is None:
        assert resolved_deadline is not None
        resolved_months = months_for_deadline(today, resolved_deadline)
    if resolved_deadline is None:
        resolved_deadline = add_calendar_months(today, resolved_months)
    elif resolved_deadline <= today:
        raise ValueError("deadline must be in the future")

    remaining = max(ZERO, entities.target_amount - entities.current_amount)
    required = _whole_taka_up(remaining / Decimal(resolved_months)) if remaining else ZERO
    affordable = None
    if monthly_capacity is not None:
        affordable = max(ZERO, Decimal(monthly_capacity)).quantize(WHOLE_TAKA)

    shortfall = ZERO
    alternative_duration = None
    if affordable is None:
        feasible, status = None, "capacity_unknown"
    elif required <= affordable:
        feasible, status = True, "on_track"
    else:
        feasible = False
        shortfall = required - affordable
        # A plan within 15% of capacity is a stretch, but it is still not
        # presented as achievable without changing the user’s spending.
        status = "stretch" if affordable > ZERO and required <= affordable * Decimal("1.15") else "timeline_too_short"
        if affordable > ZERO:
            alternative_duration = int((remaining / affordable).to_integral_value(rounding=ROUND_CEILING))

    return SavingsPlanResult(
        goal_name=entities.goal_name,
        target_amount=entities.target_amount,
        current_amount=entities.current_amount,
        remaining_amount=remaining,
        duration_months=resolved_months,
        deadline=resolved_deadline,
        required_monthly_contribution=required,
        affordable_monthly_contribution=affordable,
        feasible=feasible,
        feasibility_status=status,
        shortfall=shortfall,
        alternative_duration_months=alternative_duration,
    )
