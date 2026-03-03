from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class MaritalStatusEnum(str, Enum):
    MARRIED = "married"
    SINGLE = "single"
    DIVORCED = "divorced"
    WIDOWED = "widowed"


class MessengerType(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    VIBER = "viber"
    SIGNAL = "signal"
    THREEMA = "threema"
    WECHAT = "wechat"
    OTHER = "other"


class SocialNetworkType(str, Enum):
    VK = "vk"
    OK = "ok"  # Одноклассники
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    OTHER = "other"


class AddressType(str, Enum):
    HOME = "home"
    WORK = "work"
    REGISTRATION = "registration"
    SHIPPING = "shipping"
    OTHER = "other"


class CommunicationChannel(str, Enum):
    PHONE = "phone"
    EMAIL = "email"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    VK = "vk"


# Вложенные схемы
class MessengerBase(BaseModel):
    type: MessengerType
    value: str  # @username или номер телефона
    is_primary: bool = False
    notes: Optional[str] = None


class SocialNetworkBase(BaseModel):
    type: SocialNetworkType
    url: str
    is_primary: bool = False
    notes: Optional[str] = None


class AddressBase(BaseModel):
    type: AddressType
    country: str = "РФ"
    city: str
    street: Optional[str] = None
    house: Optional[str] = None
    apartment: Optional[str] = None
    postal_code: Optional[str] = None
    is_primary: bool = False
    notes: Optional[str] = None


class CommunicationPreferences(BaseModel):
    preferred_channel: Optional[CommunicationChannel] = None
    do_not_call: bool = False
    do_not_email: bool = False
    do_not_sms: bool = False
    best_time_to_call: Optional[str] = None  # "morning", "afternoon", "evening"
    notes: Optional[str] = None


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = "#808080"


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Основные схемы клиента
class ClientBase(BaseModel):
    # ФИО
    last_name: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)

    # Личная информация
    birth_date: Optional[date] = None
    gender: Optional[GenderEnum] = None
    marital_status: Optional[MaritalStatusEnum] = None

    # Контакты
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r'^\+?[0-9\-\s]{10,20}$')
    alternative_phone: Optional[str] = Field(None, pattern=r'^\+?[0-9\-\s]{10,20}$')

    # Мессенджеры и соцсети
    messengers: List[MessengerBase] = []
    social_networks: List[SocialNetworkBase] = []

    # Адреса
    addresses: List[AddressBase] = []

    # Профессиональная информация
    company: Optional[str] = None
    position: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = Field(None, pattern=r'^https?://.+')

    # Настройки
    communication_preferences: CommunicationPreferences = CommunicationPreferences()

    # Дополнительно
    notes: Optional[str] = None
    source: Optional[str] = None

    @field_validator('birth_date')
    def validate_birth_date(cls, v):
        if v and v > date.today():
            raise ValueError('Birth date cannot be in the future')
        return v


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    # Все поля опциональны для частичного обновления
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[GenderEnum] = None
    marital_status: Optional[MaritalStatusEnum] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[0-9\-\s]{10,20}$')
    alternative_phone: Optional[str] = Field(None, pattern=r'^\+?[0-9\-\s]{10,20}$')
    messengers: Optional[List[MessengerBase]] = None
    social_networks: Optional[List[SocialNetworkBase]] = None
    addresses: Optional[List[AddressBase]] = None
    company: Optional[str] = None
    position: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = Field(None, pattern=r'^https?://.+')
    communication_preferences: Optional[CommunicationPreferences] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class ClientResponse(ClientBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_contact_at: Optional[datetime] = None
    tags: List[TagResponse] = []

    # Добавляем производные поля
    full_name: str
    short_name: str

    model_config = ConfigDict(from_attributes=True)


class ClientDetailResponse(ClientResponse):
    """Детальная информация о клиенте (со всеми связями)"""
    deals: List['DealResponse'] = []

    model_config = ConfigDict(from_attributes=True)


# ВАЖНО: ВЫЗОВ REBUILD ПОСЛЕ ВСЕХ КЛАССОВ!
from app.schemas.deal import DealResponse

ClientDetailResponse.model_rebuild()