import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc

from app.models.notification import Notification

logger = logging.getLogger(__name__)

class NotificationService:
    """Сервис для работы с уведомлениями в БД."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> Notification:
        """Создать и сохранить уведомление."""
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)
        logger.info(f"Created notification {notif.id} for user {user_id}")
        return notif

    async def get_unread_notifications(
        self, user_id: int, limit: int = 50
    ) -> List[Notification]:
        """Получить непрочитанные уведомления пользователя."""
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .order_by(desc(Notification.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all_notifications(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Notification]:
        """Получить все уведомления с пагинацией."""
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Отметить конкретное уведомление как прочитанное."""
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    async def mark_all_as_read(self, user_id: int) -> int:
        """Отметить все уведомления пользователя как прочитанные. Возвращает количество."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount