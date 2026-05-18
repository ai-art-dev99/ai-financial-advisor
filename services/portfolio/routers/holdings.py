from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
import uuid

from database import get_db
from models import Portfolio, Holding
from security import get_current_user_id
from risk_engine import RiskEngine

router = APIRouter()


class HoldingCreate(BaseModel):
    portfolio_id: uuid.UUID
    symbol: str
    asset_type: Optional[str] = "stock"
    quantity: Decimal
    avg_cost: Optional[Decimal] = None
    target_weight: Optional[Decimal] = None


class HoldingResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    symbol: str
    asset_type: Optional[str]
    quantity: Decimal
    avg_cost: Optional[Decimal]
    target_weight: Optional[Decimal]

    model_config = {"from_attributes": True}


class PortfolioAnalysis(BaseModel):
    portfolio_id: uuid.UUID
    total_cost_basis: float
    holdings_count: int
    asset_allocation: dict
    risk_metrics: dict
    rebalancing_needed: bool
    drift_threshold_pct: float = 5.0


async def _verify_portfolio_owner(portfolio_id: uuid.UUID, user_id: str, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == uuid.UUID(user_id))
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")
    return portfolio


@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
async def get_holdings(
    portfolio_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _verify_portfolio_owner(portfolio_id, user_id, db)
    result = await db.execute(select(Holding).where(Holding.portfolio_id == portfolio_id))
    return result.scalars().all()


@router.post("/{portfolio_id}/holdings", response_model=HoldingResponse, status_code=201)
async def add_holding(
    portfolio_id: uuid.UUID,
    payload: HoldingCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _verify_portfolio_owner(portfolio_id, user_id, db)

    # Upsert: if symbol already exists, update
    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id, Holding.symbol == payload.symbol.upper())
    )
    holding = result.scalar_one_or_none()

    if holding:
        # Weighted avg cost calculation
        if payload.avg_cost and holding.avg_cost:
            total_qty = float(holding.quantity) + float(payload.quantity)
            holding.avg_cost = Decimal(str(
                (float(holding.quantity) * float(holding.avg_cost) +
                 float(payload.quantity) * float(payload.avg_cost)) / total_qty
            ))
        holding.quantity += payload.quantity
        holding.target_weight = payload.target_weight or holding.target_weight
    else:
        holding = Holding(
            portfolio_id=portfolio_id,
            symbol=payload.symbol.upper(),
            asset_type=payload.asset_type,
            quantity=payload.quantity,
            avg_cost=payload.avg_cost,
            target_weight=payload.target_weight,
        )
        db.add(holding)

    await db.flush()
    return holding


@router.get("/{portfolio_id}/analysis", response_model=PortfolioAnalysis)
async def analyze_portfolio(
    portfolio_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await _verify_portfolio_owner(portfolio_id, user_id, db)
    result = await db.execute(select(Holding).where(Holding.portfolio_id == portfolio_id))
    holdings = result.scalars().all()

    engine = RiskEngine(holdings)
    return {
        "portfolio_id": portfolio_id,
        "total_cost_basis": engine.total_cost_basis(),
        "holdings_count": len(holdings),
        "asset_allocation": engine.asset_allocation(),
        "risk_metrics": engine.risk_metrics(),
        "rebalancing_needed": engine.needs_rebalancing(),
        "drift_threshold_pct": 5.0,
    }
