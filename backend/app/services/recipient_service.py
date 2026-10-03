"""Trusted Contacts and recipient resolution service.

Users should think in terms of people, not phone numbers.
Supports mapping relationship terms like "my son" → "Rafi Ahmed"
"""
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from app.models import TrustedContact, Transaction, User
from app.services.intent_service import resolve_relationship_term


def get_trusted_contacts(db: Session, user_id: int) -> list[TrustedContact]:
    """Get all trusted contacts for a user."""
    return list(db.scalars(
        select(TrustedContact)
        .where(TrustedContact.user_id == user_id)
        .order_by(TrustedContact.name)
    ))


def add_trusted_contact(
    db: Session,
    user_id: int,
    name: str,
    phone_number: str,
    relationship: str,
    nickname: str | None = None,
    is_trusted: bool = True,
) -> TrustedContact:
    """Add a new trusted contact."""
    contact = TrustedContact(
        user_id=user_id,
        name=name,
        phone_number=phone_number,
        relationship=relationship,
        nickname=nickname,
        is_trusted=is_trusted,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def remove_trusted_contact(db: Session, contact_id: int, user_id: int) -> bool:
    """Remove a trusted contact. Returns True if removed."""
    contact = db.get(TrustedContact, contact_id)
    if contact and contact.user_id == user_id:
        db.delete(contact)
        db.commit()
        return True
    return False


def find_contact_by_name(db: Session, user_id: int, query: str) -> list[TrustedContact]:
    """Search trusted contacts by name or nickname."""
    query_lower = query.lower()
    return list(db.scalars(
        select(TrustedContact)
        .where(
            TrustedContact.user_id == user_id,
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
