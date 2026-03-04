from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.client import Client
from app.models.deal import Deal
from app.models.enums import DealStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Простой дашборд для тестирования
    """
    # Просто возвращаем тестовые данные
    return {
        "message": "Дашборд работает!",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "stats": {
                "clients": {"total": 0},
                "deals": {"total": 0}
            },
            "recent_clients": [],
            "active_deals": []
        }
    }


@router.get("/stats")
async def get_main_stats(db: AsyncSession = Depends(get_db)):
    """Простая статистика"""
    # Считаем клиентов
    result = await db.execute(select(func.count()).select_from(Client))
    clients_count = result.scalar() or 0

    # Считаем сделки
    result = await db.execute(select(func.count()).select_from(Deal))
    deals_count = result.scalar() or 0

    return {
        "clients": {"total": clients_count},
        "deals": {"total": deals_count}
    }


@router.get("/recent-clients")
async def get_recent_clients(
        limit: int = 5,
        db: AsyncSession = Depends(get_db)
):
    """Последние клиенты"""
    query = select(Client).order_by(Client.created_at.desc()).limit(limit)
    result = await db.execute(query)
    clients = result.scalars().all()

    return [
        {
            "id": c.id,
            "full_name": f"{c.last_name or ''} {c.first_name or ''}".strip() or "Без имени",
            "email": c.email,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in clients
    ]


@router.get("/active-deals")
async def get_active_deals(
        limit: int = 5,
        db: AsyncSession = Depends(get_db)
):
    """Активные сделки"""
    query = select(Deal).order_by(Deal.created_at.desc()).limit(limit)
    result = await db.execute(query)
    deals = result.scalars().all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "amount": float(d.amount) if d.amount else 0,
            "status": d.status.value if d.status else "unknown"
        }
        for d in deals
    ]