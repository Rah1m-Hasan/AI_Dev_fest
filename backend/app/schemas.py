from datetime import date as Date, datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator

class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=120)
class BudgetIn(BaseModel):
    total_limit: Decimal = Field(gt=0, le=10_000_000, decimal_places=2)
    categories: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("categories")
    @classmethod
    def valid_categories(cls, value):
        if len(value) > 20 or any(not key.strip() or len(key) > 40 or amount < 0 for key, amount in value.items()):
            raise ValueError("categories must have valid names and non-negative limits")
        return {key.strip(): amount for key, amount in value.items()}

    @model_validator(mode="after")
    def category_total_fits_budget(self):
        if sum(self.categories.values(), Decimal("0")) > self.total_limit:
            raise ValueError("category limits cannot exceed the total budget")
        return self
class PlanIn(BaseModel):
    essentials: Decimal = Field(ge=0, le=10_000_000, decimal_places=2)
    flexible: Decimal = Field(ge=0, le=10_000_000, decimal_places=2)
    savings: Decimal = Field(ge=0, le=10_000_000, decimal_places=2)
    safety_buffer: Decimal = Field(ge=0, le=10_000_000, decimal_places=2)
    categories: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("categories")
    @classmethod
    def valid_categories(cls, value):
        if len(value) > 20 or any(not key.strip() or len(key) > 40 or amount < 0 for key, amount in value.items()):
            raise ValueError("categories must have valid names and non-negative limits")
        return {key.strip(): amount for key, amount in value.items()}

    @model_validator(mode="after")
    def category_total_fits_spending(self):
        if sum(self.categories.values(), Decimal("0")) > self.essentials + self.flexible:
            raise ValueError("category limits cannot exceed essential and flexible spending")
        return self
class GoalIn(BaseModel):
    goal_name: str = Field(min_length=2,max_length=100)
    target_amount: Decimal = Field(gt=0,le=10_000_000, decimal_places=2)
    deadline: Date
    optional_current_savings: Decimal = Field(default=0,ge=0, decimal_places=2)
    category: str = Field(default="Other", min_length=2, max_length=40)
    saving_preference: str = Field(default="flexible", pattern="^(weekly|monthly|flexible)$")
    note: str | None = Field(default=None, max_length=280)
    planned_monthly_amount: Decimal | None = Field(default=None, gt=0, le=10_000_000, decimal_places=2)
    @field_validator("deadline")
    @classmethod
    def future(cls,v):
        if v <= Date.today(): raise ValueError("deadline must be in the future")
        return v
    @model_validator(mode="after")
    def savings_cannot_exceed_target(self):
        if self.optional_current_savings > self.target_amount:
            raise ValueError("current savings cannot exceed the goal target")
        return self
class GoalUpdateIn(BaseModel):
    goal_name: str | None = Field(default=None, min_length=2, max_length=100)
    target_amount: Decimal | None = Field(default=None, gt=0, le=10_000_000, decimal_places=2)
    deadline: Date | None = None
    category: str | None = Field(default=None, min_length=2, max_length=40)
    saving_preference: str | None = Field(default=None, pattern="^(weekly|monthly|flexible)$")
    note: str | None = Field(default=None, max_length=280)
    planned_monthly_amount: Decimal | None = Field(default=None, gt=0, le=10_000_000, decimal_places=2)
class ContributionIn(BaseModel):
    amount: Decimal = Field(gt=0, le=10_000_000, decimal_places=2)
class GoalPreviewIn(BaseModel):
    target_amount: Decimal | None = Field(default=None, gt=0, le=10_000_000, decimal_places=2)
    deadline: Date | None = None
    planned_monthly_amount: Decimal | None = Field(default=None, gt=0, le=10_000_000, decimal_places=2)
class ChatIn(BaseModel): question: str = Field(min_length=2,max_length=500); language: str = Field(default="en",pattern="^(en|bn)$")
class CategoryCorrection(BaseModel): category: str = Field(min_length=2,max_length=40)
class ScenarioIn(BaseModel):
    kind: str = Field(pattern="^(reduce_spending|save_more|purchase|unexpected_expense|income_delay)$")
    amount: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    days: int = Field(default=30, ge=7, le=90)
    category: str | None = Field(default=None, max_length=40)
    date: Date | None = None
    description: str | None = Field(default=None, max_length=100)
class IntentIn(BaseModel): question: str = Field(min_length=2, max_length=500); language: str = Field(default="en", pattern="^(en|bn)$")
class SendMoneyIn(BaseModel): pin: str = Field(min_length=4, max_length=6)
class TrustedContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone_number: str = Field(min_length=7, max_length=20)
    relationship: str = Field(min_length=2, max_length=40)
    nickname: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=280)

class TrustedContactUpdateIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone_number: str = Field(min_length=7, max_length=20)
    relationship: str = Field(min_length=2, max_length=40)
    nickname: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=280)

class PaymentRequestIn(BaseModel):
    amount: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    note: str | None = Field(default=None, max_length=140)

class TransactionDraftIn(BaseModel):
    recipient_id: int | None = None
    recipient_name: str = Field(min_length=1, max_length=80)
    recipient_phone: str | None = Field(default=None, max_length=20)
    amount: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    reference: str | None = Field(default=None, max_length=140)
    recognition_confirmed: bool = False
class TrustedHelperIn(BaseModel): helper_name: str = Field(min_length=2, max_length=80); relationship: str = Field(min_length=2, max_length=40); phone: str = Field(min_length=7, max_length=20); can_view_pending_transaction: bool = Field(default=False); can_receive_alerts: bool = Field(default=True); can_view_balance: bool = Field(default=False); can_view_history: bool = Field(default=False); can_initiate: bool = Field(default=False)
class HelperRequestIn(BaseModel): helper_id: int; message: str | None = Field(default=None, max_length=280)
class HelperModeCreateIn(BaseModel):
    helper_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    relationship: str = Field(min_length=2, max_length=40)
    permissions: list[str] = Field(min_length=1, max_length=8)
class HelperPermissionsIn(BaseModel):
    permissions: list[str] = Field(min_length=1, max_length=8)
class HelperRequestReviewIn(BaseModel):
    decision: str = Field(pattern="^(approved|dismissed)$")
class HelperAssistancePrepareIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    detail: str | None = Field(default=None, max_length=280)
class ExplainMetricIn(BaseModel):
    """Presentation context only; it never authorizes or recalculates financial data."""
    metric_id: str = Field(pattern="^(safe_to_spend|monthly_spending|savings_rate|money_runway|financial_health_score|financial_health_factor|savings_goal_progress|spending_category_change|remaining_budget)$")
    title: str = Field(min_length=1, max_length=100)
    value: float | int | str
    unit: str | None = Field(default=None, max_length=20)
    source: str = Field(min_length=1, max_length=60)
    language: str | None = Field(default=None, pattern="^(en|bn)$")
    context: dict[str, str | float | int | bool | None] = Field(default_factory=dict, max_length=16)
    @field_validator("value")
    @classmethod
    def short_display_value(cls, value):
        if isinstance(value, str) and len(value) > 80:
            raise ValueError("value must be at most 80 characters")
        return value
    @field_validator("context")
    @classmethod
    def no_sensitive_context(cls, value):
        blocked = ("pin", "password", "otp", "token", "jwt", "secret")
        if any(any(term in key.lower() for term in blocked) for key in value):
            raise ValueError("metric context cannot include credentials or secrets")
        return value
class AssistantMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = Field(default=None, max_length=36)
    explain_metric: ExplainMetricIn | None = None
class AssistantAuthorizeIn(BaseModel):
    pin: str = Field(min_length=4, max_length=6, pattern=r"^\d+$")


# Assistant savings contracts deliberately keep financial values numeric.  The
# browser owns localisation and display units; these models protect the action
# boundary from a model or formatter turning values into presentation strings.
class SavingsGoalEntities(BaseModel):
    goal_name: str = Field(min_length=1, max_length=100)
    target_amount: Decimal = Field(gt=0, le=10_000_000, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, le=10_000_000, decimal_places=2)
    duration_months: int | None = Field(default=None, ge=1, le=120)
    deadline: Date | None = None

    @model_validator(mode="after")
    def valid_goal_timing_and_balance(self):
        if self.duration_months is None and self.deadline is None:
            raise ValueError("a duration or deadline is required")
        if self.current_amount > self.target_amount:
            raise ValueError("current savings cannot exceed the target amount")
        return self


class SavingsPlanResult(BaseModel):
    goal_name: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    duration_months: int = Field(ge=1)
    deadline: Date
    required_monthly_contribution: Decimal
    affordable_monthly_contribution: Decimal | None = None
    feasible: bool | None = None
    feasibility_status: str
    shortfall: Decimal
    alternative_duration_months: int | None = None


class AssistantDisplayField(BaseModel):
    key: str
    label: str
    value: str | int | float | Decimal | bool
    value_type: str = Field(pattern="^(currency|months|days|percentage|date|number|score|text)$")

# --- Learn schemas ---
class QuizOptionOut(BaseModel):
    key: str
    text: str
class QuizOut(BaseModel):
    question: str
    options: list[QuizOptionOut]
    correct_key: str
class LessonCardOut(BaseModel):
    id: int
    title: str
    summary: str
    category: str
    difficulty: str
    duration_minutes: int
    trigger_type: str | None = None
    trigger_reason: str | None = None
class LessonDetailOut(BaseModel):
    id: int
    title: str
    summary: str
    content: str
    content_bn: str | None = None
    category: str
    difficulty: str
    duration_minutes: int
    personalized_section: str | None = None
    personalized_section_bn: str | None = None
    quiz: QuizOut | None = None
    trigger_type: str | None = None
    trigger_reason: str | None = None
    completed: bool = False
    started: bool = False
class LessonProgressOut(BaseModel):
    lesson_id: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    quiz_score: int | None = None
class LessonProgressSummaryOut(BaseModel):
    category: str
    completed: int
    total: int
class LearningRecommendationsOut(BaseModel):
    featured: LessonCardOut | None = None
    for_you: list[LessonCardOut]
    tabs: list[str]
    progress: list[LessonProgressSummaryOut]
class CompleteLessonIn(BaseModel):
    quiz_answer: str | None = None
class LessonCompleteOut(BaseModel):
    completed: bool
    quiz_score: int | None = None

# --- Offers schemas ---
class OfferCardOut(BaseModel):
    id: int
    title: str
    terms: str
    terms_bn: str | None = None
    category: str
    min_spend: float | None = None
    discount_percent: float | None = None
    discount_fixed: float | None = None
    max_discount: float | None = None
    typical_purchase: float | None = None
    typical_merchant: str | None = None
    potential_saving: float | None = None
    expiry_date: date | None = None
    eligibility_notes: str | None = None
    fit_status: str | None = None
    is_saved: bool = False
    learning_lesson_id: int | None = None
class OfferDetailOut(BaseModel):
    id: int
    title: str
    terms: str
    terms_bn: str | None = None
    category: str
    min_spend: float | None = None
    discount_percent: float | None = None
    discount_fixed: float | None = None
    max_discount: float | None = None
    typical_purchase: float | None = None
    typical_merchant: str | None = None
    potential_saving: float | None = None
    expiry_date: date | None = None
    eligibility_notes: str | None = None
    fit_status: str | None = None
    is_saved: bool = False
    learning_lesson_id: int | None = None
    why_relevant: str | None = None
class OffersResponseOut(BaseModel):
    offers: list[OfferCardOut]
    preferences: dict
class OfferPreferencesIn(BaseModel):
    enabled: bool
class OfferPreferencesOut(BaseModel):
    personalized_offers_enabled: bool
