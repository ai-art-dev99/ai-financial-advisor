from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from database import get_db
from models import User, RiskProfile
from schemas import UserResponse, RiskProfileCreate, RiskProfileResponse
from security import get_current_user_id

router = APIRouter()


def _calc_risk_category(score: int) -> str:
    if score <= 3:
        return "conservative"
    elif score <= 7:
        return "moderate"
    return "aggressive"


@router.get("/me", response_model=UserResponse)
async def get_me(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/me/risk-profile", response_model=RiskProfileResponse)
async def upsert_risk_profile(
    payload: RiskProfileCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id)
    result = await db.execute(select(RiskProfile).where(RiskProfile.user_id == uid))
    profile = result.scalar_one_or_none()

    category = _calc_risk_category(payload.risk_score)

    if profile:
        profile.risk_score = payload.risk_score
        profile.risk_category = category
        profile.investment_horizon = payload.investment_horizon
        profile.monthly_income = payload.monthly_income
        profile.investable_assets = payload.investable_assets
        profile.questionnaire_data = payload.questionnaire_data
        profile.completed_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
    else:
        profile = RiskProfile(
            user_id=uid,
            risk_score=payload.risk_score,
            risk_category=category,
            investment_horizon=payload.investment_horizon,
            monthly_income=payload.monthly_income,
            investable_assets=payload.investable_assets,
            questionnaire_data=payload.questionnaire_data,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(profile)

    return profile


@router.get("/me/risk-profile", response_model=RiskProfileResponse)
async def get_risk_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RiskProfile).where(RiskProfile.user_id == uuid.UUID(user_id)))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Risk profile not completed yet")
    return profile
