"""Deterministic offer service. No LLM for financial calculations or eligibility."""
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import User, Offer, SavedOffer, UserOfferPreference, Transaction
from app.services.analytics_service import spending_summary, period_bounds, is_spending, _tx, dec, amount

DECIMAL_ZERO = Decimal("0")
OFFER_TRANSACTION_CATEGORIES = {"Recharge": "Mobile Recharge"}


def _dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def _amount(value):
    return float(_dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _get_category_spending(db: Session, user_id: int, category: str) -> tuple[float, int, float | None]:
    """Return total, count and a deterministic typical purchase for 30 days.

    The median is deliberately used instead of an offer seed value: one large
    purchase should not make an offer look useful for a person whose normal
    purchase is much smaller.
    """
    now, start, _ = period_bounds()
    txs = _tx(db, user_id, start, now)
    transaction_category = OFFER_TRANSACTION_CATEGORIES.get(category, category)
    cat_txs = [t for t in txs if is_spending(t) and t.category == transaction_category]
    total = sum(_dec(t.amount) for t in cat_txs)
    purchases = sorted(_dec(t.amount) for t in cat_txs)
    if not purchases:
        typical = None
    elif len(purchases) % 2:
        typical = purchases[len(purchases) // 2]
    else:
        middle = len(purchases) // 2
        typical = (purchases[middle - 1] + purchases[middle]) / Decimal("2")
    return _amount(total), len(cat_txs), _amount(typical) if typical is not None else None


def _get_user_preference(db: Session, user_id: int) -> bool:
    pref = db.scalars(
        select(UserOfferPreference).where(UserOfferPreference.user_id == user_id)
    ).first()
    return pref.personalized_offers_enabled if pref else True


def _update_preference(db: Session, user_id: int, enabled: bool) -> UserOfferPreference:
    pref = db.scalars(
        select(UserOfferPreference).where(UserOfferPreference.user_id == user_id)
    ).first()
    if pref:
        pref.personalized_offers_enabled = enabled
    else:
        pref = UserOfferPreference(user_id=user_id, personalized_offers_enabled=enabled)
        db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def compute_fit_status(
    typical_purchase: float | None,
    min_spend: float | None,
) -> str:
    """CRITICAL GUARDRAIL: Never suggest spending more to unlock an offer."""
    if min_spend is None or min_spend == 0:
        return "good_fit"
    typical = _dec(typical_purchase or 0)
    ms = _dec(min_spend)
    if typical >= ms:
        return "good_fit"
    elif typical > DECIMAL_ZERO:
        return "conditional_fit"
    return "not_useful"


def compute_potential_saving(
    typical_purchase: float | None,
    min_spend: float | None,
    discount_percent: float | None,
    discount_fixed: float | None,
    max_discount: float | None,
) -> float | None:
    """Calculate a labelled estimate, never a guaranteed saving.

    A compatible offer uses the person's actual typical purchase. A
    conditional offer is calculated only at its stated minimum, making the
    extra spend visible rather than encouraging it.
    """
    ms = _dec(min_spend or 0)
    typical = _dec(typical_purchase or 0)
    purchase = typical if ms == DECIMAL_ZERO or typical >= ms else ms

    if discount_percent:
        saving = purchase * _dec(discount_percent) / Decimal("100")
    elif discount_fixed:
        saving = _dec(discount_fixed)
    else:
        return None

    if max_discount:
        saving = min(saving, _dec(max_discount))

    return _amount(saving)


def _rank_offers(offers: list[dict], personalized: bool) -> list[dict]:
    """Deterministic ranking. Returns sorted list of offer dicts with rank_score."""
    for o in offers:
        score = 0
        # Category relevance (30pts)
        score += (o.get("category_spending_volume", 0) / 1000) * 30
        # Usage frequency (20pts)
        score += (o.get("category_tx_count", 0) * 2)
        # Fit status bonus/penalty (25pts max)
        fit = o.get("fit_status", "not_useful")
        if fit == "good_fit":
            score += 25
        elif fit == "conditional_fit":
            score += 5
        else:
            score -= 50
        # Expiry urgency (10pts max)
        expiry = o.get("expiry_date")
        if expiry:
            days_left = (expiry - date.today()).days
            if days_left <= 3:
                score += 10
            elif days_left <= 7:
                score += 5
        # Personalization boost
        if personalized and o.get("category_spending_volume", 0) > 0:
            score *= 1.5
        o["rank_score"] = round(score, 2)

    offers.sort(key=lambda x: x["rank_score"], reverse=True)
    return offers


def _offer_state(offer: Offer) -> str:
    if offer.expiry_date and offer.expiry_date < date.today():
        return "expired"
    if not offer.active:
        return "upcoming"
    return "active"


def get_all_offers(
    db: Session,
    user_id: int,
    category: str | None = None,
    state: str = "active",
    personalized: bool | None = None,
) -> tuple[list[dict], dict]:
    """Return (offers_list, preferences)."""
    if personalized is None:
        personalized = _get_user_preference(db, user_id)

    q = select(Offer)
    if category and category != "all" and category != "For You":
        q = q.where(Offer.category == category)
    db_offers = list(db.scalars(q.order_by(Offer.id)).all())

    # Load saved offer ids
    saved_rows = db.scalars(
        select(SavedOffer.offer_id).where(SavedOffer.user_id == user_id)
    ).all()
    saved_ids = set(saved_rows)

    result = []
    for offer in db_offers:
        offer_state = _offer_state(offer)
        if state == "active" and offer_state != "active":
            continue
        if state == "expired" and offer_state != "expired":
            continue
        if state == "saved" and offer.id not in saved_ids:
            continue
        if state == "used":
            # A view or save is never treated as redemption in this demo.
            # There is no redemption flow, so there can be no used offers.
            continue
        # Compute category spending signals
        cat_vol = 0.0
        cat_count = 0
        typical_purchase = None
        if personalized and offer.category:
            cat_vol, cat_count, typical_purchase = _get_category_spending(db, user_id, offer.category)

        # Personalised mode is intentionally conservative: an active offer is
        # not an opportunity unless the person already spends in that category.
        # Saved offers remain visible so a user can manage their own list.
        if personalized and state == "active" and cat_count == 0:
            continue

        fit = compute_fit_status(typical_purchase, offer.min_spend) if personalized else None
        pot_saving = compute_potential_saving(
            typical_purchase,
            offer.min_spend,
            offer.discount_percent,
            offer.discount_fixed,
            offer.max_discount,
        ) if personalized else None

        result.append({
            "id": offer.id,
            "title": offer.title,
            "terms": offer.terms,
            "terms_bn": offer.terms_bn,
            "category": offer.category,
            "min_spend": offer.min_spend,
            "discount_percent": offer.discount_percent,
            "discount_fixed": offer.discount_fixed,
            "max_discount": offer.max_discount,
            "typical_purchase": typical_purchase,
            "typical_merchant": offer.typical_merchant,
            "potential_saving": pot_saving,
            "expiry_date": offer.expiry_date,
            "eligibility_notes": offer.eligibility_notes,
            "fit_status": fit,
            "is_saved": offer.id in saved_ids,
            "learning_lesson_id": offer.learning_lesson_id,
            "category_spending_volume": cat_vol,
            "category_tx_count": cat_count,
            "merchant_id": offer.merchant_id,
            "state": offer_state,
        })

    # Why relevant text
    if personalized:
        for o in result:
            if o["category_tx_count"] > 0:
                o["why_relevant"] = f"You made {o['category_tx_count']} {o['category']} purchases in the last 30 days."

    result = _rank_offers(result, personalized)

    prefs = {"personalized_offers_enabled": personalized}
    return result, prefs


def get_offer_detail(db: Session, offer_id: int, user_id: int) -> tuple[dict | None, bool]:
    """Return (offer_dict, is_saved)."""
    offer = db.scalars(select(Offer).where(Offer.id == offer_id)).first()
    if not offer:
        return None, False

    saved = db.scalars(
        select(SavedOffer).where(
            SavedOffer.user_id == user_id,
            SavedOffer.offer_id == offer_id
        )
    ).first()

    is_saved = saved is not None

    cat_vol = 0.0
    cat_count = 0
    typical_purchase = None
    personalized = _get_user_preference(db, user_id)
    if personalized and offer.category:
        cat_vol, cat_count, typical_purchase = _get_category_spending(db, user_id, offer.category)

    fit = compute_fit_status(typical_purchase, offer.min_spend) if personalized else None
    pot_saving = compute_potential_saving(
        typical_purchase,
        offer.min_spend,
        offer.discount_percent,
        offer.discount_fixed,
        offer.max_discount,
    ) if personalized else None

    why = None
    if cat_count > 0:
        why = f"You made {cat_count} {offer.category} purchases in the last 30 days totaling ৳{cat_vol:,.0f}."

    return {
        "id": offer.id,
        "title": offer.title,
        "terms": offer.terms,
        "terms_bn": offer.terms_bn,
        "category": offer.category,
        "min_spend": offer.min_spend,
        "discount_percent": offer.discount_percent,
        "discount_fixed": offer.discount_fixed,
        "max_discount": offer.max_discount,
        "typical_purchase": typical_purchase,
        "typical_merchant": offer.typical_merchant,
        "potential_saving": pot_saving,
        "expiry_date": offer.expiry_date,
        "eligibility_notes": offer.eligibility_notes,
        "fit_status": fit,
        "is_saved": is_saved,
        "learning_lesson_id": offer.learning_lesson_id,
        "why_relevant": why,
        "state": _offer_state(offer),
    }, is_saved


def save_offer(db: Session, user_id: int, offer_id: int) -> bool:
    existing = db.scalars(
        select(SavedOffer).where(
            SavedOffer.user_id == user_id,
            SavedOffer.offer_id == offer_id
        )
    ).first()
    if existing:
        return True
    db.add(SavedOffer(user_id=user_id, offer_id=offer_id, saved_at=datetime.utcnow()))
    db.commit()
    return True


def unsave_offer(db: Session, user_id: int, offer_id: int) -> bool:
    existing = db.scalars(
        select(SavedOffer).where(
            SavedOffer.user_id == user_id,
            SavedOffer.offer_id == offer_id
        )
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
    return False


def get_saved_offers(db: Session, user_id: int) -> list[dict]:
    rows = db.scalars(
        select(SavedOffer).where(SavedOffer.user_id == user_id).order_by(SavedOffer.saved_at.desc())
    ).all()
    offers = []
    for row in rows:
        offer_dict, _ = get_offer_detail(db, row.offer_id, user_id)
        if offer_dict:
            offers.append(offer_dict)
    return offers
