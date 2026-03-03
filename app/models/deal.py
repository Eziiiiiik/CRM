from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import DealStatus
import enum


class Deal(Base):
    """Модель сделки"""

    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Название сделки
    description = Column(Text)  # Описание

    # Связь с клиентом (обязательное поле)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    client = relationship("Client", back_populates="deals")  # back_populates позволяет обращаться client.deals

    # Финансовая информация
    amount = Column(Float, default=0.0)  # Сумма сделки
    currency = Column(String(3), default="RUB")  # Валюта

    # Статус (используем Enum)
    status = Column(Enum(DealStatus), default=DealStatus.NEW, nullable=False)

    # Вероятность успеха (0-100%)
    probability = Column(Integer, default=50)  # 50% по умолчанию

    # Даты
    expected_close_date = Column(DateTime(timezone=True))  # Ожидаемая дата закрытия
    actual_close_date = Column(DateTime(timezone=True))  # Фактическая дата закрытия

    # Причина закрытия (для Lost/Postponed)
    close_reason = Column(Text)

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Deal(id={self.id}, name={self.name}, status={self.status})>"

    def is_active(self):
        """Проверяет, активна ли сделка"""
        return self.status in DealStatus.active_statuses()

    def is_closed(self):
        """Проверяет, закрыта ли сделка"""
        return self.status in DealStatus.closed_statuses()