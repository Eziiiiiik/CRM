from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class OperatorEnum(str, Enum):
    """Операторы для правил сегментации"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
    LESS_THAN_OR_EQUALS = "less_than_or_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"


class RuleField(str, Enum):
    """Доступные поля для правил"""
    # Клиент
    LAST_NAME = "last_name"
    FIRST_NAME = "first_name"
    EMAIL = "email"
    PHONE = "phone"
    COMPANY = "company"
    POSITION = "position"
    INDUSTRY = "industry"
    CITY = "city"  # из адресов
    GENDER = "gender"
    MARITAL_STATUS = "marital_status"
    SOURCE = "source"
    IS_VERIFIED = "is_verified"

    # Сделки
    TOTAL_DEALS_SUM = "total_deals_sum"
    DEALS_COUNT = "deals_count"
    WON_DEALS_COUNT = "won_deals_count"
    LOST_DEALS_COUNT = "lost_deals_count"
    AVG_DEAL_AMOUNT = "avg_deal_amount"

    # Взаимодействия
    INTERACTIONS_COUNT = "interactions_count"
    LAST_INTERACTION_DAYS = "last_interaction_days"
    CALLS_COUNT = "calls_count"
    MEETINGS_COUNT = "meetings_count"

    # Временные
    DAYS_FROM_REGISTRATION = "days_from_registration"
    BIRTH_MONTH = "birth_month"
    CREATED_AT = "created_at"


class RuleBase(BaseModel):
    """Схема правила сегментации"""
    field: RuleField
    operator: OperatorEnum
    value: Any
    field_type: str = "string"  # string, number, date, boolean


class SegmentBase(BaseModel):
    """Базовая схема сегмента"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    rules: List[Dict[str, Any]] = []
    is_active: bool = True
    is_auto_update: bool = True
    update_frequency: str = "daily"
    color: str = "#808080"


class SegmentCreate(SegmentBase):
    """Схема для создания сегмента"""
    pass


class SegmentUpdate(BaseModel):
    """Схема для обновления сегмента"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rules: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    is_auto_update: Optional[bool] = None
    update_frequency: Optional[str] = None
    color: Optional[str] = None


class SegmentResponse(SegmentBase):
    """Схема для ответа API"""
    id: int
    clients_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_calculated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SegmentDetailResponse(SegmentResponse):
    """Детальная информация о сегменте"""
    # Опционально: первые несколько клиентов
    sample_clients: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)