from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
import uuid


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RiskProfileCreate(BaseModel):
    risk_score: int
    investment_horizon: int           # months
    monthly_income: float
    investable_assets: float
    questionnaire_data: dict = {}

    @field_validator("risk_score")
    @classmethod
    def validate_risk_score(cls, v):
        if not 1 <= v <= 10:
            raise ValueError("Risk score must be between 1 and 10")
        return v


class RiskProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    risk_score: Optional[int]
    risk_category: Optional[str]
    investment_horizon: Optional[int]
    monthly_income: Optional[float]
    investable_assets: Optional[float]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
