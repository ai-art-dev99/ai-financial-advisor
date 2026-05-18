from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional
import uuid

from database import get_db
from models import Portfolio, PerformanceSnapshot
from security import get_current_user_id

router = APIRouter()


class SnapshotResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    snapshot_date: datetime
    total_value: Optional[Decimal]
    daily_return: Optional[Decimal]
    total_return: Optional[Decimal]

    model_config = {"from_attributes": True}


class PerformanceSummary(BaseModel):
    portfolio_id: uuid.UUID
    latest_value: Optional[float]
    total_return_pct: Optional[float]
    daily_return_pct: Optional[float]
    best_day_pct: Optional[float]
    worst_day_pct: Optional[float]
    snapshots_count: int


@router.get("/{portfolio_id}/snapshots", response_model=list[SnapshotResponse])
async def get_snapshots(
    portfolio_id: uuid.UUID,
    days: int = Query(30, le=365),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == uuid.UUID(user_id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Portfolio not found")

    snaps = await db.execute(
        select(PerformanceSnapshot)
        .where(PerformanceSnapshot.portfolio_id == portfolio_id)
        .order_by(desc(PerformanceSnapshot.snapshot_date))
        .limit(days)
    )
    return snaps.scalars().all()


@router.get("/{portfolio_id}/summary", response_model=PerformanceSummary)
async def get_summary(
    portfolio_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == uuid.UUID(user_id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Portfolio not found")

    snaps_result = await db.execute(
        select(PerformanceSnapshot)
        .where(PerformanceSnapshot.portfolio_id == portfolio_id)
        .order_by(desc(PerformanceSnapshot.snapshot_date))
        .limit(365)
    )
    snaps = snaps_result.scalars().all()

    if not snaps:
        return PerformanceSummary(
            portfolio_id=portfolio_id, latest_value=None, total_return_pct=None,
            daily_return_pct=None, best_day_pct=None, worst_day_pct=None, snapshots_count=0
        )

    daily_returns = [float(s.daily_return) for s in snaps if s.daily_return is not None]

    return PerformanceSummary(
        portfolio_id=portfolio_id,
        latest_value=float(snaps[0].total_value) if snaps[0].total_value else None,
        total_return_pct=float(snaps[0].total_return) * 100 if snaps[0].total_return else None,
        daily_return_pct=float(snaps[0].daily_return) * 100 if snaps[0].daily_return else None,
        best_day_pct=max(daily_returns) * 100 if daily_returns else None,
        worst_day_pct=min(daily_returns) * 100 if daily_returns else None,
        snapshots_count=len(snaps),
    )
