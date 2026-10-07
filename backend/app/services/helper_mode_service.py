"""Persisted, least-privilege Helper Mode operations.

This module deliberately contains no payment execution capability. A helper can
only access a small, server-filtered support view after a relationship and the
specific permission have both been verified.
"""
from datetime import datetime
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import HelperActivity, HelperAssistanceRequest, HelperRelationship, User, UserPhone

PERMISSIONS = {
    "explain_financial_info", "guide_navigation", "view_alerts",
    "view_pending_transactions", "view_savings_goals", "view_spending_summary",
    "view_financial_health", "view_budget_summary", "prepare_transaction",
}

def clean_phone(value: str) -> str:
    phone = re.sub(r"[\s\-()]", "", value)
    if not re.fullmatch(r"(?:\+?880|0)1\d{9}", phone):
        raise ValueError("Enter a valid Bangladeshi mobile number.")
    return phone

def validate_permissions(values: list[str]) -> list[str]:
    cleaned = list(dict.fromkeys(values))
    invalid = set(cleaned) - PERMISSIONS
    if invalid:
        raise ValueError("One or more permissions are not allowed.")
    if not cleaned:
        raise ValueError("Choose at least one permission.")
    return cleaned

def record_activity(db: Session, owner_id: int, event_type: str, relationship_id: int | None = None, detail: str | None = None, actor: str = "owner"):
    db.add(HelperActivity(owner_user_id=owner_id, helper_relationship_id=relationship_id, event_type=event_type, detail=detail, actor=actor))

def relationship_or_none(db: Session, owner_id: int, relationship_id: int) -> HelperRelationship | None:
    return db.scalar(select(HelperRelationship).where(HelperRelationship.id == relationship_id, HelperRelationship.owner_user_id == owner_id))

def create_relationship(db: Session, owner: User, name: str, phone: str, relationship: str, permissions: list[str]) -> HelperRelationship:
    phone = clean_phone(phone)
    permissions = validate_permissions(permissions)
    if db.scalar(select(HelperRelationship.id).where(HelperRelationship.owner_user_id == owner.id, HelperRelationship.helper_phone == phone)):
        raise ValueError("This mobile number already has a helper invitation or access record.")
    account = db.scalar(select(UserPhone).where(UserPhone.phone == phone))
    if account and account.user_id == owner.id:
        raise ValueError("You cannot add yourself as a helper.")
    # A helper can be linked to an existing account, but remains pending until
    # that account accepts. External invitations intentionally have no account
    # access until an account-verification flow links them.
    helper = HelperRelationship(owner_user_id=owner.id, helper_user_id=account.user_id if account else None, helper_name=name.strip(), helper_phone=phone, relationship=relationship.strip(), permissions=permissions, status="pending")
    db.add(helper); db.flush()
    record_activity(db, owner.id, "helper_invited", helper.id, f"Invitation sent to {helper.helper_name}")
    db.commit(); db.refresh(helper)
    return helper

def update_permissions(db: Session, owner_id: int, relationship_id: int, permissions: list[str]) -> HelperRelationship | None:
    helper = relationship_or_none(db, owner_id, relationship_id)
    if not helper: return None
    if helper.status == "revoked": raise ValueError("Access has been revoked. Send a new invitation to grant access again.")
    helper.permissions = validate_permissions(permissions)
    record_activity(db, owner_id, "permission_updated", helper.id, f"Permissions updated for {helper.helper_name}")
    db.commit(); db.refresh(helper)
    return helper

def revoke(db: Session, owner_id: int, relationship_id: int) -> HelperRelationship | None:
    helper = relationship_or_none(db, owner_id, relationship_id)
    if not helper: return None
    if helper.status != "revoked":
        helper.status = "revoked"; helper.revoked_at = datetime.utcnow()
        record_activity(db, owner_id, "helper_access_revoked", helper.id, f"Access revoked for {helper.helper_name}")
        db.commit(); db.refresh(helper)
    return helper

def accept_invitation(db: Session, relationship_id: int, helper_user_id: int) -> HelperRelationship | None:
    helper = db.get(HelperRelationship, relationship_id)
    if not helper or helper.status != "pending": return None
    if helper.owner_user_id == helper_user_id: raise ValueError("You cannot accept your own helper invitation.")
    if helper.helper_user_id != helper_user_id: return None
    helper.status = "active"; helper.helper_user_id = helper_user_id; helper.accepted_at = datetime.utcnow()
    record_activity(db, helper.owner_user_id, "helper_accepted", helper.id, f"{helper.helper_name} accepted the invitation", actor="helper")
    db.commit(); db.refresh(helper)
    return helper

def helper_access(db: Session, relationship_id: int, helper_user_id: int, permission: str) -> HelperRelationship | None:
    helper = db.scalar(select(HelperRelationship).where(HelperRelationship.id == relationship_id, HelperRelationship.helper_user_id == helper_user_id, HelperRelationship.status == "active"))
    if not helper or permission not in helper.permissions: return None
    return helper

def output(helper: HelperRelationship, last_activity: HelperActivity | None = None) -> dict:
    return {"id": helper.id, "helper_name": helper.helper_name, "phone": helper.helper_phone, "relationship": helper.relationship, "status": helper.status, "permissions": helper.permissions, "created_at": helper.created_at.isoformat(), "invited_at": helper.invited_at.isoformat(), "accepted_at": helper.accepted_at.isoformat() if helper.accepted_at else None, "revoked_at": helper.revoked_at.isoformat() if helper.revoked_at else None, "last_activity": {"event_type": last_activity.event_type, "detail": last_activity.detail, "created_at": last_activity.created_at.isoformat()} if last_activity else None}

def owner_requests(db: Session, owner_id: int) -> list[HelperAssistanceRequest]:
    return list(db.scalars(select(HelperAssistanceRequest).where(HelperAssistanceRequest.owner_user_id == owner_id, HelperAssistanceRequest.status == "waiting_owner_confirmation").order_by(HelperAssistanceRequest.created_at.desc())))
