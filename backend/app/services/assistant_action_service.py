"""Whitelisted natural-language action orchestration.

Language understanding is deliberately separated from state changes.  The
fallback parser is the dependable baseline; an external model can be added as
an untrusted structured parser later without changing the action boundary.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AssistantActionDraft, AssistantConversation, Budget, SavingsGoal, Transaction
from app.services.analytics_service import amount, money_runway, run_out_analysis, safe_to_save, spending_summary, spending_comparison, health_score, budget_recommendation, simulate_scenario
from app.services.recipient_service import resolve_recipient
from app.services.safe_to_spend_service import calculate_safe_to_spend
from app.services.transaction_draft_service import DraftState, cancel_draft, confirm_draft, create_draft, get_draft_summary, review_draft, verify_pin
from app.services.relationship_service import classify_relationship
from app.services.groq_service import classify as groq_classify, respond as groq_respond
from app.services.learning_service import get_personalized_lessons
from app.services.offers_service import get_all_offers
from app.core.config import get_settings
from app.schemas import AssistantDisplayField, SavingsGoalEntities
from app.services.savings_plan_service import calculate_savings_plan


ACTIONS = {
    # Every entry is a server-owned capability.  The LLM can select a name but
    # cannot expand this registry or bypass the confirmation state machine.
    "chat": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "greeting": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "thanks": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "check_balance": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "safe_to_spend": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "money_runway": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "explain_spending": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "compare_spending": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "show_transactions": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "show_recurring": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "get_health_score": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "get_budget": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "get_budget_recommendation": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "safe_to_save": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "affordability_analysis": {"type": "read", "required_fields": ["amount"], "confirmation": False, "pin": False},
    "simulate_scenario": {"type": "read", "required_fields": ["amount"], "confirmation": False, "pin": False},
    "get_learning_recommendations": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "get_offers": {"type": "read", "required_fields": [], "confirmation": False, "pin": False},
    "send_money": {"type": "financial_write", "required_fields": ["recipient", "amount"], "confirmation": True, "pin": True},
    "create_savings_goal": {"type": "write", "required_fields": ["goal_name", "target_amount"], "confirmation": True, "pin": False},
    "update_budget": {"type": "write", "required_fields": ["category", "amount"], "confirmation": True, "pin": False},
    "mobile_recharge": {"type": "unsupported", "required_fields": ["amount"], "confirmation": True, "pin": True},
}

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Each intent only collects the slots it actually needs. Slots not listed here
# are treated as invalid for that intent — preventing a savings-goal slot
# (e.g. goal_name) from leaking into an affordability_analysis conversation.
ALLOWED_SLOTS: dict[str, list[str]] = {
    "send_money": ["recipient", "amount"],
    "create_savings_goal": ["goal_name", "target_amount", "duration_months", "deadline"],
    "update_budget": ["category", "amount"],
    "affordability_analysis": ["amount"],
    "simulate_scenario": ["amount"],
    "mobile_recharge": ["amount"],
    # Read-only intents accept no pending slots
    "chat": [],
    "greeting": [],
    "thanks": [],
    "check_balance": [],
    "safe_to_spend": [],
    "money_runway": [],
    "explain_spending": [],
    "compare_spending": [],
    "show_transactions": [],
    "show_recurring": [],
    "get_health_score": [],
    "get_budget": [],
    "get_budget_recommendation": [],
    "safe_to_save": [],
    "get_learning_recommendations": [],
    "get_offers": [],
}

# Loop detection: after 2 re-asks for the same slot, require explicit value
MAX_SLOT_REASK = 2

# Meta-intents that take precedence over any pending action
META_INTENTS = {"clarification_request", "cancel", "correction", "new_intent"}

# Whitelisted clarification-request phrases (Bangla + English)
CLARIFICATION_PHRASES = {
    "what do you mean", "কী বোঝাতে চাইছেন", "ব্যাখ্যা করুন", "explain",
    "i don't understand", "বুঝিনি", "আমি বুঝতে পারিনি",
    "that doesn't make sense", "ওটা কী", "কী জিনিস",
}

class ParsedIntent(BaseModel):
    intent: str = "unknown"
    confidence: float = Field(ge=0, le=1)
    language: str = "en"
    entities: dict[str, object] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    clarification_needed: bool = False

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(BN_DIGITS).strip().lower())

def language_of(text: str) -> str:
    return "bn" if len(re.findall(r"[ঀ-৿]", text)) > max(1, len(text) * .12) else "en"

def parse_amount(text: str) -> Decimal | None:
    """Extract a MONEY entity without treating a month/day count as money."""
    normalized = normalize(text)
    pattern = re.compile(r"(?<![\w.-])(৳\s*)?(\d+(?:[,.]\d+)?)\s*(k|thousand|হাজার|lakh|লাখ)?\s*(৳|taka|tk|টাকা)?", re.I)
    candidates: list[tuple[int, Decimal]] = []
    for match in pattern.finditer(normalized):
        tail = normalized[match.end():]
        multiplier = (match.group(3) or "").lower()
        has_money_marker = bool(match.group(1) or match.group(4) or multiplier)
        # A bare number immediately followed by a time word is a duration,
        # never a BDT amount (e.g. "in 2 months").
        if not has_money_marker and re.match(r"\s*(?:months?|mas|মাস(?:ে|ের)?)\b", tail):
            continue
        try:
            value = Decimal(match.group(2).replace(",", ""))
        except InvalidOperation:
            continue
        if multiplier in {"k", "thousand", "হাজার"}:
            value *= Decimal("1000")
        elif multiplier in {"lakh", "লাখ"}:
            value *= Decimal("100000")
        if value > 0:
            # Prefer explicit money notation over an unmarked target value.
            candidates.append((1 if has_money_marker else 0, value))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def _duration_months(text: str) -> int | None:
    match = re.search(r"(?<![\d.])(\d+)\s*(?:months?|month|mas|mashe|mash|মাস(?:ে|ের)?)\b", normalize(text), re.I)
    return int(match.group(1)) if match else None


def _deadline(text: str, today: date | None = None) -> date | None:
    """Parse common English deadline expressions; duration remains preferred."""
    today = today or date.today()
    normalized = normalize(text)
    names = "january february march april may june july august september october november december"
    match = re.search(rf"(?:by|within|এর মধ্যে|মধ্যে)\s+({'|'.join(names.split())})(?:\s+(\d{{1,2}}))?(?:,?\s+(\d{{4}}))?", normalized, re.I)
    if not match:
        return None
    month = names.split().index(match.group(1).lower()) + 1
    day = int(match.group(2) or 1)
    year = int(match.group(3) or today.year)
    try:
        parsed = date(year, month, day)
    except ValueError:
        return None
    if parsed <= today and not match.group(3):
        parsed = date(year + 1, month, day)
    return parsed


def _goal_name(text: str) -> str | None:
    """Extract a named goal while excluding money and time phrases."""
    raw = text.strip()
    for token, label in (("laptop", "Laptop"), ("phone", "Phone"), ("tv", "TV"), ("টিভি", "টিভি")):
        if (token.isascii() and re.search(rf"\b{re.escape(token)}\b", raw, re.I)) or (not token.isascii() and token in raw):
            return label
    patterns = (
        r"\bfor\s+([A-Za-z][A-Za-z0-9 &'\-]{0,80}?)(?=\s+(?:in|within|by)\b|$)",
        r"(?:জন্য|jonno)\s*([A-Za-zঀ-৿][A-Za-zঀ-৿0-9 &'\-]{0,80}?)(?=\s+(?:in|within|by|মাসে|মাসের|মধ্যে)\b|$)",
        r"([A-Za-zঀ-৿][A-Za-zঀ-৿0-9 &'\-]{0,80}?)\s*(?:er\s+jonno|এর\s+জন্য)",
    )
    for pattern in patterns:
        found = re.search(pattern, raw, re.I)
        if found:
            value = found.group(1).strip(" .,!?")
            if value and not re.fullmatch(r"\d+(?:\.\d+)?", value):
                value = re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.I)
                return value.upper() if value.isascii() and len(value) <= 3 else (value.title() if value.isascii() else value)
    return None

def _recipient(text: str) -> str | None:
    raw = text.strip()
    # English/Banglish name before "to" or "ke"; relationship terms are
    # intentionally passed to the deterministic recipient resolver.
    patterns = [r"(?:to|কে|ke)\s+([^\d৳,]+?)(?:\s+(?:for|\d|taka|tk|টাকা|পাঠ|send|path|transfer)|$)", r"^\s*([^\d,]+?)\s+(?:ke|কে)\s+", r"(?:send|পাঠাও|পাঠান|pathao|pathabo)\s+(?:money\s+)?(?:to\s+)?([^\d,]+?)\s+(?:\d|৳|taka|tk|টাকা)"]
    for pattern in patterns:
        found = re.search(pattern, raw, re.I)
        if found:
            value = found.group(1).strip(" .,")
            if value and len(value) <= 60: return value
    for term in ("brother", "mother", "father", "sister", "friend", "ভাই", "আম্মু", "মা", "বাবা", "বোন", "বন্ধু"):
        if term in normalize(raw): return term
    return None

def fallback_intent(message: str) -> ParsedIntent:
    text = normalize(message); language = language_of(message); amount_value = parse_amount(message)
    intent, entities, confidence = "unknown", {}, .35
    if re.search(r"^(?:hello|hi|hey|assalam|হ্যালো|আসসালাম)(?:\s|!|,|$)", text):
        intent, confidence = "greeting", .95
    elif any(x in text for x in ("thanks", "thank you", "ধন্যবাদ", "thank u")):
        intent, confidence = "thanks", .95
    elif any(x in text for x in ("recharge", "রিচার্জ", "top up")):
        intent, confidence = "mobile_recharge", .9
        if amount_value: entities["amount"] = amount_value
    elif any(x in text for x in ("send", "transfer", "pathao", "pathabo", "পাঠাও", "পাঠান", "সেন্ড")):
        intent, confidence = "send_money", .9
        recipient = _recipient(message)
        if recipient: entities["recipient"] = recipient
        if amount_value: entities["amount"] = amount_value
        entities["currency"] = "BDT"
    elif any(x in text for x in ("safe to spend", "safely spend", "নিরাপদে খরচ", "কত খরচ")):
        intent, confidence = "safe_to_spend", .95
    elif any(x in text for x in ("runway", "run out", "running out", "শেষ হচ্ছে", "দ্রুত শেষ", "কত দিন চলবে")):
        intent, confidence = "money_runway", .9
    elif any(x in text for x in ("why", "higher", "increase", "compare", "more this month", "কেন", "বেড়েছে", "বেশি খরচ")):
        intent, confidence = "compare_spending", .84
    elif any(x in text for x in ("health score", "financial health", "হেলথ স্কোর")):
        intent, confidence = "get_health_score", .9
    elif any(x in text for x in ("afford", "can i buy", "পারব", "কিনতে")) and amount_value:
        intent, confidence = "affordability_analysis", .88
        entities["amount"] = amount_value
    elif any(x in text for x in ("what happens if", "scenario", "if i spend", "খরচ করি")) and amount_value:
        intent, confidence = "simulate_scenario", .88
        entities["amount"] = amount_value; entities["scenario_kind"] = "purchase"
    elif any(x in text for x in ("recurring", "regular expense", "নিয়মিত খরচ")):
        intent, confidence = "show_recurring", .95
    elif any(x in text for x in ("spend", "spent", "spending", "expense", "খরচ", "ব্যয়", "food", "groceries")):
        intent, confidence = "explain_spending", .82
    elif any(x in text for x in ("recent transaction", "show transaction", "সাম্প্রতিক ট্রানজেকশন", "লেনদেন দেখ")):
        intent, confidence = "show_transactions", .9
    elif any(x in text for x in ("balance", "ব্যালেন্স", "কত টাকা আছে")):
        intent, confidence = "check_balance", .92
    elif any(x in text for x in ("recommend budget", "budget recommendation", "বাজেট সাজেশন")):
        intent, confidence = "get_budget_recommendation", .88
    elif any(x in text for x in ("my budget", "current budget", "বাজেট দেখ")):
        intent, confidence = "get_budget", .88
    elif any(x in text for x in ("offer", "discount", "অফার", "ডিসকাউন্ট")):
        intent, confidence = "get_offers", .85
    elif any(x in text for x in ("learn", "lesson", "শিখ", "লেসন")):
        intent, confidence = "get_learning_recommendations", .82
    elif any(x in text for x in ("safe to save", "how much save", "কত সেভ")):
        intent, confidence = "safe_to_save", .9
    elif any(x in text for x in ("budget", "বাজেট")):
        intent, confidence = "update_budget", .88
        if amount_value: entities["amount"] = amount_value
        categories = {"food": "Food", "খাবার": "Food", "transport": "Transport", "যাতায়াত": "Transport", "shopping": "Shopping"}
        for term, category in categories.items():
            if term in text: entities["category"] = category; break
    elif any(x in text for x in ("save", "saving", "laptop", "phone", "tv", "emergency", "buffer", "সেভ", "জমা", "ল্যাপটপ", "টিভি", "কিনতে চাই")) or (amount_value is not None and "by" in text and any(x in text for x in ("need", "want", "for"))):
        intent, confidence = "create_savings_goal", .86
        if amount_value is not None: entities["target_amount"] = amount_value
        if goal_name := _goal_name(message): entities["goal_name"] = goal_name
        months = _duration_months(message)
        if months is not None: entities["duration_months"] = months
        if deadline := _deadline(message): entities["deadline"] = deadline.isoformat()
    required = ACTIONS.get(intent, {}).get("required_fields", [])
    missing = [field for field in required if field not in entities]
    return ParsedIntent(intent=intent, confidence=confidence, language=language, entities=entities, missing_fields=missing, clarification_needed=bool(missing))

def understand_intent(message: str, context: dict | None = None) -> tuple[ParsedIntent, dict]:
    """Use Groq only as an untrusted JSON classifier, then validate locally.

    The parser has no tools, database access, or PIN access. Invalid output,
    rate limits, timeouts, and disabled configuration all use the deterministic
    parser below without changing any financial calculation.
    """
    routed, meta = groq_classify(message, ACTIONS, context)
    selected_action = routed.action if routed else None
    if routed and selected_action is None and routed.intent in ACTIONS:
        selected_action = routed.intent
    if routed and selected_action:
        entities = _json_data(routed.entities)
        # Guard against model-provided non-action junk and normalise numbers.
        allowed_entities = {"recipient", "amount", "currency", "goal_name", "target_amount", "duration_months", "category", "scenario_kind"}
        entities = {key: value for key, value in entities.items() if key in allowed_entities and isinstance(value, (str, int, float))}
        # Locally normalise typed entities. This is deliberately independent of
        # Groq so it cannot confuse a duration with BDT or author a calculation.
        if selected_action == "create_savings_goal":
            if amount := parse_amount(message): entities["target_amount"] = amount
            months = _duration_months(message)
            if months is not None: entities["duration_months"] = months
            if deadline := _deadline(message): entities["deadline"] = deadline.isoformat()
            if goal_name := _goal_name(message): entities["goal_name"] = goal_name
        parsed = ParsedIntent(intent=selected_action, confidence=routed.confidence, language="bn" if routed.language == "bn" else language_of(message), entities=entities)
        parsed.missing_fields = [key for key in ACTIONS[parsed.intent]["required_fields"] if key not in parsed.entities]
        parsed.clarification_needed = bool(parsed.missing_fields)
        return parsed, meta
    return fallback_intent(message), meta

def _say(language: str, en: str, bn: str) -> str: return bn if language == "bn" else en

def get_conversation(db: Session, user_id: int, conversation_id: str | None) -> AssistantConversation:
    conversation = db.get(AssistantConversation, conversation_id) if conversation_id else None
    if conversation and conversation.user_id != user_id: raise PermissionError("Conversation not found")
    if not conversation:
        conversation = AssistantConversation(id=str(uuid4()), user_id=user_id)
        db.add(conversation); db.commit(); db.refresh(conversation)
    return conversation

def _response(conversation, kind: str, message: str, **payload):
    return {"conversation_id": conversation.id, "type": kind, "message": message, **payload}

def _json_data(value):
    """JSON columns must never receive Decimal values from financial services."""
    def convert(item):
        if isinstance(item, Decimal):
            return float(item)
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        raise TypeError(f"Unsupported JSON value: {type(item)!r}")
    return json.loads(json.dumps(value, default=convert))

def explain_metric(conversation: AssistantConversation, metric: dict) -> dict:
    """Explain values already calculated by the product; this function never calculates or changes money."""
    context = metric.get("context") or {}
    value, unit, metric_id = metric.get("value"), metric.get("unit") or "", metric["metric_id"]
    def money(item):
        try: return f"৳{float(item):,.0f}"
        except (TypeError, ValueError): return str(item)
    def number(item):
        try: return f"{float(item):,.1f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError): return str(item)
    display = money(value) if unit == "BDT" else f"{number(value)}{unit if unit.startswith('/') else (' ' + unit if unit else '')}"
    title = metric["title"]
    if metric_id == "safe_to_spend":
        situation = f"The app has set aside commitments and a safety reserve, leaving about **{display}** as flexible spending room."
        meaning, why = "Safe to Spend is the amount left after planned needs and a buffer.", "It helps you separate money that is available for choices from money that may be needed soon."
    elif metric_id == "monthly_spending":
        situation = f"You have spent **{display}** in the current 30-day view."
        meaning, why = "Monthly Spending is the total money that went out during this period.", "Watching it over time helps you spot whether your usual spending is rising, falling, or staying steady."
    elif metric_id == "savings_rate":
        income, savings = context.get("monthlyIncome"), context.get("monthlySavings")
        situation = f"You are keeping about **{display}** of your income."
        if income is not None and savings is not None: situation += f" That reflects {money(savings)} saved from {money(income)} received this month."
        meaning, why = "Savings Rate is the share of income you keep rather than spend.", "It shows how much room your current income leaves for future goals or unexpected costs."
    elif metric_id == "money_runway":
        situation = f"At the spending assumptions already calculated by the app, your available money could cover roughly **{display}**."
        meaning, why = "Money Runway estimates how long available money may last if recent spending continues similarly.", "It gives an early signal to review spending or upcoming commitments before money becomes tight."
    elif metric_id == "financial_health_score":
        situation = f"Your current informational indicator is **{display}**{f' ({context["label"]})' if context.get("label") else ''}."
        meaning, why = "Financial Health Score combines several recent money habits into one educational indicator; it is not a credit score.", "It helps you see which habits may be supporting your financial resilience and which deserve attention."
    elif metric_id == "financial_health_factor":
        factor = context.get("factor") or title
        maximum = context.get("maximum")
        situation = f"Your **{factor}** factor is **{display}**{f' out of {number(maximum)}' if maximum is not None else ''}."
        meaning, why = "This is one part of your Financial Health Score, based on recent wallet activity and financial behavior.", "It helps show which individual money habit is supporting your financial resilience or may need attention."
    elif metric_id == "savings_goal_progress":
        situation = f"This goal is **{display}** complete."
        if context.get("saved") is not None and context.get("target") is not None: situation += f" You have saved {money(context['saved'])} toward a {money(context['target'])} target."
        meaning, why = "Savings Goal Progress shows how much of a chosen target has already been funded.", "It helps you judge whether your current saving pace is moving you toward the goal."
    elif metric_id == "spending_category_change":
        category = context.get("category") or title.replace(" Spending Change", "")
        situation = f"{category} changed by **{money(value)}** compared with the previous period."
        if context.get("current") is not None and context.get("previous") is not None: situation += f" It is {money(context['current'])} now versus {money(context['previous'])} before."
        meaning, why = "Spending Category Change compares one category with an earlier equivalent period.", "It helps identify where a change in your overall spending is coming from."
    else:  # remaining_budget
        situation = f"You have about **{display}** left within the budget currently shown by the app."
        meaning, why = "Remaining Budget is the planned limit minus spending already recorded in that budget period.", "It helps you pace flexible spending before the period ends."
    if metric.get("language") == "bn":
        bn_meaning = {
            "safe_to_spend": "নিরাপদে খরচ করার টাকা হলো প্রয়োজনীয় দায় ও সেফটি বাফার রাখার পর বাকি থাকা অংশ।",
            "monthly_spending": "মাসিক খরচ হলো এই সময়ের মধ্যে আপনার মোট টাকা বের হওয়ার পরিমাণ।",
            "savings_rate": "সেভিংস রেট দেখায় আয়ের কত অংশ আপনি খরচ না করে রেখে দিচ্ছেন।",
            "money_runway": "মানি রানওয়ে দেখায় বর্তমান খরচের ধারা চললে হাতে থাকা টাকা আনুমানিক কত দিন চলতে পারে।",
            "financial_health_score": "ফাইন্যান্সিয়াল হেলথ স্কোর সাম্প্রতিক আর্থিক অভ্যাসের একটি তথ্যভিত্তিক সূচক; এটি ক্রেডিট স্কোর নয়।",
            "financial_health_factor": "এটি ফাইন্যান্সিয়াল হেলথ স্কোরের একটি অংশ, যা সাম্প্রতিক ওয়ালেট কার্যক্রম ও আর্থিক অভ্যাস থেকে তৈরি।",
            "savings_goal_progress": "গোল প্রগ্রেস দেখায় আপনার নির্ধারিত সেভিংস লক্ষ্যের কতটা পূরণ হয়েছে।",
            "spending_category_change": "ক্যাটাগরি পরিবর্তন আগের সময়ের সঙ্গে একটি খরচের ধরন তুলনা করে।",
            "remaining_budget": "বাজেটে বাকি অর্থ হলো পরিকল্পিত সীমা থেকে ইতোমধ্যে হওয়া খরচ বাদ দেওয়ার পরের অংশ।",
        }[metric_id]
        bn_situation = {
            "safe_to_spend": f"অ্যাপের হিসাব অনুযায়ী প্রয়োজনীয় দায় ও রিজার্ভ রাখার পর প্রায় **{display}** নমনীয় খরচের জন্য আছে।",
            "monthly_spending": f"বর্তমান ৩০ দিনের হিসাবে আপনার খরচ **{display}**।",
            "savings_rate": f"আপনি আয়ের প্রায় **{display}** সঞ্চয় হিসেবে রাখছেন।",
            "money_runway": f"অ্যাপের ইতোমধ্যে করা খরচের হিসাব অনুযায়ী আপনার টাকা প্রায় **{display}** চলতে পারে।",
            "financial_health_score": f"আপনার বর্তমান তথ্যভিত্তিক সূচক **{display}**।",
            "financial_health_factor": f"আপনার **{context.get('factor') or title}** ফ্যাক্টরটি **{display}**।",
            "savings_goal_progress": f"এই লক্ষ্যটি **{display}** পূরণ হয়েছে।",
            "spending_category_change": f"আগের সময়ের তুলনায় এই খরচের ক্যাটাগরিতে পরিবর্তন **{money(value)}**।",
            "remaining_budget": f"বর্তমান বাজেট অনুযায়ী প্রায় **{display}** বাকি আছে।",
        }[metric_id]
        message = f"### এর মানে কী\n{bn_meaning}\n\n### আপনার অবস্থা\n{bn_situation}\n\n### কেন গুরুত্বপূর্ণ\nএটি বুঝলে খরচ, সঞ্চয় ও ভবিষ্যতের প্রয়োজন নিয়ে আরও সচেতন সিদ্ধান্ত নিতে সুবিধা হয়।\n\n### পরের প্রশ্ন\nচাইলে আপনি এই হিসাবের বিস্তারিত বা এর উন্নতির উপায় জানতে পারেন।"
    else:
        message = f"### What it means\n{meaning}\n\n### Your situation\n{situation}\n\n### Why it matters\n{why}\n\n### Next question\nYou can ask me to explain this in Bangla or to show the available calculation details."
    evidence = {"metric_id": metric_id, "title": title, "value": value, "unit": unit, "source": metric.get("source"), "context": context}
    return _insight(conversation, "explain_metric", f"Explain {title}", evidence, message)

# ─── Meta-intent helpers ───────────────────────────────────────────────────

def _is_meta_intent(message: str, conversation: AssistantConversation) -> str | None:
    """Return meta-intent name if message is a clarification/cancel/correction."""
    norm = normalize(message)
    # Cancellation is handled separately in handle_message.
    # Here we detect clarification_request and correction.
    if any(phrase in norm for phrase in CLARIFICATION_PHRASES):
        return "clarification_request"
    correction_patterns = {
        "no that's wrong", "that is wrong", "i made a mistake",
        "not that one", "ভুল", "আগেরটা", "ওটা না",
        "actually", "correction",
    }
    if any(p in norm for p in correction_patterns):
        return "correction"
    return None

def _is_new_action_intent(intent: str, active: str | None) -> bool:
    """True when intent is a substantive new action that should interrupt."""
    return (
        intent in ACTIONS
        and intent not in {active, "chat", "greeting", "thanks"}
    )

def _clear_invalid_pending_state(conversation: AssistantConversation) -> bool:
    """
    If a pending slot is NOT valid for the pending intent, discard it.
    Returns True if state was cleared.
    """
    if not conversation.active_intent or not conversation.slots:
        return False
    allowed = ALLOWED_SLOTS.get(conversation.active_intent, [])
    dirty = False
    slots = dict(conversation.slots)
    for key in list(slots.keys()):
        if not key.startswith("_") and key not in allowed:
            del slots[key]; dirty = True
    if dirty:
        conversation.slots = slots if slots else {}
        conversation.state = "IDLE"
        conversation.active_intent = None
    return dirty

def _check_loop_and_recover(conversation: AssistantConversation, missing_field: str, active_intent: str | None = None) -> dict | None:
    """
    Increment the reask counter for missing_field. If exceeded, trigger
    clarification_request instead of re-asking the same question.
    Returns a dict response when loop is broken, else None.
    """
    slots = conversation.slots or {}
    reask_key = f"_reask_{missing_field}"
    reask_count = (slots.get(reask_key) or 0) + 1
    slots[reask_key] = reask_count
    conversation.slots = slots
    # Use passed active_intent when available, fall back to conversation
    _active = active_intent or conversation.active_intent
    if reask_count > MAX_SLOT_REASK:
        # Build a context-aware amount question for affordability_analysis
        ctx = _conversation_context(conversation)
        amount_ctx = ctx.get("entities", {}).get("_amount_context", "")
        if conversation.active_intent == "affordability_analysis" and amount_ctx:
            amount_prompt_en = f"You've mentioned '{amount_ctx}' — what is the amount you'd like me to analyze?"
            amount_prompt_bn = f"আপনি '{amount_ctx}' উল্লেখ করেছেন — কত টাকার বিশ্লেষণ চান?"
        else:
            amount_prompt_en = "What amount should I use? Please give a number."
            amount_prompt_bn = "কত টাকা ব্যবহার করব? দয়া করে একটি সংখ্যা দিন।"
        prompts = {"amount": (amount_prompt_en, amount_prompt_bn)}
        en, bn = prompts.get(missing_field, (f"Please provide a valid {missing_field}.", f"দয়া করে একটি বৈধ {missing_field} দিন।"))
        return _response(
            conversation, "clarification_request",
            _say(conversation.language, en, bn),
            missing_fields=[missing_field],
        )
    return None

# ─── Context-aware missing-prompt ─────────────────────────────────────────

def _missing_prompt(conversation, missing: str, active_intent: str | None = None) -> dict:
    # Derive the correct question from the ACTUAL pending context.
    # Never hardcode "purchase price" — it only applies when the user
    # was explicitly talking about buying something.
    ctx = _conversation_context(conversation)
    pending_goal = ctx.get("entities", {}).get("goal_name") or ctx.get("goal_name") or ""
    pending_context = ctx.get("entities", {}).get("_amount_context") or ""

    prompts: dict[str, tuple[str, str]] = {
        "recipient": ("Who would you like to send money to?", "কাকে টাকা পাঠাতে চান?"),
        "amount": (
            f"What amount should I use for your analysis?{f' (e.g. for: {pending_context})' if pending_context else ''}",
            f"আপনার বিশ্লেষণের জন্য কত টাকা ব্যবহার করব?{f' (উদা: {pending_context})' if pending_context else ''}",
        ),
        "goal_name": ("What are you saving for? Please give a name for your goal.", "কিসের জন্য সেভ করতে চান? আপনার গোলের একটি নাম দিন।"),
        "target_amount": ("What is your savings target amount?", "আপনার সঞ্চয়ের লক্ষ্যমাত্রা কত টাকা?"),
        "duration_months": (
            "By when do you want to reach this goal? You can give a number of months or a date.",
            "কত দিনের মধ্যে বা কোন তারিখের মধ্যে এই লক্ষ্যে পৌঁছাতে চান?",
        ),
        "category": ("Which budget category should I update?", "কোন বাজেট ক্যাটাগরি পরিবর্তন করতে চান?"),
    }
    # Context-sensitive overrides
    if missing == "amount":
        if conversation.active_intent == "simulate_scenario":
            prompts["amount"] = ("What amount should I simulate? This will not change your balance.", "কত টাকার পরিস্থিতি হিসাব করব? এতে আপনার ব্যালেন্স বদলাবে না।")
        elif conversation.active_intent == "affordability_analysis":
            if pending_goal:
                prompts["amount"] = (
                    f"You asked about your '{pending_goal}' goal — what amount should I analyze for that goal?",
                    f"আপনি আপনার '{pending_goal}' গোল নিয়ে জিজ্ঞেস করেছিলেন — সেই গোলের জন্য কত টাকার বিশ্লেষণ চান?",
                )
            elif pending_context:
                prompts["amount"] = (
                    f"You mentioned '{pending_context}' — what amount should I use?",
                    f"আপনি '{pending_context}' উল্লেখ করেছেন — কত টাকা ব্যবহার করব?",
                )
            # else: falls through to the generic amount prompt (no hardcoded "purchase price")
    en, bn = prompts.get(missing, (f"Please provide a valid {missing}.", f"দয়া করে একটি বৈধ {missing} দিন।"))
    return _response(conversation, "clarification", _say(conversation.language, en, bn), missing_fields=[missing])

def _conversation_context(conversation: AssistantConversation) -> dict:
    """Only compact, non-secret references are kept between turns."""
    saved = (conversation.slots or {}).get("_context", {})
    return saved if isinstance(saved, dict) else {}

def _remember(conversation: AssistantConversation, parsed: ParsedIntent, message: str) -> None:
    # Replace action slots on every completed turn so a previous transfer's
    # recipient/amount cannot leak into a later request.  A collecting turn
    # already merges its accumulated fields into ``parsed.entities`` above.
    serializable_entities = _json_data(parsed.entities)
    slots = {"_context": {
        "intent": parsed.intent,
        "entities": {k: v for k, v in serializable_entities.items() if k not in {"pin", "password", "token", "secret"}},
        "last_user_message": message[:280],
    }}
    # Collection state must remain flat for the existing state machine.
    slots.update(serializable_entities)
    conversation.slots = slots

def _insight(conversation: AssistantConversation, intent: str, question: str, evidence: dict, fallback: str, *, response_type: str = "financial_insight", **payload) -> dict:
    text, ai_meta = groq_respond(question, evidence, conversation.language, fallback, _conversation_context(conversation))
    if get_settings().environment == "development":
        payload["debug"] = ai_meta
    return _response(conversation, response_type, text, intent=intent, status="completed", data=_json_data(evidence), **payload)

def handle_message(db: Session, user, conversation: AssistantConversation, message: str) -> dict:
    # PIN entry belongs exclusively to the authorization endpoint/modal. Do not
    # classify, persist, or send a credential-looking chat message to Groq.
    if re.search(r"(?:\b(?:pin|otp|password)\b|পিন)\s*[:=-]?\s*[০-৯\d]{4,}(?:\b|$)", message, re.I):
        return _response(conversation, "error", _say(conversation.language, "For your security, please do not send a PIN or password in chat. Use the secure confirmation prompt when an action requires it.", "নিরাপত্তার জন্য চ্যাটে PIN বা পাসওয়ার্ড পাঠাবেন না। কোনো কাজের জন্য দরকার হলে নিরাপদ কনফার্মেশন প্রম্পট ব্যবহার করুন।"))
    # Natural-language cancellation is safe and only affects a server-owned draft.
    if normalize(message) in {"cancel", "cancel it", "never mind", "বাদ", "বাতিল", "বাতিল করুন"} and conversation.pending_action_id:
        return cancel_action(db, user, conversation.pending_action_id)
    parsed, route_meta = understand_intent(message, _conversation_context(conversation))
    # A new high-confidence action always interrupts slot collection. Keeping
    # collection only for an unknown/neutral reply prevents savings fields from
    # leaking into a fresh transfer (and vice versa).
    if conversation.state == "COLLECTING_INFORMATION" and conversation.active_intent:
        # Fresh start for cross-intent slot pollution — clear slots that don't apply to current intent.
        active = conversation.active_intent  # save before clearing
        _clear_invalid_pending_state(conversation)
        slots = {key: value for key, value in dict(conversation.slots or {}).items() if not key.startswith("_")}
        is_new_action = parsed.intent in ACTIONS and parsed.intent not in {active, "chat", "greeting", "thanks"} and parsed.confidence >= .65
        if is_new_action:
            conversation.state = "IDLE"
            conversation.slots = {}
        # Step 5: When is_new_action is False (continuing same intent), always run
        # branch parsing. When is_new_action is True (user switched intents), guard so
        # branch parsing only runs when parsed intent matches active (no cross-intent pollution).
        if not is_new_action or parsed.intent == active:
            if active == "send_money":
                if "amount" not in slots and (value := parse_amount(message)): slots["amount"] = value
                if "recipient" not in slots and (value := _recipient(message)): slots["recipient"] = value
                if "recipient" not in slots and not parse_amount(message) and re.fullmatch(r"[A-Za-zঀ-৿][A-Za-zঀ-৿ .'-]{0,59}", message.strip()): slots["recipient"] = message.strip()
            elif active == "create_savings_goal":
                if "target_amount" not in slots and (value := parse_amount(message)): slots["target_amount"] = value
                if "duration_months" not in slots:
                    month = _duration_months(message)
                    if month is not None: slots["duration_months"] = month
                if "deadline" not in slots and (parsed_deadline := _deadline(message)): slots["deadline"] = parsed_deadline.isoformat()
                if "goal_name" not in slots and (parsed_goal_name := _goal_name(message)): slots["goal_name"] = parsed_goal_name
            elif active == "update_budget":
                if "amount" not in slots and (value := parse_amount(message)): slots["amount"] = value
                if "category" not in slots: slots["category"] = message.strip().title()[:40]
        if not is_new_action:
            parsed = ParsedIntent(intent=active, confidence=.9, language=conversation.language, entities=slots)
    # Deterministic context resolution for pronouns such as “why is it higher?”
    if parsed.intent in {"unknown", "chat"} and any(term in normalize(message) for term in ("why", "higher", "that", "it", "কেন", "বেশি", "ওটা")):
        prior = _conversation_context(conversation)
        if prior.get("intent") in {"explain_spending", "compare_spending", "show_transactions"}:
            parsed = ParsedIntent(intent="compare_spending", confidence=.8, language=conversation.language, entities=dict(prior.get("entities") or {}))
    conversation.language = parsed.language; conversation.active_intent = parsed.intent; _remember(conversation, parsed, message)
    db.add(conversation); db.commit()
    if parsed.intent not in ACTIONS or parsed.intent == "unknown":
        return _insight(conversation, "chat", message, {}, _say(parsed.language, "I can help with your balance, spending, savings, budgets, transactions, and supported transfer drafts. What would you like to check?", "আমি ব্যালেন্স, খরচ, সেভিংস, বাজেট, লেনদেন ও ট্রান্সফার ড্রাফট নিয়ে সাহায্য করতে পারি। কী জানতে চান?"))
    if parsed.intent == "mobile_recharge":
        return _response(conversation, "error", _say(parsed.language, "I understand the recharge request, but recharge is not connected to this prototype yet.", "আমি রিচার্জের অনুরোধটি বুঝেছি, কিন্তু এই প্রোটোটাইপে রিচার্জ এখনো সংযুক্ত নয়।"), action="mobile_recharge")
    required = ACTIONS[parsed.intent]["required_fields"]
    missing = [field for field in required if field not in parsed.entities]
    if parsed.intent == "create_savings_goal" and not (parsed.entities.get("duration_months") or parsed.entities.get("deadline")):
        missing.append("duration_months")
    if missing:
        conversation.state = "COLLECTING_INFORMATION"; db.commit()
        # Detect meta-intents BEFORE asking a clarifying question.
        # If user is confused/correcting, clear stale pending slots and retry.
        if (meta := _is_meta_intent(message, conversation)):
            conversation.state = "IDLE"
            conversation.active_intent = None
            conversation.slots = {}
            db.commit()
            if meta == "clarification_request":
                return _response(
                    conversation, "clarification_request",
                    _say(conversation.language,
                         "I understand you need more clarity. Try asking me about your balance, spending, savings goals, or a transfer — or tell me what you'd like to explore.",
                         "আপনাকে আরও ব্যাখ্যা দরকার বুঝতে পারছি। আপনার ব্যালেন্স, খরচ, সেভিংস গোল, বা ট্রান্সফার নিয়ে জিজ্ঞেস করুন।"),
                    missing_fields=missing,
                )
            if meta == "correction":
                return _response(
                    conversation, "correction",
                    _say(conversation.language,
                         "I sorry for the confusion. What would you like to do instead?",
                         "বিরক্ত করার জন্য দুঃখিত। আপনি কী করতে চান আমাকে বলুন।"),
                    missing_fields=missing,
                )
        return _missing_prompt(conversation, missing[0], conversation.active_intent)
    conversation.state = "PREPARING"; db.commit()
    result = prepare_action(db, user, conversation, parsed.intent, parsed.entities, message)
    # Development observability remains server-side; no keys, pins, or tokens are logged.
    if get_settings().environment == "development":
        if route_meta.get("provider") == "groq":
            print(f"AI provider: groq | Model: {route_meta.get('model')} | Intent: {parsed.intent} | Fallback: false")
        else:
            print(f"AI provider: deterministic | Intent: {parsed.intent} | Fallback: true | Reason: {route_meta.get('reason', 'route fallback')}")
    return result

def prepare_action(db: Session, user, conversation, action: str, slots: dict, question: str = "") -> dict:
    if action in {"chat", "greeting", "thanks"}:
        fallback = _say(conversation.language, "Hello! I can help you understand your money, plan savings, or safely prepare a supported transfer. What would you like to do?" if action == "greeting" else "You’re welcome. What would you like to explore next?" if action == "thanks" else "I’m here to help with your finances. You can ask about spending, savings, your balance, or a supported workflow.", "হ্যালো! আমি আপনার টাকা, খরচ, সেভিংস বা নিরাপদ ট্রান্সফার ড্রাফট নিয়ে সাহায্য করতে পারি। কী করতে চান?" if action == "greeting" else "স্বাগতম। এরপর কী জানতে চান?" if action == "thanks" else "আমি আপনার আর্থিক তথ্য ও পরিকল্পনা নিয়ে সাহায্য করতে পারি।")
        return _insight(conversation, action, question, {}, fallback)
    if action == "check_balance":
        data={"balance": amount(user.account.balance), "currency": "BDT"}
        return _insight(conversation, action, question, data, _say(conversation.language, f"Your available balance is **৳{float(user.account.balance):,.0f}**.", f"আপনার বর্তমান ব্যালেন্স **৳{float(user.account.balance):,.0f}**।"))
    if action == "safe_to_spend":
        data = calculate_safe_to_spend(db, user); return _insight(conversation, action, question, data, _say(conversation.language, f"You can safely spend about **৳{data['safe_to_spend']:,.0f}** after commitments and your safety reserve.", f"প্রয়োজনীয় খরচ ও সেফটি রিজার্ভের পর আপনি প্রায় **৳{data['safe_to_spend']:,.0f}** নিরাপদে খরচ করতে পারেন।"))
    if action == "explain_spending":
        data = run_out_analysis(db, user); return _insight(conversation, action, question, data, _say(conversation.language, f"You spent **৳{data['total_expense']:,.0f}** in the last 30 days. {data.get('largest_category_increase', {}).get('category', 'Your largest category')} is the biggest measured change.", f"গত ৩০ দিনে আপনার খরচ **৳{data['total_expense']:,.0f}**। সবচেয়ে বড় পরিবর্তন হয়েছে {data.get('largest_category_increase', {}).get('category', 'আপনার প্রধান খরচের ক্যাটাগরি')}তে।"))
    if action == "money_runway":
        data = money_runway(db, user)
        return _insight(conversation, action, question, data, _say(conversation.language, f"At your recent pace, your estimated money runway is about **{data['days']} days**.", f"সাম্প্রতিক খরচের হিসেবে আপনার টাকার আনুমানিক রানওয়ে প্রায় **{data['days']} দিন**।"))
    if action == "compare_spending":
        data = spending_comparison(db, user)
        category = next((item for item in data.get("categories", []) if item.get("difference", 0) > 0), None)
        fallback = (f"Your spending comparison is ready. {category['category']} increased by ৳{category['difference']:,.0f}." if category else "Your spending comparison is ready; there was no measured category increase.")
        return _insight(conversation, action, question, data, fallback)
    if action == "get_health_score":
        data = health_score(db, user)
        return _insight(conversation, action, question, data, f"Your informational financial health score is **{data.get('score', 0)}**. It is not a credit score.")
    if action == "get_budget":
        current = db.scalars(select(Budget).where(Budget.user_id == user.id, Budget.status == "active").order_by(Budget.id.desc())).first()
        summary = spending_summary(db, user.id)
        data = {"budget": {"total_limit": amount(current.total_limit), "categories": _json_data(current.categories), "remaining": amount(float(current.total_limit) - float(summary["total_spending"]))} if current else None, "spending": summary["total_spending"]}
        fallback = f"Your current budget has **৳{data['budget']['remaining']:,.0f}** remaining." if data["budget"] else "There is no active budget yet. I can help you prepare one."
        return _insight(conversation, action, question, data, fallback)
    if action == "get_budget_recommendation":
        data = budget_recommendation(db, user)
        return _insight(conversation, action, question, data, "Here is a budget recommendation based on your recorded income and spending.")
    if action == "safe_to_save":
        data = safe_to_save(db, user)
        return _insight(conversation, action, question, data, f"Based on the current calculation, about **৳{data.get('recommended', 0):,.0f}** may be a comfortable weekly saving amount. This does not move money automatically.")
    if action == "affordability_analysis":
        requested = float(slots["amount"])
        safe = calculate_safe_to_spend(db, user)
        data = {"purchase_amount": requested, "safe_to_spend": safe["safe_to_spend"], "current_balance": safe["current_balance"], "within_safe_to_spend": requested <= safe["safe_to_spend"]}
        fallback = f"A ৳{requested:,.0f} purchase is {'within' if data['within_safe_to_spend'] else 'above'} your calculated safe-to-spend amount of ৳{safe['safe_to_spend']:,.0f}."
        return _insight(conversation, action, question, data, fallback)
    if action == "simulate_scenario":
        requested = float(slots["amount"])
        data = simulate_scenario(db, user, str(slots.get("scenario_kind") or "purchase") if str(slots.get("scenario_kind") or "purchase") in {"reduce_spending", "save_more", "purchase", "unexpected_expense", "income_delay"} else "purchase", Decimal(str(requested)), 30)
        evidence = {"scenario": data, "scenario_amount": requested, "current_runway_days": data["current"]["runway_days"], "projected_runway_days": data["projected"]["runway_days"], "projected_balance": data["projected"]["balance"], "impact_level": data["impact_level"]}
        return _insight(conversation, action, question, evidence, f"I ran a read-only scenario for ৳{requested:,.0f}. It does not change your balance or transactions.")
    if action == "get_learning_recommendations":
        featured, for_you = get_personalized_lessons(db, user)
        lessons = [{"id": lesson.id, "title": lesson.title, "summary": lesson.summary, "reason": reason} for lesson, reason in (featured + for_you)[:5]]
        return _insight(conversation, action, question, {"lessons": lessons}, "I found learning content selected from your current financial signals.")
    if action == "get_offers":
        offers, preferences = get_all_offers(db, user.id)
        compact = [{key: item.get(key) for key in ("id", "title", "category", "fit_status", "potential_saving", "expiry_date")} for item in offers[:6]]
        return _insight(conversation, action, question, {"offers": compact, "preferences": preferences}, "Here are the currently available offers that the app found. I will not suggest spending extra just to unlock one.")
    if action == "show_recurring":
        data = spending_summary(db, user); return _insight(conversation, action, question, {"recurring_total": data["recurring_expenses"]}, _say(conversation.language, f"Your recurring expenses total ৳{data['recurring_expenses']:,.0f}.", f"আপনার নিয়মিত খরচ মোট ৳{data['recurring_expenses']:,.0f}।"))
    if action == "show_transactions":
        rows = list(db.scalars(select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.timestamp.desc()).limit(8)))
        return _response(conversation, "transaction_list", _say(conversation.language, "Here are your recent transactions.", "এগুলো আপনার সাম্প্রতিক ট্রানজেকশন।"), transactions=[{"id": x.id, "merchant_name": x.merchant_name, "amount": amount(x.amount), "direction": x.direction, "category": x.category, "timestamp": x.timestamp.isoformat()} for x in rows])
    if action == "send_money":
        contact, ambiguous = resolve_recipient(db, user.id, str(slots["recipient"]))
        if ambiguous:
            conversation.state = "COLLECTING_INFORMATION"
            conversation.slots = _json_data({key: value for key, value in slots.items() if key != "recipient"})
            db.commit()
            return _response(conversation, "selection", _say(conversation.language, "I found more than one matching person. Please choose one.", "একই নামে একাধিক ব্যক্তি পেয়েছি। একজনকে নির্বাচন করুন।"), options=[{"id": c.id, "name": c.name, "relationship": c.relationship, "phone_masked": c.phone_number[:3] + "••••" + c.phone_number[-4:]} for c in ambiguous])
        if not contact: return _response(conversation, "error", _say(conversation.language, f"I couldn't find a contact named {slots['recipient']}.", f"{slots['recipient']} নামে কোনো কনট্যাক্ট খুঁজে পাইনি।"))
        if contact.verification_status != "verified":
            return _response(conversation, "error", _say(conversation.language, f"{contact.name}'s saved details need verification before a transfer can be prepared. Review the number in Trusted People first.", f"ট্রান্সফারের আগে {contact.name}-এর সেভ করা তথ্য যাচাই করুন।"))
        value = float(slots["amount"]); safe = calculate_safe_to_spend(db, user)
        if value <= 0 or value > 1_000_000: return _response(conversation, "error", "That amount is not valid.")
        rel = classify_relationship(db, user.id, contact, contact.name, value)
        td = create_draft(db, user.id, contact.id, contact.name, contact.phone_number, value)
        preview = _json_data(get_draft_summary(db, td, user, rel, safe))
        draft = AssistantActionDraft(id=str(uuid4()), user_id=user.id, conversation_id=conversation.id, action_type=action, parameters={"recipient": contact.name, "amount": value}, preview=preview, transaction_draft_id=td.id, requires_authorization=True)
        db.add(draft); conversation.pending_action_id = draft.id; conversation.state = "READY_FOR_REVIEW"; db.commit()
        return _response(conversation, "action_preview", _say(conversation.language, "I prepared this transfer. Review it before continuing.", "ট্রান্সফারটি প্রস্তুত করেছি। এগোনোর আগে যাচাই করুন।"), action={"id": draft.id, "name": action, "status": draft.state, "requires_authorization": True}, preview=preview)
    if action == "create_savings_goal":
        try:
            goal = SavingsGoalEntities(
                goal_name=str(slots["goal_name"]),
                target_amount=Decimal(str(slots["target_amount"])),
                current_amount=Decimal("0"),
                duration_months=int(slots["duration_months"]) if slots.get("duration_months") is not None else None,
                deadline=date.fromisoformat(str(slots["deadline"])) if slots.get("deadline") else None,
            )
            # This is an affordability estimate for one month, not a replacement
            # for the required pace. The deterministic plan reports both values.
            capacity = safe_to_save(db, user, 30)
            plan = calculate_savings_plan(
                goal_name=goal.goal_name,
                target_amount=goal.target_amount,
                current_amount=goal.current_amount,
                duration_months=goal.duration_months,
                deadline=goal.deadline,
                monthly_capacity=Decimal(str(capacity["recommended"])),
            )
        except (ValueError, TypeError, InvalidOperation) as exc:
            return _response(conversation, "error", f"Please provide a valid positive goal amount and future timeline. ({exc})")
        preview = _json_data(plan.model_dump())
        preview["display_fields"] = _json_data([
            AssistantDisplayField(key="goal_name", label="Goal Name", value=plan.goal_name, value_type="text").model_dump(),
            AssistantDisplayField(key="target_amount", label="Target Amount", value=plan.target_amount, value_type="currency").model_dump(),
            AssistantDisplayField(key="duration_months", label="Duration", value=plan.duration_months, value_type="months").model_dump(),
            AssistantDisplayField(key="deadline", label="Deadline", value=plan.deadline.isoformat(), value_type="date").model_dump(),
            AssistantDisplayField(key="required_monthly_contribution", label="Required Monthly Saving", value=plan.required_monthly_contribution, value_type="currency").model_dump(),
        ] + ([
            AssistantDisplayField(key="affordable_monthly_contribution", label="Comfortable Monthly Saving", value=plan.affordable_monthly_contribution, value_type="currency").model_dump()
        ] if plan.affordable_monthly_contribution is not None else []))
        draft = AssistantActionDraft(id=str(uuid4()), user_id=user.id, conversation_id=conversation.id, action_type=action, parameters=preview, preview=preview)
        db.add(draft); conversation.pending_action_id=draft.id; conversation.state="READY_FOR_REVIEW"; db.commit()
        return _response(conversation, "savings_plan", _say(conversation.language, "Your savings plan is ready to review.", "আপনার সেভিংস প্ল্যান রিভিউয়ের জন্য প্রস্তুত।"), action={"id": draft.id, "name": action, "status": draft.state}, preview=preview)
    # Budget update is persisted only after confirm.
    preview = {"category": slots["category"], "monthly_limit": float(slots["amount"])}
    draft = AssistantActionDraft(id=str(uuid4()), user_id=user.id, conversation_id=conversation.id, action_type=action, parameters=preview, preview=preview)
    db.add(draft); conversation.pending_action_id=draft.id; conversation.state="READY_FOR_REVIEW"; db.commit()
    return _response(conversation, "action_preview", "Review this budget update before confirming.", action={"id": draft.id, "name": action, "status": draft.state}, preview=preview)

def confirm_action(db: Session, user, action_id: str) -> dict:
    draft = db.get(AssistantActionDraft, action_id)
    if not draft or draft.user_id != user.id: raise PermissionError("Action not found")
    if draft.state != "READY_FOR_REVIEW": raise ValueError("This action can no longer be confirmed")
    if draft.action_type == "send_money":
        tx = db.get(__import__("app.models", fromlist=["TransactionDraft"]).TransactionDraft, draft.transaction_draft_id)
        review_draft(db, tx); confirm_draft(db, tx); draft.state="AWAITING_AUTHORIZATION"; db.commit()
        return {"type": "authorization_required", "message": "Enter your PIN to complete this demo transfer.", "action": {"id": draft.id, "name": draft.action_type, "status": draft.state}}
    draft.state="CONFIRMED"; db.commit()
    return execute_nonfinancial(db, user, draft)

def execute_nonfinancial(db: Session, user, draft: AssistantActionDraft) -> dict:
    if draft.state not in {"CONFIRMED", "EXECUTING"}: raise ValueError("Action is not ready")
    draft.state="EXECUTING"; db.commit(); parameters=draft.parameters
    if draft.action_type == "create_savings_goal":
        goal=SavingsGoal(user_id=user.id,name=parameters["goal_name"],target_amount=parameters["target_amount"],current_amount=0,target_date=date.fromisoformat(parameters["deadline"])); db.add(goal); db.flush(); result={"goal_id": goal.id, "name": goal.name}
    elif draft.action_type == "update_budget":
        current=db.scalars(select(Budget).where(Budget.user_id==user.id,Budget.status=="active")).first(); categories=dict(current.categories) if current else {}; categories[parameters["category"]]=parameters["monthly_limit"]; total=max(float(current.total_limit) if current else 0, sum(float(v) for v in categories.values()));
        if current: current.categories=categories; current.total_limit=total; result={"budget_id":current.id}
        else:
            current=Budget(user_id=user.id,total_limit=total,categories=categories,start_date=date.today()-timedelta(days=29),end_date=date.today()); db.add(current); db.flush(); result={"budget_id":current.id}
    else: raise ValueError("Unsupported action")
    draft.state="COMPLETED"; db.commit(); return {"type":"success","message":"Your request was completed.","action":{"id":draft.id,"name":draft.action_type,"status":draft.state},"result":result}

def authorize_action(db: Session, user, action_id: str, pin: str) -> dict:
    draft=db.get(AssistantActionDraft, action_id)
    if not draft or draft.user_id != user.id: raise PermissionError("Action not found")
    if draft.action_type != "send_money" or draft.state != "AWAITING_AUTHORIZATION": raise ValueError("Action is not awaiting authorization")
    tx=db.get(__import__("app.models", fromlist=["TransactionDraft"]).TransactionDraft, draft.transaction_draft_id)
    success, message=verify_pin(db, tx, pin)
    if not success: return {"type":"error","message":message,"action":{"id":draft.id,"status":draft.state}}
    draft.state="COMPLETED"; db.commit()
    return {"type":"success","message":"Demo transfer completed. No real money moved.","action":{"id":draft.id,"name":"send_money","status":draft.state},"result":{"balance_after":float(user.account.balance)}}

def cancel_action(db: Session, user, action_id: str) -> dict:
    draft=db.get(AssistantActionDraft, action_id)
    if not draft or draft.user_id != user.id: raise PermissionError("Action not found")
    if draft.state in {"COMPLETED", "CANCELLED"}: raise ValueError("Action can no longer be cancelled")
    if draft.transaction_draft_id:
        tx=db.get(__import__("app.models", fromlist=["TransactionDraft"]).TransactionDraft, draft.transaction_draft_id)
        if tx and tx.state not in {DraftState.COMPLETED.value, DraftState.CANCELLED.value}: cancel_draft(db, tx)
    draft.state="CANCELLED"; db.commit(); return {"type":"success","message":"The action was cancelled. No money moved."}
