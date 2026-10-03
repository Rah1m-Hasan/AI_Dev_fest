from datetime import date
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
class GoalIn(BaseModel):
    goal_name: str = Field(min_length=2,max_length=100)
    target_amount: Decimal = Field(gt=0,le=10_000_000, decimal_places=2)
    deadline: date
    optional_current_savings: Decimal = Field(default=0,ge=0, decimal_places=2)
    @field_validator("deadline")
    @classmethod
    def future(cls,v):
        if v <= date.today(): raise ValueError("deadline must be in the future")
        return v
    @model_validator(mode="after")
    def savings_cannot_exceed_target(self):
        if self.optional_current_savings > self.target_amount:
            raise ValueError("current savings cannot exceed the goal target")
        return self
class ChatIn(BaseModel): question: str = Field(min_length=2,max_length=500); language: str = Field(default="en",pattern="^(en|bn)$")
class CategoryCorrection(BaseModel): category: str = Field(min_length=2,max_length=40)
class ScenarioIn(BaseModel):
    kind: str = Field(pattern="^(reduce_spending|save_more|purchase|income_delay)$")
    amount: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    days: int = Field(default=7, ge=1, le=90)
class IntentIn(BaseModel): question: str = Field(min_length=2, max_length=500); language: str = Field(default="en", pattern="^(en|bn)$")
class SendMoneyIn(BaseModel): draft_id: int; pin: str = Field(min_length=4, max_length=6)
class TrustedContactIn(BaseModel): name: str = Field(min_length=2, max_length=80); phone_number: str = Field(min_length=7, max_length=20); relationship: str = Field(min_length=2, max_length=40); nickname: str | None = Field(default=None, max_length=40); is_trusted: bool = Field(default=True)
class TrustedHelperIn(BaseModel): helper_name: str = Field(min_length=2, max_length=80); relationship: str = Field(min_length=2, max_length=40); phone: str = Field(min_length=7, max_length=20); can_view_pending_transaction: bool = Field(default=False); can_receive_alerts: bool = Field(default=True); can_view_balance: bool = Field(default=False); can_view_history: bool = Field(default=False); can_initiate: bool = Field(default=False)
class HelperRequestIn(BaseModel): helper_id: int; message: str | None = Field(default=None, max_length=280)
class GuidedFlowIn(BaseModel): step: str = Field(min_length=1); value: str | None = Field(default=None)
