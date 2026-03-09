from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class IntentType(str, Enum):
    """Типы намерений"""
    GREETING = "greeting"
    FAREWELL = "farewell"
    SCHEDULE_MEETING = "schedule_meeting"
    CHECK_STATUS = "check_status"
    PRICING = "pricing"
    HELP = "help"
    GENERAL_QUESTION = "general_question"
    COMPLAINT = "complaint"
    THANKS = "thanks"


class SentimentType(str, Enum):
    """Тональность"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ChatRequest(BaseModel):
    """Запрос к чату"""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    client_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = {}


class ChatResponse(BaseModel):
    """Ответ от чата"""
    message: str
    session_id: str
    intent: IntentType
    sentiment: Optional[SentimentType] = None
    suggestions: List[str] = []
    quick_replies: List[str] = []
    actions: List[Dict[str, Any]] = []
    requires_human: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class MeetingRequest(BaseModel):
    """Запрос на создание встречи"""
    client_id: int
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    preferred_date: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}")
    preferred_time: str = Field(..., pattern=r"\d{2}:\d{2}")
    duration_minutes: int = 30
    meeting_type: str = "online"
    manager_id: Optional[int] = None


class MeetingResponse(BaseModel):
    """Ответ на запрос встречи"""
    meeting_id: int
    status: str
    datetime: str
    manager_name: str
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    instructions: Optional[str] = None