from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
import uuid

from database import get_db
from models import Portfolio
from security import get_current_user_id

router = APIRouter()


class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    currency: str = "USD"
    target_return: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str]
    currency: str
    target_return: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[PortfolioResponse])
async def list_portfolios(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == uuid.UUID(user_id), Portfolio.is_active == True)
    )
    return result.scalars().all()


@router.post("/", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(
    payload: PortfolioCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    portfolio = Portfolio(user_id=uuid.UUID(user_id), **payload.model_dump())
    db.add(portfolio)
    await db.flush()
    return portfolio


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == uuid.UUID(user_id))
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")
    return portfolio


@router.delete("/{portfolio_id}", status_code=204)
async def delete_portfolio(
    portfolio_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == uuid.UUID(user_id))
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")
    portfolio.is_active = False
