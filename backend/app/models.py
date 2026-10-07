from datetime import datetime, date
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, Date, ForeignKey, Text, JSON, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    persona: Mapped[str] = mapped_column(String(40), default="student")
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    account: Mapped["Account"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    goals: Mapped[list["SavingsGoal"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    balance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    user: Mapped[User] = relationship(back_populates="account")

# The following supporting entities keep the production data model extensible;
# the demo currently materializes the entities that drive active user flows.
class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True); locale: Mapped[str] = mapped_column(String(8), default="en")
class UserPhone(Base):
    __tablename__ = "user_phones"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[int] = mapped_column(primary_key=True); name: Mapped[str] = mapped_column(String(120), index=True); category: Mapped[str] = mapped_column(String(40))
class TransactionCategory(Base):
    __tablename__ = "transaction_categories"
    id: Mapped[int] = mapped_column(primary_key=True); name: Mapped[str] = mapped_column(String(40), unique=True); is_essential: Mapped[bool] = mapped_column(Boolean, default=False)

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    direction: Mapped[str] = mapped_column(String(10))
    transaction_type: Mapped[str] = mapped_column(String(40))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    balance_before: Mapped[float] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[float] = mapped_column(Numeric(14, 2))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(30), default="synthetic_demo")
    description: Mapped[str] = mapped_column(String(180), default="")
    user: Mapped[User] = relationship(back_populates="transactions")
    __table_args__ = (Index("ix_transactions_user_timestamp", "user_id", "timestamp"),)

class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    total_limit: Mapped[float] = mapped_column(Numeric(14, 2))
    period_type: Mapped[str] = mapped_column(String(20), default="monthly")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    categories: Mapped[dict] = mapped_column(JSON, default=dict)
    user: Mapped[User] = relationship(back_populates="budgets")

class PlanState(Base):
    """The user's saved monthly-plan choices, separate from the active budget.

    A budget remains the source used by existing dashboard and alert flows.  This
    record lets a person save a customised plan as a draft before explicitly
    activating it.
    """
    __tablename__ = "plan_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="recommended")
    essentials: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    flexible: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    savings: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    safety_buffer: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    categories: Mapped[dict] = mapped_column(JSON, default=dict)
    budget_id: Mapped[int | None] = mapped_column(ForeignKey("budgets.id"), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SavingsGoal(Base):
    __tablename__ = "savings_goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    current_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    target_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    user: Mapped[User] = relationship(back_populates="goals")

class GoalPlanSettings(Base):
    """Persistent user choices for a goal's savings plan."""
    __tablename__ = "goal_plan_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("savings_goals.id"), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(40), default="Other")
    saving_preference: Mapped[str] = mapped_column(String(20), default="flexible")
    note: Mapped[str | None] = mapped_column(String(280), nullable=True)
    planned_monthly_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    id: Mapped[int] = mapped_column(primary_key=True); budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"), index=True); category: Mapped[str] = mapped_column(String(40)); limit_amount: Mapped[float] = mapped_column(Numeric(14, 2)); spent_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
class SavingsContribution(Base):
    __tablename__ = "savings_contributions"
    id: Mapped[int] = mapped_column(primary_key=True); goal_id: Mapped[int] = mapped_column(ForeignKey("savings_goals.id"), index=True); amount: Mapped[float] = mapped_column(Numeric(14, 2)); contributed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class FinancialInsight(Base):
    __tablename__ = "financial_insights"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); insight_type: Mapped[str] = mapped_column(String(40)); evidence: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class FinancialHealthSnapshot(Base):
    __tablename__ = "financial_health_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); score: Mapped[float] = mapped_column(Numeric(5, 2)); explanation_json: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class Forecast(Base):
    __tablename__ = "forecasts"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); horizon_days: Mapped[int] = mapped_column(Integer); payload: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    body: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

class CategoryFeedback(Base):
    __tablename__ = "category_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    old_category: Mapped[str] = mapped_column(String(40))
    new_category: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FinancialLesson(Base):
    __tablename__ = "financial_lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(140))
    summary: Mapped[str] = mapped_column(String(280))
    content: Mapped[str] = mapped_column(Text)
    content_bn: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    duration_minutes: Mapped[int] = mapped_column(default=2)
    personalized_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    personalized_section_bn: Mapped[str | None] = mapped_column(Text, nullable=True)
    quiz: Mapped[dict] = mapped_column(JSON, default=dict)
    trigger_type: Mapped[str] = mapped_column(String(60), index=True)
    trigger_rule: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("financial_lessons.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    quiz_score: Mapped[int | None] = mapped_column(nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),)

class SavedOffer(Base):
    __tablename__ = "saved_offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "offer_id", name="uq_saved_offer_user_offer"),)
class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(140))
    terms: Mapped[str] = mapped_column(Text)
    terms_bn: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    min_spend: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    discount_fixed: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    max_discount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    typical_purchase: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    typical_merchant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    potential_saving: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    eligibility_notes: Mapped[str | None] = mapped_column(String(280), nullable=True)
    learning_lesson_id: Mapped[int | None] = mapped_column(ForeignKey("financial_lessons.id"), nullable=True)
class UserOfferPreference(Base):
    __tablename__ = "user_offer_preferences"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True); personalized_offers_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True); conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversations.id"), index=True); role: Mapped[str] = mapped_column(String(12)); content: Mapped[str] = mapped_column(Text); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Server-owned state for the natural-language action assistant.  It contains
# action slots and draft references only; PINs and authorization secrets never
# enter this table or chat history.
class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    active_intent: Mapped[str | None] = mapped_column(String(60), nullable=True)
    state: Mapped[str] = mapped_column(String(40), default="IDLE")
    slots: Mapped[dict] = mapped_column(JSON, default=dict)
    language: Mapped[str] = mapped_column(String(8), default="en")
    pending_action_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AssistantActionDraft(Base):
    __tablename__ = "assistant_action_drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("assistant_conversations.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(60), index=True)
    state: Mapped[str] = mapped_column(String(40), default="READY_FOR_REVIEW")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    preview: Mapped[dict] = mapped_column(JSON, default=dict)
    transaction_draft_id: Mapped[int | None] = mapped_column(ForeignKey("transaction_drafts.id"), nullable=True)
    requires_authorization: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class UserFeedback(Base):
    __tablename__ = "user_feedback"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); feedback_type: Mapped[str] = mapped_column(String(40)); payload: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TrustedContact(Base):
    __tablename__ = "trusted_contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    phone_number: Mapped[str] = mapped_column(String(20))
    # E.164-ish local canonical form (8801XXXXXXXXX), used only for matching
    # and de-duplication. `phone_number` remains the display-safe source.
    normalized_phone: Mapped[str] = mapped_column(String(20), index=True)
    relationship: Mapped[str] = mapped_column(String(40), default="Known")
    nickname: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(280), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified", index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Retained for compatibility with early assistant records. New UI never
    # calls a saved person "trusted" merely because it has history.
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    __table_args__ = (UniqueConstraint("user_id", "normalized_phone", name="uq_trusted_contact_user_phone"),)

class PaymentRequest(Base):
    """A user-created request; it never represents money received or sent."""
    __tablename__ = "payment_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trusted_contact_id: Mapped[int] = mapped_column(ForeignKey("trusted_contacts.id"), index=True)
    recipient_name: Mapped[str] = mapped_column(String(80))
    recipient_phone: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    note: Mapped[str | None] = mapped_column(String(140), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="requested", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class TrustedContactAudit(Base):
    __tablename__ = "trusted_contact_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trusted_contact_id: Mapped[int | None] = mapped_column(ForeignKey("trusted_contacts.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class TrustedHelper(Base):
    __tablename__ = "trusted_helpers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    helper_name: Mapped[str] = mapped_column(String(80))
    relationship: Mapped[str] = mapped_column(String(40))
    phone: Mapped[str] = mapped_column(String(20))
    can_view_pending_transaction: Mapped[bool] = mapped_column(Boolean, default=False)
    can_receive_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_balance: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_history: Mapped[bool] = mapped_column(Boolean, default=False)
    can_initiate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Helper Mode uses a separate relationship record rather than treating a helper
# as a contact.  The legacy TrustedHelper table is retained for backwards
# compatibility with early demo data; all new Helper Mode APIs use these tables.
class HelperRelationship(Base):
    __tablename__ = "helper_relationships"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    helper_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    helper_name: Mapped[str] = mapped_column(String(80))
    helper_phone: Mapped[str] = mapped_column(String(20), index=True)
    relationship: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    invited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (Index("ix_helper_relationship_owner_phone", "owner_user_id", "helper_phone", unique=True),)

class HelperActivity(Base):
    __tablename__ = "helper_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    helper_relationship_id: Mapped[int | None] = mapped_column(ForeignKey("helper_relationships.id"), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(16), default="owner")
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[str | None] = mapped_column(String(280), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class HelperAssistanceRequest(Base):
    __tablename__ = "helper_assistance_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    helper_relationship_id: Mapped[int] = mapped_column(ForeignKey("helper_relationships.id"), index=True)
    request_type: Mapped[str] = mapped_column(String(40), default="guidance")
    title: Mapped[str] = mapped_column(String(160))
    detail: Mapped[str | None] = mapped_column(String(280), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="waiting_owner_confirmation", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class TransactionDraft(Base):
    __tablename__ = "transaction_drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int | None] = mapped_column(ForeignKey("trusted_contacts.id"), nullable=True)
    recipient_name: Mapped[str] = mapped_column(String(80))
    recipient_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    fee: Mapped[float] = mapped_column(Numeric(14, 2), default=5)
    reference: Mapped[str | None] = mapped_column(String(140), nullable=True)
    state: Mapped[str] = mapped_column(String(30), default="draft_created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class HelperRequest(Base):
    __tablename__ = "helper_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    helper_id: Mapped[int] = mapped_column(ForeignKey("trusted_helpers.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    message: Mapped[str | None] = mapped_column(String(280), nullable=True)
    response: Mapped[str | None] = mapped_column(String(280), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
