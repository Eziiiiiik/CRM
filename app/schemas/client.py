"""
Pydantic схемы для валидации и сериализации данных клиента.
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional


class ClientBase(BaseModel):
    """Базовая схема клиента."""
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    """Схема для создания клиента."""
    pass


class ClientUpdate(BaseModel):
    """Схема для обновления клиента (все поля опциональны)."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ClientInDB(ClientBase):
    """Схема для клиента в базе данных."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Включаем поддержку ORM для SQLAlchemy
    model_config = ConfigDict(from_attributes=True)


class ClientResponse(ClientInDB):
    """Схема для ответа API."""
    pass