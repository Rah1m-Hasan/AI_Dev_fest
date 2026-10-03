from datetime import datetime, date
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, Date, ForeignKey, Text, JSON, Index
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
    id: Mapped[int] = mapped_column(primary_key=True); title: Mapped[str] = mapped_column(String(140)); content: Mapped[str] = mapped_column(Text); trigger_key: Mapped[str] = mapped_column(String(60))
class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); lesson_id: Mapped[int] = mapped_column(ForeignKey("financial_lessons.id")); completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(primary_key=True); merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"), nullable=True); title: Mapped[str] = mapped_column(String(140)); terms: Mapped[str] = mapped_column(Text); active: Mapped[bool] = mapped_column(Boolean, default=True)
class UserOfferPreference(Base):
    __tablename__ = "user_offer_preferences"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True); personalized_offers_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True); conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversations.id"), index=True); role: Mapped[str] = mapped_column(String(12)); content: Mapped[str] = mapped_column(Text); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class UserFeedback(Base):
    __tablename__ = "user_feedback"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); feedback_type: Mapped[str] = mapped_column(String(40)); payload: Mapped[dict] = mapped_column(JSON, default=dict); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TrustedContact(Base):
    __tablename__ = "trusted_contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    phone_number: Mapped[str] = mapped_column(String(20))
    relationship: Mapped[str] = mapped_column(String(40), default="Known")
    nickname: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
