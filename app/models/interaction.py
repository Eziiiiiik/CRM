from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
import enum


class InteractionType(str, enum.Enum):
    """Типы взаимодействий с клиентом"""
    CALL = "call"
    MEETING = "meeting"
    EMAIL = "email"
    SMS = "sms"
    MESSENGER = "messenger"
    SOCIAL = "social"
    TASK = "task"
    NOTE = "note"
    CHAT = "chat"
    OTHER = "other"


class InteractionDirection(str, enum.Enum):
    """Направление взаимодействия"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class InteractionStatus(str, enum.Enum):
    """Статус взаимодействия"""
    PLANNED = "planned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class Interaction(Base):
    """Модель истории взаимодействий с клиентом"""

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    # Связь с клиентом
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    client = relationship("Client", back_populates="interactions")

    # Связь со сделкой (опционально)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)
    deal = relationship("Deal", backref="interactions")

    # Тип взаимодействия
    type = Column(Enum(InteractionType), nullable=False)
    direction = Column(Enum(InteractionDirection), default=InteractionDirection.OUTGOING)
    status = Column(Enum(InteractionStatus), default=InteractionStatus.COMPLETED)

    # Основная информация
    title = Column(String(255), nullable=False)
    description = Column(Text)
    result = Column(Text)

    # Временные метки
    scheduled_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)

    # Контактная информация
    contact_person = Column(String(255))
    contact_phone = Column(String(20))
    contact_email = Column(String(255))

    # Дополнительные данные
    additional_data = Column(JSON, default=dict)

    # Системные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Interaction(id={self.id}, type={self.type}, client_id={self.client_id})>"

    @property
    def is_overdue(self) -> bool:
        """Проверка, просрочено ли запланированное взаимодействие"""
        if self.status == InteractionStatus.PLANNED and self.scheduled_at:
            # Получаем значение scheduled_at и преобразуем в naive datetime
            scheduled = self.scheduled_at
            if isinstance(scheduled, datetime):
                # Убираем timezone для сравнения
                scheduled_naive = scheduled.replace(tzinfo=None)
                now_naive = datetime.now().replace(tzinfo=None)
                return scheduled_naive < now_naive
        return False