from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone, timedelta
from typing import List
from app.database import get_db
from app.models.inventory import Sale, SaleStatus, Conversation, ConversationStatus, Message, MessageSource, Product
from app.schemas import DashboardStats, SalesByDay, TopProduct, SaleOut
from app.core.deps import require_any, require_supervisor
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])
sales_router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # AI sales today
    ai_sales_res = await db.execute(
        select(func.coalesce(func.sum(Sale.total), 0))
        .where(and_(Sale.closed_by_ai == True, Sale.created_at >= today_start, Sale.status != SaleStatus.CANCELLED))
    )
    ai_sales_today = float(ai_sales_res.scalar_one())

    # Total sales today
    total_sales_res = await db.execute(
        select(func.coalesce(func.sum(Sale.total), 0))
        .where(and_(Sale.created_at >= today_start, Sale.status != SaleStatus.CANCELLED))
    )
    total_sales_today = float(total_sales_res.scalar_one())

    # Clients served by AI today
    ai_clients_res = await db.execute(
        select(func.count(Sale.id))
        .where(and_(Sale.closed_by_ai == True, Sale.created_at >= today_start))
    )
    clients_served_ai = int(ai_clients_res.scalar_one())

    # Open conversations
    open_res = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.status.in_([ConversationStatus.OPEN, ConversationStatus.IN_PROGRESS]))
    )
    open_conversations = int(open_res.scalar_one())

    # Escalated today
    esc_res = await db.execute(
        select(func.count(Conversation.id))
        .where(and_(Conversation.status == ConversationStatus.ESCALATED, Conversation.updated_at >= today_start))
    )
    escalated_today = int(esc_res.scalar_one())

    # Conversion rate (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    total_convs = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.created_at >= week_ago)
    )
    total_sales = await db.execute(
        select(func.count(Sale.id)).where(and_(Sale.created_at >= week_ago, Sale.closed_by_ai == True))
    )
    tc = int(total_convs.scalar_one()) or 1
    ts = int(total_sales.scalar_one())
    conversion_rate = round((ts / tc) * 100, 1)

    return DashboardStats(
        ai_sales_today=ai_sales_today,
        total_sales_today=total_sales_today,
        clients_served_ai=clients_served_ai,
        conversion_rate=conversion_rate,
        avg_response_ms=1200.0,  # TODO: implement real measurement
        open_conversations=open_conversations,
        escalated_today=escalated_today,
    )


@router.get("/sales-by-day", response_model=List[SalesByDay])
async def sales_by_day(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    """Returns daily AI vs human sales for the last N days."""
    result = []
    for i in range(days - 1, -1, -1):
        day_start = (datetime.now(timezone.utc) - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day_start + timedelta(days=1)

        ai_res = await db.execute(
            select(func.coalesce(func.sum(Sale.total), 0))
            .where(and_(Sale.closed_by_ai == True, Sale.created_at >= day_start, Sale.created_at < day_end, Sale.status != SaleStatus.CANCELLED))
        )
        human_res = await db.execute(
            select(func.coalesce(func.sum(Sale.total), 0))
            .where(and_(Sale.closed_by_ai == False, Sale.created_at >= day_start, Sale.created_at < day_end, Sale.status != SaleStatus.CANCELLED))
        )
        label = "Hoy" if i == 0 else day_start.strftime("%a")
        result.append(SalesByDay(day=label, ai=float(ai_res.scalar_one()), human=float(human_res.scalar_one())))
    return result


@router.get("/top-products", response_model=List[TopProduct])
async def top_products(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(
            Sale.product_id,
            Product.name,
            func.sum(Sale.quantity).label("units"),
            func.sum(Sale.total).label("revenue"),
        )
        .join(Product, Sale.product_id == Product.id)
        .where(and_(Sale.created_at >= since, Sale.status != SaleStatus.CANCELLED))
        .group_by(Sale.product_id, Product.name)
        .order_by(func.sum(Sale.total).desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    max_rev = max((r.revenue for r in rows), default=1) or 1
    return [
        TopProduct(
            product_id=r.product_id,
            product_name=r.name,
            units_sold=int(r.units),
            revenue=float(r.revenue),
            pct=round((float(r.revenue) / max_rev) * 100, 1),
        )
        for r in rows
    ]


# ── Sales ─────────────────────────────────────────────────────────────────────
@sales_router.get("", response_model=List[SaleOut])
async def list_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    result = await db.execute(
        select(Sale).order_by(Sale.created_at.desc()).offset(skip).limit(limit)
    )
    return [SaleOut.model_validate(s) for s in result.scalars().all()]
