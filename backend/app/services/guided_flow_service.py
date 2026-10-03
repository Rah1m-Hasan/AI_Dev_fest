"""Guided Flow service for step-by-step transaction guidance.

Helps users who prefer conversational interaction, especially elderly/low-tech users.
One question at a time, large text, simple wording.
"""
from dataclasses import dataclass, field
from enum import Enum


class FlowState(Enum):
    IDLE = "idle"
    CHOOSING_RECIPIENT = "choosing_recipient"
    CONFIRMING_RECIPIENT = "confirming_recipient"
    ENTERING_AMOUNT = "entering_amount"
    REVIEWING_DRAFT = "reviewing_draft"
    AWAITING_PIN = "awaiting_pin"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class GuidedFlowSession:
    """In-memory session for guided flow. Not persisted to DB."""
    user_id: int
    state: FlowState = FlowState.IDLE
    recipient_id: int | None = None
    recipient_name: str | None = None
    recipient_phone: str | None = None
    amount: float | None = None
    draft_id: int | None = None
    step: int = 1
    total_steps: int = 4  # Choose person, Enter amount, Review, Confirm
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "state": self.state.value,
            "recipient_id": self.recipient_id,
            "recipient_name": self.recipient_name,
            "recipient_phone": self.recipient_phone,
            "amount": self.amount,
            "draft_id": self.draft_id,
            "step": self.step,
            "total_steps": self.total_steps,
        }


# In-memory storage for active sessions (per-user)
_active_sessions: dict[int, GuidedFlowSession] = {}


def get_session(user_id: int) -> GuidedFlowSession | None:
    """Get active guided session for user."""
    return _active_sessions.get(user_id)


def create_session(user_id: int) -> GuidedFlowSession:
    """Create a new guided session."""
    session = GuidedFlowSession(
        user_id=user_id,
        state=FlowState.CHOOSING_RECIPIENT,
        step=1,
    )
    _active_sessions[user_id] = session
    return session


def update_session(user_id: int, **kwargs) -> GuidedFlowSession | None:
    """Update session fields."""
    session = _active_sessions.get(user_id)
    if session:
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        _active_sessions[user_id] = session
    return session


def cancel_session(user_id: int) -> bool:
    """Cancel and remove session."""
    if user_id in _active_sessions:
        _active_sessions[user_id].state = FlowState.CANCELLED
        del _active_sessions[user_id]
        return True
    return False


def get_flow_prompt(session: GuidedFlowSession) -> tuple[str, list[str]]:
    """Get the current prompt and available actions for the session state.

    Returns (prompt_text, available_actions).
    """
    if session.state == FlowState.CHOOSING_RECIPIENT:
        prompt = "Who would you like to send money to?"
        actions = ["Cancel", "Back"]
    elif session.state == FlowState.CONFIRMING_RECIPIENT:
        prompt = f"Do you mean {session.recipient_name}?"
        actions = ["Yes, that's right", "Choose someone else", "Cancel"]
    elif session.state == FlowState.ENTERING_AMOUNT:
        prompt = "How much would you like to send?"
        actions = ["Back", "Cancel"]
    elif session.state == FlowState.REVIEWING_DRAFT:
        prompt = "Please review your transfer before confirming."
        actions = ["Confirm transfer", "Change amount", "Change person", "Cancel"]
    elif session.state == FlowState.AWAITING_PIN:
        prompt = "Enter your PIN to confirm the transfer."
        actions = []
    else:
        prompt = "What would you like to do?"
        actions = ["Cancel"]

    return prompt, actions


def handle_flow_command(
    session: GuidedFlowSession,
    user_input: str,
    contacts: list,
) -> tuple[str, GuidedFlowSession, bool]:
    """Handle user input in guided flow.

    Returns (response_text, updated_session, should_end_turn).
    """
    user_input_lower = user_input.lower().strip()

    # Handle universal commands
    if user_input_lower in ["cancel", "বাতিল", "না"]:
        cancel_session(session.user_id)
        return "Transfer cancelled. Is there anything else I can help with?", session, True

    if user_input_lower in ["back", "go back", "ফিরে যাই", "পিছনে"]:
        if session.state == FlowState.ENTERING_AMOUNT:
            session.state = FlowState.CHOOSING_RECIPIENT
            session.recipient_id = None
            session.recipient_name = None
            session.step = 1
            return "Who would you like to send money to?", session, False
        elif session.state == FlowState.REVIEWING_DRAFT:
            session.state = FlowState.ENTERING_AMOUNT
            session.amount = None
            session.step = 2
            return "How much would you like to send?", session, False

    if user_input_lower.startswith("change amount") or user_input_lower == "amount":
        session.state = FlowState.ENTERING_AMOUNT
        session.amount = None
        session.step = 2
        return "How much would you like to send?", session, False

    if user_input_lower.startswith("change person") or "change recipient" in user_input_lower:
        session.state = FlowState.CHOOSING_RECIPIENT
        session.recipient_id = None
        session.recipient_name = None
        session.step = 1
        return "Who would you like to send money to?", session, False

    # State-specific handling
    if session.state == FlowState.CHOOSING_RECIPIENT:
        # Look for matching contact
        for contact in contacts:
            name_lower = contact.name.lower()
            if name_lower in user_input_lower or user_input_lower in name_lower:
                session.recipient_id = contact.id
                session.recipient_name = contact.name
                session.recipient_phone = contact.phone_number
                session.state = FlowState.CONFIRMING_RECIPIENT
                session.step = 1
                return f"Do you mean {contact.name} ({contact.relationship})?", session, False

        # No match found - ask for clarification
        return "I couldn't find that person. Could you try a different name or say 'Help me find someone'?", session, False

    elif session.state == FlowState.CONFIRMING_RECIPIENT:
        if user_input_lower in ["yes", "yes that's right", "correct", "হ্যাঁ", "জি", "যা"]:
            session.state = FlowState.ENTERING_AMOUNT
            session.step = 2
            return "How much would you like to send?", session, False
        elif user_input_lower in ["no", "choose someone else", "না", "অন্য কাউকে"]:
            session.state = FlowState.CHOOSING_RECIPIENT
            session.recipient_id = None
            session.recipient_name = None
            return "Who would you like to send money to?", session, False

    elif session.state == FlowState.ENTERING_AMOUNT:
        # Try to extract amount
        import re
        match = re.search(r"[\d,]+", user_input)
        if match:
            amount = float(match.group().replace(",", ""))
            if amount > 0:
                session.amount = amount
                session.state = FlowState.REVIEWING_DRAFT
                session.step = 3
                return _build_review_message(session), session, False
            else:
                return "Please enter an amount greater than zero.", session, False
        else:
            return "I couldn't understand the amount. Please enter a number like 500 or 2000.", session, False

    return "I'm not sure what you mean. Would you like to continue or cancel?", session, False


def _build_review_message(session: GuidedFlowSession) -> str:
    """Build the review message for the current session."""
    return (
        f"I've prepared your transfer:\n\n"
        f"To: {session.recipient_name}\n"
        f"Amount: ৳{session.amount:,.0f}\n\n"
        f"Please review and confirm."
    )
