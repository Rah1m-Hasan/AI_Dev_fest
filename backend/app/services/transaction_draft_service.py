"""Transaction Draft service with explicit state machine.

States: DRAFT → REVIEWED → CONFIRMED → PIN_VERIFIED → COMPLETED (or CANCELLED).

Every transactional action ends with a clear human confirmation step.
PIN must be entered through a dedicated secure-looking PIN UI component.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy.orm import Session
from app.models import TransactionDraft, Account, Transaction, User
from app.services.analytics_service import dec, amount
from app.services.relationship_service import classify_relationship, RelationshipInfo


class DraftState(Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    PIN_VERIFIED = "PIN_VERIFIED"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Demo PIN - never expose in responses
DEMO_PIN = "1234"
TRANSFER_FEE_RATE = Decimal("0.005")  # 0.5%
MIN_FEE = Decimal("5")
MAX_FEE = Decimal("50")


def _calculate_fee(amount: Decimal) -> Decimal:
    """Calculate transfer fee."""
    fee = amount * TRANSFER_FEE_RATE
    return max(MIN_FEE, min(MAX_FEE, fee))


def create_draft(
    db: Session,
    user_id: int,
    recipient_id: int | None,
    recipient_name: str,
    recipient_phone: str | None,
    amount: float,
    reference: str | None = None,
) -> TransactionDraft:
    """Create a new transfer draft. It is not a payment instruction."""
    # Cancel any existing active drafts for this user
    existing = db.query(TransactionDraft).filter(
        TransactionDraft.user_id == user_id,
        TransactionDraft.state.notin_(["completed", "cancelled"])
    ).all()
    for draft in existing:
        draft.state = DraftState.CANCELLED.value
    db.commit()

    amount_dec = Decimal(str(amount))
    fee = _calculate_fee(amount_dec)

    draft = TransactionDraft(
        user_id=user_id,
        recipient_id=recipient_id,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        amount=float(amount_dec),
        fee=float(fee),
        reference=reference,
        state=DraftState.DRAFT.value,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def get_active_draft(db: Session, user_id: int) -> TransactionDraft | None:
    """Get the current active draft for a user."""
    return db.query(TransactionDraft).filter(
        TransactionDraft.user_id == user_id,
        TransactionDraft.state.notin_([DraftState.COMPLETED.value, DraftState.CANCELLED.value])
    ).order_by(TransactionDraft.created_at.desc()).first()


def transition_state(
    db: Session,
    draft: TransactionDraft,
    new_state: DraftState,
) -> TransactionDraft:
    """Transition draft to new state with validation."""
    current = DraftState(draft.state)

    # Valid transitions
    valid_transitions = {
        DraftState.DRAFT: [DraftState.REVIEWED, DraftState.CANCELLED],
        DraftState.REVIEWED: [DraftState.CONFIRMED, DraftState.CANCELLED],
        DraftState.CONFIRMED: [DraftState.PIN_VERIFIED, DraftState.CANCELLED],
        DraftState.PIN_VERIFIED: [DraftState.COMPLETED, DraftState.CANCELLED],
    }

    if new_state in valid_transitions.get(current, []):
        draft.state = new_state.value
        db.commit()
        db.refresh(draft)
        return draft

    raise ValueError(f"Invalid state transition from {current.value} to {new_state.value}")


def review_draft(db: Session, draft: TransactionDraft) -> TransactionDraft:
    """Mark the human-readable transfer summary as reviewed."""
    return transition_state(db, draft, DraftState.REVIEWED)


def confirm_draft(db: Session, draft: TransactionDraft) -> TransactionDraft:
    """Record explicit user confirmation before requesting a PIN."""
    return transition_state(db, draft, DraftState.CONFIRMED)


def verify_pin(db: Session, draft: TransactionDraft, pin: str) -> tuple[bool, str]:
    """Verify demo PIN and execute transaction if correct.

    Returns (success, message).
    """
    if pin != DEMO_PIN:
        return False, "Incorrect PIN. Please try again."

    try:
        transition_state(db, draft, DraftState.PIN_VERIFIED)
    except ValueError as e:
        return False, str(e)

    # Execute the simulated transaction
    return _execute_transfer(db, draft)


def _execute_transfer(db: Session, draft: TransactionDraft) -> tuple[bool, str]:
    """Execute the simulated transfer."""
    user = db.get(User, draft.user_id)
    if not user:
        return False, "User not found."

    account = user.account
    total = Decimal(str(draft.amount)) + Decimal(str(draft.fee))

    # Check sufficient balance
    if Decimal(str(account.balance)) < total:
        draft.state = DraftState.CANCELLED.value
        db.commit()
        return False, "Insufficient balance."

    # Execute the prototype transfer only after an explicit confirmation and
    # successful local demo-PIN check. No AI service participates here.
    balance_before = Decimal(str(account.balance))
    account.balance = float(balance_before - total)

    # Create transaction record
    tx = Transaction(
        user_id=draft.user_id,
        merchant_name=draft.recipient_name,
        category="Transfers",
        amount=draft.amount,
        direction="expense",
        transaction_type="transfer",
        timestamp=datetime.utcnow(),
        balance_before=float(balance_before),
        balance_after=float(account.balance),
        description=f"Demo transfer to {draft.recipient_name}" + (f" - {draft.reference}" if draft.reference else ""),
    )
    db.add(tx)
    db.commit()

    draft.state = DraftState.COMPLETED.value
    db.commit()
    db.refresh(draft)

    return True, "Transfer completed successfully."


def cancel_draft(db: Session, draft: TransactionDraft) -> TransactionDraft:
    """Cancel the draft."""
    draft.state = DraftState.CANCELLED.value
    db.commit()
    db.refresh(draft)
    return draft


def get_draft_summary(
    db: Session,
    draft: TransactionDraft,
    user: User,
    relationship_info: RelationshipInfo | None,
    safe_to_spend_before: dict | None,
) -> dict:
    """Get a complete summary of the draft for display."""
    total = Decimal(str(draft.amount)) + Decimal(str(draft.fee))
    balance_after = Decimal(str(user.account.balance)) - total

    from app.services.analytics_service import money_runway
    runway_before = money_runway(db, user)
    flexible_after = max(Decimal("0"), dec(safe_to_spend_before["safe_to_spend"]) - total) if safe_to_spend_before else Decimal("0")
    balance_before = dec(user.account.balance)
    buffer = dec(runway_before["buffer"])
    usable_before = max(Decimal("1"), balance_before - buffer)
    usable_after = max(Decimal("0"), balance_after - buffer)
    runway_after_days = max(0, int(runway_before["days"] * float(usable_after / usable_before)))

    return {
        "draft_id": draft.id,
        "recipient": {
            "id": draft.recipient_id,
            "name": draft.recipient_name,
            "phone": draft.recipient_phone,
        },
        "relationship": relationship_info.relationship_type if relationship_info else "unknown",
        "relationship_evidence": relationship_info.evidence if relationship_info else [],
        "amount": draft.amount,
        "fee": draft.fee,
        "total": float(total),
        "available_balance": user.account.balance,
        "balance_after": float(balance_after),
        "safe_to_spend_before": safe_to_spend_before,
        "safe_to_spend_after": amount(flexible_after),
        "runway_before_days": runway_before["days"],
        "runway_after_days": runway_after_days,
        "runway_note": "Estimated from the current runway projection after this transfer and fee.",
        "reference": draft.reference,
        "state": draft.state,
    }
