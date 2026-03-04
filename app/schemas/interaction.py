from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.interaction import InteractionType, InteractionDirection, InteractionStatus


class InteractionBase(BaseModel):
    """Базовая схема взаимодействия"""
    client_id: int = Field(..., gt=0)
    deal_id: Optional[int] = Field(None, gt=0)
    type: InteractionType
    direction: InteractionDirection = InteractionDirection.OUTGOING
    status: InteractionStatus = InteractionStatus.COMPLETED
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    result: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = Field(None, pattern=r'^\+?[0-9\-\s]{10,20}$')
    contact_email: Optional[str] = None
    metadata: Dict[str, Any] = {}


class InteractionCreate(InteractionBase):
    """Схема для создания взаимодействия"""
    pass


class InteractionUpdate(BaseModel):
    """Схема для обновления взаимодействия"""
    type: Optional[InteractionType] = None
    direction: Optional[InteractionDirection] = None
    status: Optional[InteractionStatus] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    result: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = Field(None, pattern=r'^\+?[0-9\-\s]{10,20}$')
    contact_email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InteractionResponse(InteractionBase):
    """Схема для ответа API"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_overdue: bool

    model_config = ConfigDict(from_attributes=True)


class InteractionWithClientResponse(InteractionResponse):
    """Взаимодействие с информацией о клиенте"""
    client_name: str
    client_email: str
    deal_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)