"""Trusted Helper service.

Allows a trusted person to assist without gaining full financial control.
Helper must NEVER see PIN, enter PIN, silently execute transactions, or bypass confirmation.
"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import TrustedHelper, HelperRequest, User


def get_trusted_helpers(db: Session, user_id: int) -> list[TrustedHelper]:
    """Get all trusted helpers for a user."""
    return list(db.scalars(
        select(TrustedHelper).where(TrustedHelper.user_id == user_id).order_by(TrustedHelper.helper_name)
    ))


def add_trusted_helper(
    db: Session,
    user_id: int,
    helper_name: str,
    relationship: str,
    phone: str,
    can_view_pending_transaction: bool = False,
    can_receive_alerts: bool = True,
    can_view_balance: bool = False,
    can_view_history: bool = False,
    can_initiate: bool = False,
) -> TrustedHelper:
    """Add a new trusted helper."""
    helper = TrustedHelper(
        user_id=user_id,
        helper_name=helper_name,
        relationship=relationship,
        phone=phone,
        can_view_pending_transaction=can_view_pending_transaction,
        can_receive_alerts=can_receive_alerts,
        can_view_balance=can_view_balance,
        can_view_history=can_view_history,
        # A Trusted Helper is an accessibility aid, never delegated payment
        # authority. Ignore caller input rather than relying on the UI.
        can_initiate=False,
    )
    db.add(helper)
    db.commit()
    db.refresh(helper)
    return helper


def remove_trusted_helper(db: Session, helper_id: int, user_id: int) -> bool:
    """Remove a trusted helper."""
    helper = db.get(TrustedHelper, helper_id)
    if helper and helper.user_id == user_id:
        db.delete(helper)
        db.commit()
        return True
    return False


def create_helper_request(
    db: Session,
    user_id: int,
    helper_id: int,
    message: str | None = None,
) -> HelperRequest:
    """Create a help request to a trusted helper."""
    request = HelperRequest(
        user_id=user_id,
        helper_id=helper_id,
        status="pending",
        message=message,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_pending_requests_for_helper(
    db: Session,
    helper_id: int,
) -> list[HelperRequest]:
    """Get pending help requests for a helper."""
    return list(db.scalars(
        select(HelperRequest).where(
            HelperRequest.helper_id == helper_id,
            HelperRequest.status == "pending"
        ).order_by(HelperRequest.created_at.desc())
    ))


def respond_to_helper_request(
    db: Session,
    request_id: int,
    helper_id: int,
    response: str,
) -> HelperRequest | None:
    """Helper responds to a help request."""
    request = db.get(HelperRequest, request_id)
    if not request or request.helper_id != helper_id:
        return None

    request.response = response
    request.status = "responded"
    db.commit()
    db.refresh(request)
    return request


def get_request_with_context(
    db: Session,
    request_id: int,
    user_id: int,
) -> dict | None:
    """Get a helper request with full context for display."""
    request = db.get(HelperRequest, request_id)
    if not request or request.user_id != user_id:
        return None

    helper = db.get(TrustedHelper, request.helper_id)
    user = db.get(User, user_id)

    return {
        "request_id": request.id,
        "status": request.status,
        "message": request.message,
        "response": request.response,
        "created_at": request.created_at.isoformat(),
        "helper": {
            "name": helper.helper_name if helper else "Unknown",
            "relationship": helper.relationship if helper else "Unknown",
        } if helper else None,
    }
