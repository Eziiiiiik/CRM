from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
from app.models.enums import DealStatus


class DealBase(BaseModel):
    """Базовая схема сделки"""
    name: str = Field(..., min_length=1, max_length=255, description="Название сделки")
    description: Optional[str] = None
    client_id: int = Field(..., gt=0, description="ID клиента")
    amount: float = Field(0.0, ge=0, description="Сумма сделки")
    currency: str = Field("RUB", min_length=3, max_length=3, description="Валюта (RUB, USD, EUR)")
    status: DealStatus = Field(DealStatus.NEW, description="Статус сделки")
    probability: int = Field(50, ge=0, le=100, description="Вероятность успеха 0-100%")
    expected_close_date: Optional[datetime] = None
    close_reason: Optional[str] = None


class DealCreate(DealBase):
    """Схема для создания сделки"""
    pass


class DealUpdate(BaseModel):
    """Схема для обновления сделки (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    status: Optional[DealStatus] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    expected_close_date: Optional[datetime] = None
    close_reason: Optional[str] = None


class DealClose(BaseModel):
    """Схема для закрытия сделки"""
    status: DealStatus = Field(..., description="Статус закрытия (won/lost/postponed)")
    close_reason: Optional[str] = Field(None, description="Причина закрытия")
    actual_close_date: datetime = Field(default_factory=datetime.now, description="Дата закрытия")


class DealResponse(DealBase):
    """Схема для ответа API"""
    id: int
    actual_close_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Добавляем клиента для удобства (опционально)
    client_name: Optional[str] = None
    client_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DealWithClientResponse(DealResponse):
    """Сделка с полной информацией о клиенте"""
    from app.schemas.client import ClientResponse
    client: Optional[ClientResponse] = None