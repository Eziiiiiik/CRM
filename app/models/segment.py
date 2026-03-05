from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Таблица для связи многие-ко-многим (клиенты <-> сегменты)
client_segments = Table(
    'client_segments',
    Base.metadata,
    Column('client_id', Integer, ForeignKey('clients.id', ondelete='CASCADE'), primary_key=True),
    Column('segment_id', Integer, ForeignKey('segments.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now())
)


class Segment(Base):
    """Модель сегмента клиентов"""

    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)

    # Основная информация
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)

    # Правила сегментации (хранятся в JSON)
    # Пример: {"field": "total_deals_sum", "operator": ">=", "value": 1000000}
    rules = Column(JSON, default=list)

    # Настройки
    is_active = Column(Boolean, default=True)
    is_auto_update = Column(Boolean, default=True)  # Автоматически обновлять
    update_frequency = Column(String(20), default="daily")  # daily, hourly, manual

    # Статистика (кэшируется)
    clients_count = Column(Integer, default=0)

    # Визуализация
    color = Column(String(7), default="#808080")  # HEX цвет для графиков

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_calculated_at = Column(DateTime(timezone=True))  # Последний пересчёт

    # Связи
    clients = relationship(
        "Client",
        secondary=client_segments,
        back_populates="segments",
        passive_deletes=True
    )

    def __repr__(self):
        return f"<Segment(id={self.id}, name={self.name}, clients={self.clients_count})>"