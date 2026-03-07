from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.models.client import Client
from app.models.deal import Deal
from app.models.enums import DealStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def get_dashboard():
    """
    Простой дашборд для тестирования
    """
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


@router.get("/deals-by-status")
async def get_deals_by_status(
        db: AsyncSession = Depends(get_db)
):
    """
    Получить группировку сделок по статусам
    """
    # Получаем все статусы
    status_counts = {}

    for status in DealStatus:
        query = select(func.count()).select_from(Deal).where(Deal.status == status)
        result = await db.execute(query)
        count = result.scalar() or 0
        status_counts[status.value] = count

    # Получаем общее количество
    total_query = select(func.count()).select_from(Deal)
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    return {
        "total": total,
        "by_status": status_counts
    }


@router.get("/active-deals")
async def get_active_deals(
        limit: int = Query(20, ge=1, le=100, description="Количество сделок"),
        status_filter: Optional[DealStatus] = Query(None, description="Фильтр по статусу"),
        sort_by: str = Query("status", description="Сортировка: status, date, amount"),
        db: AsyncSession = Depends(get_db)
):
    """
    Активные сделки с возможностью фильтрации и сортировки по статусу

    - **status_filter**: показать только сделки с указанным статусом
    - **sort_by**:
        - "status" - сортировка по приоритету статуса (new → contact → negotiation → proposal → contract)
        - "date" - по дате создания
        - "amount" - по сумме
    """
    # Базовый запрос
    query = select(Deal)

    # Применяем фильтр по статусу
    if status_filter:
        query = query.where(Deal.status == status_filter)

    # Применяем сортировку
    if sort_by == "status":
        # Сортировка по приоритету статуса с помощью case
        status_order = case(
            (Deal.status == DealStatus.NEW, 1),
            (Deal.status == DealStatus.CONTACT, 2),
            (Deal.status == DealStatus.NEGOTIATION, 3),
            (Deal.status == DealStatus.PROPOSAL, 4),
            (Deal.status == DealStatus.CONTRACT, 5),
            (Deal.status == DealStatus.WON, 6),
            (Deal.status == DealStatus.LOST, 7),
            (Deal.status == DealStatus.POSTPONED, 8),
            else_=9
        )
        query = query.order_by(status_order, Deal.created_at.desc())
    elif sort_by == "date":
        query = query.order_by(Deal.created_at.desc())
    elif sort_by == "amount":
        query = query.order_by(Deal.amount.desc())
    else:
        query = query.order_by(Deal.created_at.desc())

    query = query.limit(limit)
    result = await db.execute(query)
    deals = result.scalars().all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "amount": float(d.amount) if d.amount else 0,
            "status": d.status.value if d.status else "unknown",
            "status_label": _get_status_label(d.status),
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "probability": d.probability,
            "client_id": d.client_id
        }
        for d in deals
    ]


@router.get("/deals-timeline")
async def get_deals_timeline(
        days: int = Query(30, ge=1, le=365),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику по сделкам за период (для графиков)
    Группировка по дням и статусам
    """
    from datetime import timedelta, date

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Получаем все сделки за период
    query = select(Deal).where(Deal.created_at >= start_date)
    result = await db.execute(query)
    deals = result.scalars().all()

    # Создаём структуру для результатов
    timeline = []
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.isoformat()
        day_deals = [d for d in deals if d.created_at and d.created_at.date() == current_date]

        # Считаем статистику по статусам для этого дня
        status_stats = {}
        for status in DealStatus:
            count = sum(1 for d in day_deals if d.status == status)
            if count > 0:
                status_stats[status.value] = count

        timeline.append({
            "date": date_str,
            "total": len(day_deals),
            "by_status": status_stats,
            "total_amount": sum(d.amount or 0 for d in day_deals)
        })

        current_date += timedelta(days=1)

    return timeline


def _get_status_label(status: DealStatus) -> str:
    """Возвращает человеко-читаемое название статуса"""
    labels = {
        DealStatus.NEW: "Новая",
        DealStatus.CONTACT: "Контакт",
        DealStatus.NEGOTIATION: "Переговоры",
        DealStatus.PROPOSAL: "Предложение",
        DealStatus.CONTRACT: "Договор",
        DealStatus.WON: "Выиграно",
        DealStatus.LOST: "Проиграно",
        DealStatus.POSTPONED: "Отложено"
    }
    return labels.get(status, str(status))