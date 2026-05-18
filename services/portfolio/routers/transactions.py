from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid

from database import get_db
from models import Portfolio, Transaction, Holding
from security import get_current_user_id

router = APIRouter()


class TransactionCreate(BaseModel):
    portfolio_id: uuid.UUID
    symbol: str
    tx_type: str
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    fee: Decimal = Decimal("0")
    notes: Optional[str] = None
    executed_at: Optional[datetime] = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    symbol: str
    tx_type: str
    quantity: Optional[Decimal]
    price: Optional[Decimal]
    total_amount: Optional[Decimal]
    fee: Decimal
    notes: Optional[str]
    executed_at: datetime

    model_config = {"from_attributes": True}


@router.get("/{portfolio_id}/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    portfolio_id: uuid.UUID,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == uuid.UUID(user_id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Portfolio not found")

    txns = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(desc(Transaction.executed_at))
        .limit(limit)
        .offset(offset)
    )
    return txns.scalars().all()


@router.post("/{portfolio_id}/transactions", response_model=TransactionResponse, status_code=201)
async def record_transaction(
    portfolio_id: uuid.UUID,
    payload: TransactionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == uuid.UUID(user_id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Portfolio not found")

    total = None
    if payload.quantity and payload.price:
        total = payload.quantity * payload.price

    txn = Transaction(
        portfolio_id=portfolio_id,
        symbol=payload.symbol.upper(),
        tx_type=payload.tx_type,
        quantity=payload.quantity,
        price=payload.price,
        total_amount=total,
        fee=payload.fee,
        notes=payload.notes,
        executed_at=payload.executed_at or datetime.utcnow(),
    )
    db.add(txn)

    # Update holding quantity
    if payload.tx_type in ("buy", "sell") and payload.quantity:
        h_result = await db.execute(
            select(Holding).where(Holding.portfolio_id == portfolio_id, Holding.symbol == payload.symbol.upper())
        )
        holding = h_result.scalar_one_or_none()
        if holding:
            if payload.tx_type == "buy":
                if payload.price:
                    total_qty = float(holding.quantity) + float(payload.quantity)
                    holding.avg_cost = Decimal(str(
                        (float(holding.quantity) * float(holding.avg_cost or 0) +
                         float(payload.quantity) * float(payload.price)) / total_qty
                    ))
                holding.quantity += payload.quantity
            else:
                holding.quantity -= payload.quantity
                if holding.quantity < 0:
                    raise HTTPException(400, f"Insufficient quantity for {payload.symbol}")

    await db.flush()
    return txn
