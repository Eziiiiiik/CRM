import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Optional
import traceback

from app.core.database import get_db
from app.models.client import Client
from app.models.deal import Deal
from app.models.interaction import Interaction, InteractionType
from app.models.enums import DealStatus

# Настраиваем логгер
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def get_full_dashboard(
        period: str = Query("month", pattern="^(day|week|month|year)$"),
        db: AsyncSession = Depends(get_db)
):
    """
    Полный дашборд со всей статистикой
    """
    try:
        logger.info("=" * 50)
        logger.info("Начинаем сбор данных для дашборда")
        logger.info(f"Период: {period}")

        # Определяем период для фильтрации
        date_filter = get_date_filter(period)
        logger.info(f"Date filter: {date_filter}")

        # Проверяем подключение к БД
        try:
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            logger.info(f"Подключение к БД работает: {result.scalar()}")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка подключения к БД: {str(e)}")

        # Собираем все данные с обработкой ошибок
        kpi_data = await safe_execute(get_kpi_metrics, db=db, date_filter=date_filter, default={})
        recent_activity = await safe_execute(get_recent_activity, db=db, limit=10, default=[])
        upcoming_events = await safe_execute(get_upcoming_events, db=db, default=[])
        top_clients = await safe_execute(get_top_clients, db=db, limit=5, default=[])
        alerts = await safe_execute(get_alerts, db=db, default=[])

        logger.info("Дашборд успешно собран")
        logger.info("=" * 50)

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "period": period,
            "data": {
                "kpi": kpi_data,
                "recent_activity": recent_activity,
                "upcoming_events": upcoming_events,
                "top_clients": top_clients,
                "alerts": alerts
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@router.get("/kpi")
async def get_kpi_metrics(
        db: AsyncSession = Depends(get_db),
        date_filter: Optional[datetime] = None
):
    """
    Ключевые показатели эффективности
    """
    try:
        if date_filter is None:
            date_filter = datetime.now() - timedelta(days=30)

        # Общее количество клиентов
        total_clients = await db.scalar(select(func.count()).select_from(Client)) or 0

        # Новые клиенты за период
        new_clients = await db.scalar(
            select(func.count()).select_from(Client).where(Client.created_at >= date_filter)
        ) or 0

        # Все сделки
        total_deals = await db.scalar(select(func.count()).select_from(Deal)) or 0

        # Активные сделки
        active_deals = 0
        try:
            active_statuses = [s.value for s in DealStatus.active_statuses()]
            active_deals = await db.scalar(
                select(func.count()).select_from(Deal).where(Deal.status.in_(active_statuses))
            ) or 0
        except Exception as e:
            logger.error(f"Ошибка при подсчете активных сделок: {e}")

        # Сумма всех сделок
        total_amount = await db.scalar(select(func.sum(Deal.amount))) or 0

        # Выигранные сделки за период
        won_deals = await db.scalar(
            select(func.count()).select_from(Deal).where(
                and_(
                    Deal.status == DealStatus.WON,
                    Deal.created_at >= date_filter
                )
            )
        ) or 0

        # Конверсия
        conversion_rate = 0
        if total_deals > 0:
            conversion_rate = round((won_deals / total_deals) * 100, 1)

        # Средняя сделка
        avg_deal = 0
        if total_deals > 0:
            avg_deal = round(total_amount / total_deals, 2)

        # Взаимодействия за период
        interactions = await db.scalar(
            select(func.count()).select_from(Interaction).where(Interaction.created_at >= date_filter)
        ) or 0

        return {
            "clients": {
                "total": total_clients,
                "new": new_clients,
                "growth": calculate_growth(total_clients, new_clients)
            },
            "deals": {
                "total": total_deals,
                "active": active_deals,
                "won": won_deals,
                "conversion_rate": conversion_rate
            },
            "financial": {
                "total_amount": float(total_amount),
                "average_deal": float(avg_deal),
                "currency": "RUB"
            },
            "activity": {
                "interactions": interactions,
                "avg_per_client": round(interactions / (total_clients or 1), 1)
            }
        }
    except Exception as e:
        logger.error(f"Ошибка в get_kpi_metrics: {e}")
        logger.error(traceback.format_exc())
        return {
            "clients": {"total": 0, "new": 0, "growth": 0},
            "deals": {"total": 0, "active": 0, "won": 0, "conversion_rate": 0},
            "financial": {"total_amount": 0, "average_deal": 0, "currency": "RUB"},
            "activity": {"interactions": 0, "avg_per_client": 0}
        }


@router.get("/recent-activity")
async def get_recent_activity(
        limit: int = 10,
        db: AsyncSession = Depends(get_db)
):
    """
    Последние действия в системе
    """
    try:
        activity = []

        # Получаем последних клиентов
        try:
            clients_query = select(Client).order_by(Client.created_at.desc()).limit(limit)
            clients_result = await db.execute(clients_query)
            clients = clients_result.scalars().all()

            for client in clients:
                activity.append({
                    "id": f"client_{client.id}",
                    "type": "new_client",
                    "title": f"Новый клиент: {getattr(client, 'full_name', 'Неизвестно')}",
                    "description": f"Email: {getattr(client, 'email', 'Нет email')}",
                    "icon": "👤",
                    "color": "green",
                    "timestamp": client.created_at.isoformat() if client.created_at else None,
                    "link": f"/api/v1/clients/{client.id}"
                })
        except Exception as e:
            logger.error(f"Ошибка при получении клиентов: {e}")

        # Последние сделки
        try:
            deals_query = select(Deal).options(
                selectinload(Deal.client)
            ).order_by(Deal.created_at.desc()).limit(limit)
            deals_result = await db.execute(deals_query)
            deals = deals_result.scalars().all()

            for deal in deals:
                client_name = "Неизвестно"
                if deal.client:
                    client_name = getattr(deal.client, 'full_name', 'Неизвестно')

                activity.append({
                    "id": f"deal_{deal.id}",
                    "type": "new_deal",
                    "title": f"Новая сделка: {getattr(deal, 'name', 'Без названия')}",
                    "description": f"Сумма: {getattr(deal, 'amount', 0)} {getattr(deal, 'currency', 'RUB')}, Клиент: {client_name}",
                    "icon": "💼",
                    "color": "blue",
                    "timestamp": deal.created_at.isoformat() if deal.created_at else None,
                    "link": f"/api/v1/deals/{deal.id}"
                })
        except Exception as e:
            logger.error(f"Ошибка при получении сделок: {e}")

        # Последние взаимодействия
        try:
            interactions_query = select(Interaction).options(
                selectinload(Interaction.client)
            ).order_by(Interaction.created_at.desc()).limit(limit)
            interactions_result = await db.execute(interactions_query)
            interactions = interactions_result.scalars().all()

            for interaction in interactions:
                client_name = "Неизвестно"
                if interaction.client:
                    client_name = getattr(interaction.client, 'full_name', 'Неизвестно')

                activity.append({
                    "id": f"interaction_{interaction.id}",
                    "type": "interaction",
                    "title": f"Взаимодействие: {getattr(interaction, 'title', 'Без названия')}",
                    "description": f"Тип: {getattr(interaction, 'type', 'unknown')}, Клиент: {client_name}",
                    "icon": get_interaction_icon(getattr(interaction, 'type', None)),
                    "color": "purple",
                    "timestamp": interaction.created_at.isoformat() if interaction.created_at else None,
                    "link": f"/api/v1/interactions/{interaction.id}"
                })
        except Exception as e:
            logger.error(f"Ошибка при получении взаимодействий: {e}")

        # Сортируем по времени (новые сверху)
        activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)

        return activity[:limit]

    except Exception as e:
        logger.error(f"Ошибка в get_recent_activity: {e}")
        logger.error(traceback.format_exc())
        return []


@router.get("/upcoming")
async def get_upcoming_events(
        db: AsyncSession = Depends(get_db)
):
    """
    Предстоящие события (встречи, дни рождения, дедлайны)
    """
    try:
        now = datetime.now()
        week_later = now + timedelta(days=7)

        events = []

        # Предстоящие встречи
        try:
            meetings_query = select(Interaction).where(
                and_(
                    Interaction.type == InteractionType.MEETING,
                    Interaction.status == "planned",
                    Interaction.scheduled_at >= now,
                    Interaction.scheduled_at <= week_later
                )
            ).options(selectinload(Interaction.client)).order_by(Interaction.scheduled_at)

            meetings_result = await db.execute(meetings_query)
            meetings = meetings_result.scalars().all()

            for meeting in meetings:
                client_name = "клиентом"
                if meeting.client:
                    client_name = getattr(meeting.client, 'full_name', 'клиентом')

                events.append({
                    "id": f"meeting_{meeting.id}",
                    "type": "meeting",
                    "title": getattr(meeting, 'title', 'Встреча'),
                    "description": f"Встреча с {client_name}",
                    "datetime": meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
                    "priority": "high"
                })
        except Exception as e:
            logger.error(f"Ошибка при получении встреч: {e}")

        # Дни рождения на этой неделе
        try:
            clients_query = select(Client).where(
                Client.birth_date.is_not(None)
            )
            clients_result = await db.execute(clients_query)
            clients = clients_result.scalars().all()

            for client in clients:
                if client.birth_date:
                    try:
                        birthday_this_year = client.birth_date.replace(year=now.year)
                        if birthday_this_year < now:
                            birthday_this_year = birthday_this_year.replace(year=now.year + 1)

                        days_until = (birthday_this_year - now).days
                        if 0 <= days_until <= 7:
                            events.append({
                                "id": f"birthday_{client.id}",
                                "type": "birthday",
                                "title": f"День рождения: {getattr(client, 'full_name', 'Клиент')}",
                                "description": f"Исполняется {calculate_age(client.birth_date)} лет",
                                "datetime": birthday_this_year.isoformat(),
                                "days_until": days_until,
                                "priority": "medium"
                            })
                    except Exception as e:
                        logger.error(f"Ошибка при обработке дня рождения клиента {client.id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка при получении дней рождения: {e}")

        # Дедлайны по сделкам
        try:
            deals_query = select(Deal).where(
                and_(
                    Deal.expected_close_date >= now,
                    Deal.expected_close_date <= week_later,
                    Deal.status.in_(DealStatus.active_statuses())
                )
            ).options(selectinload(Deal.client)).order_by(Deal.expected_close_date)

            deals_result = await db.execute(deals_query)
            deals = deals_result.scalars().all()

            for deal in deals:
                client_name = "Неизвестно"
                if deal.client:
                    client_name = getattr(deal.client, 'full_name', 'Неизвестно')

                days_until = (deal.expected_close_date - now).days if deal.expected_close_date else 0
                events.append({
                    "id": f"deal_deadline_{deal.id}",
                    "type": "deadline",
                    "title": f"Дедлайн сделки: {getattr(deal, 'name', 'Без названия')}",
                    "description": f"Сумма: {getattr(deal, 'amount', 0)} {getattr(deal, 'currency', 'RUB')}, Клиент: {client_name}",
                    "datetime": deal.expected_close_date.isoformat() if deal.expected_close_date else None,
                    "days_until": days_until,
                    "priority": "high" if days_until <= 2 else "medium"
                })
        except Exception as e:
            logger.error(f"Ошибка при получении дедлайнов: {e}")

        # Сортируем по дате
        events.sort(key=lambda x: x.get("datetime", ""))

        return events

    except Exception as e:
        logger.error(f"Ошибка в get_upcoming_events: {e}")
        logger.error(traceback.format_exc())
        return []


# Вспомогательная функция для безопасного выполнения
async def safe_execute(func, default=None, **kwargs):
    """Безопасно выполняет функцию и возвращает результат или значение по умолчанию"""
    try:
        return await func(**kwargs)
    except Exception as e:
        logger.error(f"Ошибка при выполнении {func.__name__}: {e}")
        logger.error(traceback.format_exc())
        return default() if callable(default) else default
@router.get("/top-clients")
async def get_top_clients(
        limit: int = 5,
        db: AsyncSession = Depends(get_db)
):
    """
    Топ клиентов по сумме сделок
    """
    # Получаем всех клиентов с суммой сделок
    clients_query = select(Client).options(selectinload(Client.deals))
    clients_result = await db.execute(clients_query)
    clients = clients_result.scalars().all()

    top_clients = []
    for client in clients:
        total_amount = sum(deal.amount or 0 for deal in client.deals)
        if total_amount > 0:
            top_clients.append({
                "id": client.id,
                "name": client.full_name,
                "company": client.company,
                "total_amount": float(total_amount),
                "deals_count": len([d for d in client.deals if d.status == DealStatus.WON]),
                "last_deal": max((d.created_at for d in client.deals if d.created_at), default=None)
            })

    # Сортируем по сумме
    top_clients.sort(key=lambda x: x["total_amount"], reverse=True)

    return top_clients[:limit]


@router.get("/alerts")
async def get_alerts(
        db: AsyncSession = Depends(get_db)
):
    """
    Важные уведомления и предупреждения
    """
    alerts = []
    now = datetime.now()

    # Просроченные встречи
    overdue_meetings = await db.execute(
        select(Interaction).where(
            and_(
                Interaction.type == InteractionType.MEETING,
                Interaction.status == "planned",
                Interaction.scheduled_at < now
            )
        ).limit(5)
    )

    for meeting in overdue_meetings.scalars().all():
        alerts.append({
            "type": "warning",
            "title": "Просроченная встреча",
            "message": f"Встреча '{meeting.title}' была запланирована на {meeting.scheduled_at.strftime('%d.%m.%Y %H:%M') if meeting.scheduled_at else 'неизвестное время'}",
            "icon": "⚠️"
        })

    # Сделки с низкой вероятностью
    low_prob_deals = await db.execute(
        select(Deal).where(
            and_(
                Deal.probability < 30,
                Deal.status.in_(DealStatus.active_statuses())
            )
        ).limit(5)
    )

    for deal in low_prob_deals.scalars().all():
        alerts.append({
            "type": "info",
            "title": "Сделка под риском",
            "message": f"Сделка '{deal.name}' имеет низкую вероятность закрытия ({deal.probability}%)",
            "icon": "📉"
        })

    return alerts


# Вспомогательные функции
def get_date_filter(period: str) -> datetime:
    """Возвращает дату для фильтрации по периоду"""
    now = datetime.now()
    if period == "day":
        return now - timedelta(days=1)
    elif period == "week":
        return now - timedelta(days=7)
    elif period == "month":
        return now - timedelta(days=30)
    elif period == "year":
        return now - timedelta(days=365)
    return now - timedelta(days=30)


def calculate_growth(total: int, new: int) -> float:
    """Рассчитывает процент роста"""
    if total == 0:
        return 0
    return round((new / total) * 100, 1)


def calculate_age(birth_date) -> int:
    """Рассчитывает возраст"""
    today = datetime.now().date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def get_interaction_icon(interaction_type) -> str:
    """Возвращает иконку для типа взаимодействия"""
    icons = {
        "call": "📞",
        "meeting": "🤝",
        "email": "📧",
        "sms": "💬",
        "messenger": "💭",
        "task": "✅",
        "note": "📝",
        "chat": "💬"
    }
    return icons.get(interaction_type, "📌")


async def get_clients_dynamics(db: AsyncSession, start_date: datetime, period: str):
    """Динамика добавления клиентов"""
    result = []
    current = start_date
    end = datetime.now()

    delta = timedelta(days=1)
    if period == "week":
        delta = timedelta(days=1)
    elif period == "month":
        delta = timedelta(days=1)
    elif period == "year":
        delta = timedelta(days=30)

    while current <= end:
        next_date = current + delta
        count = await db.scalar(
            select(func.count()).select_from(Client).where(
                and_(
                    Client.created_at >= current,
                    Client.created_at < next_date
                )
            )
        ) or 0

        result.append({
            "date": current.strftime("%Y-%m-%d"),
            "count": count
        })
        current = next_date

    return result


async def get_deals_dynamics(db: AsyncSession, start_date: datetime, period: str):
    """Динамика создания сделок"""
    result = []
    current = start_date
    end = datetime.now()

    delta = timedelta(days=1)
    if period == "week":
        delta = timedelta(days=1)
    elif period == "month":
        delta = timedelta(days=1)
    elif period == "year":
        delta = timedelta(days=30)

    while current <= end:
        next_date = current + delta
        count = await db.scalar(
            select(func.count()).select_from(Deal).where(
                and_(
                    Deal.created_at >= current,
                    Deal.created_at < next_date
                )
            )
        ) or 0

        amount = await db.scalar(
            select(func.sum(Deal.amount)).where(
                and_(
                    Deal.created_at >= current,
                    Deal.created_at < next_date
                )
            )
        ) or 0

        result.append({
            "date": current.strftime("%Y-%m-%d"),
            "count": count,
            "amount": float(amount)
        })
        current = next_date

    return result


async def get_deals_by_status(db: AsyncSession):
    """Распределение сделок по статусам"""
    result = []
    for status in DealStatus:
        count = await db.scalar(
            select(func.count()).select_from(Deal).where(Deal.status == status)
        ) or 0

        if count > 0:
            result.append({
                "status": status.value,
                "count": count,
                "color": get_status_color(status)
            })

    return result


async def get_activity_heatmap(db: AsyncSession, days: int = 30):
    """Тепловая карта активности по дням"""
    result = []
    end = datetime.now()
    start = end - timedelta(days=days)

    current = start
    while current <= end:
        next_date = current + timedelta(days=1)

        # Считаем взаимодействия за день
        interactions = await db.scalar(
            select(func.count()).select_from(Interaction).where(
                and_(
                    Interaction.created_at >= current,
                    Interaction.created_at < next_date
                )
            )
        ) or 0

        # Считаем новые сделки
        deals = await db.scalar(
            select(func.count()).select_from(Deal).where(
                and_(
                    Deal.created_at >= current,
                    Deal.created_at < next_date
                )
            )
        ) or 0

        result.append({
            "date": current.strftime("%Y-%m-%d"),
            "interactions": interactions,
            "deals": deals,
            "total": interactions + deals
        })

        current = next_date

    return result


def get_status_color(status: DealStatus) -> str:
    """Возвращает цвет для статуса сделки"""
    colors = {
        DealStatus.NEW: "#3498db",  # синий
        DealStatus.CONTACT: "#9b59b6",  # фиолетовый
        DealStatus.NEGOTIATION: "#f39c12",  # оранжевый
        DealStatus.PROPOSAL: "#e67e22",  # темно-оранжевый
        DealStatus.CONTRACT: "#2ecc71",  # зеленый
        DealStatus.WON: "#27ae60",  # темно-зеленый
        DealStatus.LOST: "#e74c3c",  # красный
        DealStatus.POSTPONED: "#95a5a6"  # серый
    }
    return colors.get(status, "#3498db")
