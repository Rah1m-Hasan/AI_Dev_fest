"""Recipient relationship classification service.

Classifies recipients as: Trusted, Known, New, Unusual

Evidence is deterministically computed from transaction history.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Transaction, TrustedContact, User


@dataclass
class RelationshipInfo:
    recipient_id: int
    recipient_name: str
    relationship_type: str  # "trusted" | "known" | "new" | "unusual"
    previous_transaction_count: int
    last_transaction_amount: float | None
    last_transaction_date: str | None
    average_transaction_amount: float | None
    total_sent: float
    evidence: list[str]


def _is_trusted_contact(contact: TrustedContact) -> bool:
    """Only an explicit owner confirmation counts as verified context."""
    return contact.verification_status == "verified"


def get_transaction_count_to_recipient(
    db: Session,
    user_id: int,
    recipient_name: str,
) -> tuple[int, float | None, str | None, float]:
    """Get transaction stats for a recipient.

    Returns: (count, last_amount, last_date, total_sent)
    """
    rows = list(db.scalars(
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.merchant_name.ilike(f"%{recipient_name}%"),
            Transaction.direction == "expense",
        )
        .order_by(Transaction.timestamp.desc())
    ))

    if not rows:
        return 0, None, None, 0.0

    count = len(rows)
    last_amount = float(rows[0].amount)
    last_date = rows[0].timestamp.date().isoformat()
    total_sent = sum(float(t.amount) for t in rows)

    return count, last_amount, last_date, total_sent


def classify_relationship(
    db: Session,
    user_id: int,
    contact: TrustedContact | None,
    recipient_name: str,
    amount: float | None = None,
) -> RelationshipInfo:
    """Classify the user's relationship with a recipient.

    Logic:
    - Trusted: Frequent transactions (5+) AND contact marked as trusted
    - Known: Has previous transactions but not frequent or not explicitly trusted
    - New: No transaction history with this recipient
    - Unusual: New recipient + large amount OR new + unusual behavior pattern
    """
    count, last_amount, last_date, total_sent = get_transaction_count_to_recipient(
        db, user_id, contact.name if contact else recipient_name
    )

    # History informs context; it never upgrades a person to "verified".
    evidence = []
    relationship_type = "new"

    if contact and _is_trusted_contact(contact):
        if count >= 5:
            relationship_type = "trusted"
            evidence.append(f"You have sent money to {contact.name} {count} times.")
            if last_amount:
                evidence.append(f"Last transaction: ৳{last_amount:,.0f}, {last_date or 'unknown date'}.")
        elif count >= 1:
            relationship_type = "known"
            evidence.append(f"You have sent money to {contact.name} {count} time{'s' if count > 1 else ''} before.")
        else:
            relationship_type = "new"
            evidence.append(f"{contact.name} is saved as your {contact.relationship}.")
            evidence.append("You have not previously sent money to this account.")
    elif count >= 3:
        relationship_type = "known"
        evidence.append(f"You have sent money to this recipient {count} times.")
        if last_amount:
            evidence.append(f"Last: ৳{last_amount:,.0f}, {last_date or 'unknown date'}.")
    elif count >= 1:
        relationship_type = "known"
        evidence.append(f"You have sent money to this recipient {count} time before.")
    else:
        relationship_type = "new"
        evidence.append("You have not previously sent money to this account.")
        if contact:
            evidence.append(f"{contact.name} is saved in your trusted contacts as {contact.relationship}.")

    # Check for unusual patterns
    if relationship_type == "new" and amount and amount > 5000:
        relationship_type = "unusual"
        evidence.append(f"This would be a new recipient with a large amount (৳{amount:,.0f}).")
        evidence.append("Please verify the recipient carefully before proceeding.")

    # Calculate average if we have transactions
    avg_amount = total_sent / count if count > 0 else None

    return RelationshipInfo(
        recipient_id=contact.id if contact else 0,
        recipient_name=contact.name if contact else recipient_name,
        relationship_type=relationship_type,
        previous_transaction_count=count,
        last_transaction_amount=last_amount,
        last_transaction_date=last_date,
        average_transaction_amount=avg_amount,
        total_sent=total_sent,
        evidence=evidence,
    )
