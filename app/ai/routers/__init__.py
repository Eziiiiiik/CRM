"""
AI-ассистент для CRM
"""
from app.ai.client_assistant import ClientAIAssistant
from app.ai.dependencies import get_ai_assistant, get_session_id
from app.ai.models import ChatRequest, ChatResponse, IntentType, SentimentType

__all__ = [
    "ClientAIAssistant",
    "get_ai_assistant",
    "get_session_id",
    "ChatRequest",
    "ChatResponse",
    "IntentType",
    "SentimentType"
]