from datetime import date
from pydantic import BaseModel, Field, field_validator
class LoginIn(BaseModel): email: str
class BudgetIn(BaseModel):
    total_limit: float = Field(gt=0, le=10_000_000)
    categories: dict[str,float] = Field(default_factory=dict)
class GoalIn(BaseModel):
    goal_name: str = Field(min_length=2,max_length=100)
    target_amount: float = Field(gt=0,le=10_000_000)
    deadline: date
    optional_current_savings: float = Field(default=0,ge=0)
    @field_validator("deadline")
    @classmethod
    def future(cls,v):
        if v <= date.today(): raise ValueError("deadline must be in the future")
        return v
class ChatIn(BaseModel): question: str = Field(min_length=2,max_length=500); language: str = Field(default="en",pattern="^(en|bn)$")
class CategoryCorrection(BaseModel): category: str = Field(min_length=2,max_length=40)
