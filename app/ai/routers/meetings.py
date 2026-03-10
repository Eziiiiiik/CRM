from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.ai.models import MeetingRequest, MeetingResponse
from app.models.client import Client

router = APIRouter(prefix="/meetings", tags=["ai-meetings"])


@router.post("/request", response_model=MeetingResponse)
async def request_meeting(
        request: MeetingRequest,
        db: AsyncSession = Depends(get_db)
):
    """
    Запросить встречу через AI-ассистента
    """
    # Проверяем существование клиента
    client = await db.get(Client, request.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Находим свободного менеджера (базовая логика)
    manager = await find_available_manager(db)
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No managers available"
        )

    # Создаем встречу
    meeting_datetime = datetime.strptime(
        f"{request.preferred_date} {request.preferred_time}",
        "%Y-%m-%d %H:%M"
    )

    # Сохраняем в БД
    meeting = await create_meeting(
        db=db,
        client_id=client.id,
        manager_id=manager.id,
        title=request.title,
        description=request.description,
        datetime=meeting_datetime,
        duration=request.duration_minutes,
        meeting_type=request.meeting_type
    )

    # Генерируем ссылку для онлайн встречи
    meeting_link = None
    if request.meeting_type == "online":
        meeting_link = f"https://meet.example.com/{meeting.id}"

    return MeetingResponse(
        meeting_id=meeting.id,
        status="scheduled",
        datetime=meeting_datetime.isoformat(),
        manager_name=manager.full_name if hasattr(manager, 'full_name') else "Менеджер",
        meeting_link=meeting_link,
        instructions="Ссылка для подключения будет отправлена на email"
    )


@router.get("/available-slots")
async def get_available_slots(
        date: str,
        duration: int = 30,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить доступные слоты для встреч на указанную дату
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Базовая логика - слоты с 9 до 18, каждый час
    slots = []
    for hour in range(9, 18):
        slot_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour))
        slots.append({
            "time": slot_time.strftime("%H:%M"),
            "available": True
        })

    return {"date": date, "slots": slots}


async def find_available_manager(db: AsyncSession):
    """Находит доступного менеджера"""

    # TODO: реализовать поиск менеджера
    # Пока возвращаем заглушку
    class MockManager:
        def __init__(self):
            self.id = 1
            self.full_name = "Менеджер"

    return MockManager()


async def create_meeting(db: AsyncSession, **kwargs):
    """Создает встречу в БД"""

    # TODO: реализовать сохранение встречи
    # Пока возвращаем объект с id
    class Meeting:
        def __init__(self, **kwargs):
            self.id = 1
            for k, v in kwargs.items():
                setattr(self, k, v)

    return Meeting(**kwargs)