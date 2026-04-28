from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.services.notification_service import NotificationService
from app.api.endpoints.auth import get_current_user
from app.models.user import User
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["notifications"])

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    entity_type: str | None
    entity_id: int | None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить все уведомления текущего пользователя (с пагинацией)."""
    service = NotificationService(db)
    notifs = await service.get_all_notifications(current_user.id, skip, limit)
    return notifs


@router.get("/unread", response_model=List[NotificationResponse])
async def get_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить только непрочитанные уведомления"""


    @router.put("/{notification_id}/read")
    async def mark_notification_read(
            notification_id: int,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
    ):
        """Отметить конкретное уведомление как прочитанное."""
        service = NotificationService(db)
        success = await service.mark_as_read(notification_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"status": "ok"}

    @router.put("/read-all")
    async def mark_all_notifications_read(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
    ):
        """Отметить все уведомления пользователя как прочитанные."""
        service = NotificationService(db)
        count = await service.mark_all_as_read(current_user.id)
        return {"status": "ok", "marked_count": count}