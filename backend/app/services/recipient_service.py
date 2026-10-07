"""Trusted Contacts and recipient resolution service.

Users should think in terms of people, not phone numbers.
Supports mapping relationship terms like "my son" → "Rafi Ahmed"
"""
import re
from datetime import datetime
from sqlalchemy import select, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import TrustedContact, Transaction, User, UserPhone, TrustedContactAudit
from app.services.intent_service import resolve_relationship_term


def get_trusted_contacts(db: Session, user_id: int) -> list[TrustedContact]:
    """Get active saved people for one owner only."""
    return list(db.scalars(
        select(TrustedContact)
        .where(TrustedContact.user_id == user_id, TrustedContact.archived_at.is_(None))
        .order_by(TrustedContact.created_at.desc(), TrustedContact.name)
    ))

def normalize_bangladesh_phone(value: str) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if digits.startswith("+"): digits = digits[1:]
    if re.fullmatch(r"01[3-9]\d{8}", digits):
        return "880" + digits[1:]
    if re.fullmatch(r"8801[3-9]\d{8}", digits):
        return digits
    raise ValueError("Enter a valid Bangladeshi mobile number, such as 01812345678.")

def display_phone(normalized: str) -> str:
    return "0" + normalized[3:]

def _audit(db: Session, user_id: int, contact_id: int | None, event: str) -> None:
    db.add(TrustedContactAudit(user_id=user_id, trusted_contact_id=contact_id, event_type=event))

def contact_or_none(db: Session, user_id: int, contact_id: int) -> TrustedContact | None:
    return db.scalar(select(TrustedContact).where(TrustedContact.id == contact_id, TrustedContact.user_id == user_id, TrustedContact.archived_at.is_(None)))


def add_trusted_contact(
    db: Session,
    user_id: int,
    name: str,
    phone_number: str,
    relationship: str,
    nickname: str | None = None,
    notes: str | None = None,
) -> TrustedContact:
    normalized = normalize_bangladesh_phone(phone_number)
    if db.scalar(select(UserPhone.id).where(UserPhone.user_id == user_id, UserPhone.phone == display_phone(normalized))):
        raise ValueError("You cannot save your own mobile number.")
    existing = db.scalar(select(TrustedContact).where(TrustedContact.user_id == user_id, TrustedContact.normalized_phone == normalized))
    if existing:
        if existing.archived_at:
            existing.archived_at = None
            existing.name, existing.relationship = name.strip(), relationship.strip()
            existing.nickname, existing.notes = nickname.strip() if nickname else None, notes.strip() if notes else None
            existing.verification_status, existing.verified_at = "unverified", None
            _audit(db, user_id, existing.id, "trusted_person_restored")
            db.commit(); db.refresh(existing); return existing
        raise ValueError(f"This number is already saved as {existing.name}.")
    contact = TrustedContact(
        user_id=user_id,
        name=name.strip(), phone_number=display_phone(normalized), normalized_phone=normalized,
        relationship=relationship.strip(), nickname=nickname.strip() if nickname else None,
        notes=notes.strip() if notes else None, verification_status="unverified", is_trusted=False,
    )
    db.add(contact)
    db.flush(); _audit(db, user_id, contact.id, "trusted_person_added"); db.commit()
    db.refresh(contact)
    return contact


def update_trusted_contact(db: Session, contact: TrustedContact, name: str, phone_number: str, relationship: str, nickname: str | None, notes: str | None) -> TrustedContact:
    normalized = normalize_bangladesh_phone(phone_number)
    if normalized != contact.normalized_phone:
        duplicate = db.scalar(select(TrustedContact).where(TrustedContact.user_id == contact.user_id, TrustedContact.normalized_phone == normalized, TrustedContact.id != contact.id))
        if duplicate: raise ValueError(f"This number is already saved as {duplicate.name}.")
        if db.scalar(select(UserPhone.id).where(UserPhone.user_id == contact.user_id, UserPhone.phone == display_phone(normalized))): raise ValueError("You cannot save your own mobile number.")
        contact.normalized_phone, contact.phone_number = normalized, display_phone(normalized)
        contact.verification_status, contact.verified_at, contact.is_trusted = "unverified", None, False
    contact.name, contact.relationship = name.strip(), relationship.strip()
    contact.nickname, contact.notes = nickname.strip() if nickname else None, notes.strip() if notes else None
    _audit(db, contact.user_id, contact.id, "trusted_person_updated")
    db.commit(); db.refresh(contact); return contact

def verify_trusted_contact(db: Session, contact: TrustedContact) -> TrustedContact:
    contact.verification_status, contact.verified_at, contact.is_trusted = "verified", datetime.utcnow(), True
    _audit(db, contact.user_id, contact.id, "trusted_person_verified")
    db.commit(); db.refresh(contact); return contact

def remove_trusted_contact(db: Session, contact_id: int, user_id: int) -> bool:
    contact = contact_or_none(db, user_id, contact_id)
    if not contact: return False
    contact.archived_at = datetime.utcnow()
    _audit(db, user_id, contact.id, "trusted_person_removed")
    db.commit(); return True


def find_contact_by_name(db: Session, user_id: int, query: str) -> list[TrustedContact]:
    """Search trusted contacts by name or nickname."""
    query_lower = query.lower()
    return list(db.scalars(
        select(TrustedContact)
        .where(
            TrustedContact.user_id == user_id,
            TrustedContact.archived_at.is_(None),
            or_(
                func.lower(TrustedContact.name).contains(query_lower),
                func.lower(TrustedContact.nickname).contains(query_lower),
                func.lower(TrustedContact.relationship).contains(query_lower),
            )
        )
        .order_by(TrustedContact.name)
    ))


def find_contact_by_relationship(
    db: Session,
    user_id: int,
    relationship_term: str,
) -> list[TrustedContact]:
    """Find contacts matching a relationship term like 'son', 'my daughter'."""
    resolved = resolve_relationship_term(relationship_term)
    if not resolved:
        # Try direct search
        return find_contact_by_name(db, user_id, relationship_term)

    # Search by resolved relationship
    return list(db.scalars(
        select(TrustedContact)
        .where(
            TrustedContact.user_id == user_id,
            TrustedContact.archived_at.is_(None),
            func.lower(TrustedContact.relationship) == resolved
        )
        .order_by(TrustedContact.name)
    ))


def find_best_contact_match(
    db: Session,
    user_id: int,
    query: str,
) -> list[TrustedContact]:
    """Find best matching contacts for a query that may be name, relationship, or partial."""
    if not query or len(query) < 2:
        return []

    query_lower = query.lower()

    # First try exact name/nickname match
    exact = list(db.scalars(
        select(TrustedContact)
        .where(
            TrustedContact.user_id == user_id,
            TrustedContact.archived_at.is_(None),
            or_(
                func.lower(TrustedContact.name) == query_lower,
                func.lower(TrustedContact.nickname) == query_lower,
            )
        )
    ))
    if exact:
        return exact

    # Try relationship term resolution
    relationship_matches = find_contact_by_relationship(db, user_id, query)
    if relationship_matches:
        return relationship_matches

    # Fall back to partial name search
    return find_contact_by_name(db, user_id, query)


def resolve_recipient(
    db: Session,
    user_id: int,
    query: str,
) -> tuple[TrustedContact | None, list[TrustedContact]]:
    """Resolve a recipient query to a contact.

    Returns (matched_contact, ambiguous_contacts).
    If query matches exactly one contact, returns (contact, []).
    If multiple matches, returns (None, [contacts]).
    If no match, returns (None, []).
    """
    matches = find_best_contact_match(db, user_id, query)

    if len(matches) == 1:
        return matches[0], []
    elif len(matches) > 1:
        return None, matches
    else:
        return None, []
