"""Deterministic intent parsing for the AI Financial Coach.

All numerical financial calculations remain in Python/backend logic.
LLM may only classify intent and extract entities from natural language.
"""
import re
from dataclasses import dataclass

# Supported intents
INTENTS = {
    "send_money",
    "check_balance",
    "safe_to_spend",
    "transaction_history",
    "recipient_lookup",
    "mobile_recharge",
    "bill_payment",
    "financial_question",
    "guided_send_money",
    "spending_analysis",
    "money_runway",
    "savings_help",
}

# Bangla/Banglish keywords mapping
SEND_MONEY_PATTERNS = [
    r"send", r"pathabo", r"pathao", r"dao", r"diye", r"dibo",
    r"পাঠাব", r"দাও", r"দিব", r"প্রেরণ", r"ট্রান্সফার",
    r"transfer", r"পেমেন্ট", r"payment", r"বাকি", r"রিমিট",
]

BALANCE_PATTERNS = [
    r"balance", r"ব্যালেন্স", r"একাউন্ট", r"account", r"কত আছে",
    r"কত টাকা আছে", r"how much", r"কারেন্ট", r"current balance",
]

SAFE_TO_SPEND_PATTERNS = [
    r"safe", r"spend", r"খরচ", r"ব্যয়", r"সেফ", r"কত খরচ করতে পারি",
    r"afford", r"কত ব্যয়", r"flexible", r"ফ্লেক্সিবল",
]

RUNWAY_PATTERNS = [
    r"runway", r"running short", r"run short", r"salary.*(before|age)",
    r"balance.*(last|tikbe|টিকবে)", r"কত দিন", r"শেষ হয়ে", r"চলবে",
]

SPENDING_ANALYSIS_PATTERNS = [
    r"why.*(spend|spent|short|low)", r"why am i running short", r"why.*খরচ",
    r"eto.*(khoroch|taka)", r"কেন.*(খরচ|টাকা)", r"where.*money",
]

SAVINGS_PATTERNS = [
    r"help me save", r"emergency fund", r"save for", r"সেভ", r"জমানো",
    r"buy a laptop", r"laptop", r"phone", r"কেনার", r"কিনতে চাই",
    r"saving goal", r"save up", r"save money", r"want to save",
    r"how much to save", r"৳[\d,]+.*months?", r"months.*৳",
]

HISTORY_PATTERNS = [
    r"history", r"transaction", r"লেনদেন", r"ট্রানজাকশন", r"transection",
    r"একাউন্ট", r"কি কি হয়েছে", r"দেখ", r"show", r"গেল কোথায়",
]

RECIPIENT_LOOKUP_PATTERNS = [
    r"who", r"কে", r"কাকে", r"কার",
    r"যাকে", r"তাকে", r"বাকে", r"পরিচিত", r"নম্বর", r"phone",
]

MOBILE_RECHARGE_PATTERNS = [
    r"recharge", r"রিচার্জ", r"মোবাইল", r"সিম", r"নম্বর চার্জ",
    r"top up", r"টপ আপ", r"ব্যালেন্স রিচার্জ",
]

BILL_PAYMENT_PATTERNS = [
    r"bill", r"বিল", r"পেমেন্ট", r"বিদ্যুৎ", r"গ্যাস", r"পানি",
    r"utility", r"আবাসন", r"ভাড়া", r"rent",
]

GUIDANCE_PATTERNS = [
    r"help me", r"সাহায্য", r"কিভাবে", r"how to", r"কি করব",
    r"বলো", r"বল", r"guide", r"গাইড", r"ধাপ", r"step",
]

RELATIONSHIP_TERMS = {
    "son": ["son", "ছেলে", "পুত্র", "ছেলেে", "মেয়ে না", "মেয়ের"],
    "daughter": ["daughter", "মেয়ে", "কন্যা", "মেয়ের"],
    "wife": ["wife", "স্ত্রী", "বউ", "গৃহিনী"],
    "husband": ["husband", "স্বামী", "বর"],
    "mother": ["mother", "মা", "মায়ের", "মাকে"],
    "father": ["father", "বাবা", "বাবার", "বাবাকে", "আব baba"],
    "brother": ["brother", "ভাই", "ভাইয়ের", "ভাইকে"],
    "sister": ["sister", "বোন", "বোনের", "বোনকে"],
    "friend": ["friend", "বন্ধু", "বন্ধুর", "বন্ধুকে"],
    "landlord": ["landlord", "বাড়িওয়ালা", "মালিক", "গৃহকর্তা", "ভাড়াটিয়া"],
    "customer": ["customer", "কাস্টমার", "গ্রাহক", "দোকানদার", "shopkeeper"],
}


@dataclass
class ParsedIntent:
    intent: str
    recipient_query: str | None
    amount: float | None
    currency: str
    reference: str | None
    confidence: float
    language: str
    raw_query: str


def _extract_amount(text: str) -> float | None:
    """Extract amount from text. Returns value in BDT."""
    text = text.lower().translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    # Handle ৳ symbol
    taka_patterns = [
        r"(?:৳|tk\.?\s*)([\d,]+(?:\.\d+)?)",
        r"([\d,]+(?:\.\d+)?)\s*(?:৳|taka|tk)",
        r"([\d,]+(?:\.\d+)?)",
    ]
    for pattern in taka_patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).replace(",", "")
            return float(value)
    return None


def _extract_recipient_query(text: str) -> str | None:
    """Extract recipient name/query from text."""
    text = text.lower()
    # Remove common action words and amounts
    patterns = [
        # Banglish: "Rafi ke 2000 taka pathabo". Keep this before the more
        # permissive patterns so an amount or verb can never become a name.
        r"\b([a-z][a-z .'-]{1,48}?)\s+ke\s+(?:(?:\d[\d,]*\s*(?:taka|tk|৳)?)|(?:taka\s+))",
        r"\b([a-z][a-z .'-]{1,48}?)\s+ke\s+(?:pathabo|pathao|dibo|dao|send|transfer)",
        # Bangla: "রাফিকে ২০০০ টাকা পাঠাব" / "রাফি কে ২০০০ টাকা পাঠাব".
        r"([ঀ-৿]{2,40}?)(?:কে|\s+কে)\s*(?:[০-৯\d,]+\s*)?(?:টাকা|৳)?",
        r"(?:to|প্রতি|কে|রে|কে|যাকে|তাকে|বাকে)\s+([a-zA-Zঀ-৿\s]{1,50})",
        r"(?:send|pay|pathabo|dao)\s+(?:money\s+)?(?:to\s+)?([a-zA-Zঀ-৿\s]{1,50})",
        r"([a-zA-Zঀ-৿]{2,30})\s+(?:এ|ে|কে|রে)",
        r"(?:my\s+)?(?:son|daughter|wife|husband|mother|father|brother|sister|friend|landlord)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip().lower()
            # Filter out generic/money-related words that are not recipients
            invalid = {"money", "taka", "tk", "amount", "some", "payment", "send", "pay", "to"}
            if candidate not in invalid and not candidate.isdigit():
                return match.group(1).strip()
    return None


def _detect_language(text: str) -> str:
    """Detect if text is primarily Bangla or English/Banglish."""
    bengali_chars = len(re.findall(r"[ঀ-৿]", text))
    if bengali_chars > len(text) * 0.3:
        return "bn"
    return "en"


def _classify_intent(text: str) -> tuple[str, float]:
    """Classify intent based on keyword matching. Returns (intent, confidence)."""
    text_lower = text.lower()

    # Check for guided/send money first (most specific)
    guidance_trigger = any(re.search(p, text_lower) for p in GUIDANCE_PATTERNS)
    send_trigger = any(re.search(p, text_lower) for p in SEND_MONEY_PATTERNS)

    if any(re.search(p, text_lower) for p in SPENDING_ANALYSIS_PATTERNS):
        return "spending_analysis", 0.90

    if any(re.search(p, text_lower) for p in RUNWAY_PATTERNS):
        return "money_runway", 0.88

    if any(re.search(p, text_lower) for p in SAVINGS_PATTERNS):
        return "savings_help", 0.86

    if guidance_trigger and send_trigger:
        return "guided_send_money", 0.92

    if guidance_trigger:
        return "guided_send_money", 0.88

    if send_trigger:
        return "send_money", 0.90

    # Check safe-to-spend BEFORE balance - "how much can I safely spend" has both
    if any(re.search(p, text_lower) for p in SAFE_TO_SPEND_PATTERNS):
        return "safe_to_spend", 0.85

    if any(re.search(p, text_lower) for p in BALANCE_PATTERNS):
        return "check_balance", 0.88

    if any(re.search(p, text_lower) for p in HISTORY_PATTERNS):
        return "transaction_history", 0.85

    if any(re.search(p, text_lower) for p in MOBILE_RECHARGE_PATTERNS):
        return "mobile_recharge", 0.82

    if any(re.search(p, text_lower) for p in BILL_PAYMENT_PATTERNS):
        return "bill_payment", 0.80

    if any(re.search(p, text_lower) for p in RECIPIENT_LOOKUP_PATTERNS):
        return "recipient_lookup", 0.78

    return "financial_question", 0.65


def parse_intent(query: str) -> ParsedIntent:
    """Parse user query into structured intent.

    This is deterministic fallback parsing. If Groq is available,
    it can refine this parsing with LLM understanding.
    """
    query_clean = query.strip()
    language = _detect_language(query_clean)
    intent, base_confidence = _classify_intent(query_clean)
    amount = _extract_amount(query_clean)
    recipient_query = _extract_recipient_query(query_clean)

    # Calculate confidence based on data quality
    confidence = base_confidence
    if amount is not None:
        confidence += 0.05
    if recipient_query is not None:
        confidence += 0.05
    confidence = min(0.99, confidence)

    return ParsedIntent(
        intent=intent,
        recipient_query=recipient_query,
        amount=amount,
        currency="BDT",
        reference=None,
        confidence=round(confidence, 2),
        language=language,
        raw_query=query_clean,
    )


def resolve_relationship_term(term: str) -> str | None:
    """Map relationship terms like 'my son' to standardized relationship types."""
    term_lower = term.lower().strip()

    # Check for "my X" patterns
    for relationship, patterns in RELATIONSHIP_TERMS.items():
        for pattern in patterns:
            if f"my {pattern}" in term_lower or term_lower == pattern:
                return relationship

    return None
