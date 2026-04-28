from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Notification(Base):
    """
    Уведомление для пользователя.
    Сохраняется в БД и может быть отправлено через WebSocket.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(String(1000), nullable=False)
    type = Column(String(50), default="info")   # info, warning, success, error
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # дополнительные поля (например, ссылка на сущность) – по желанию
    entity_type = Column(String(50), nullable=True)  # 'deal', 'client', etc.
    entity_id = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, is_read={self.is_read})>"