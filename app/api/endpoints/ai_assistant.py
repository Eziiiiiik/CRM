"""
Эндпоинты для взаимодействия с AI ассистентом.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import httpx
from typing import Optional, Dict, Any

from app.core.config import get_settings
from app.core.notifications import manager

router = APIRouter(prefix="/ai", tags=["ai_assistant"])
settings = get_settings()


class AIClient:
    """Клиент для работы с AI сервисом."""

    def __init__(self):
        self.base_url = settings.AI_API_URL
        self.api_key = settings.AI_API_KEY
        self.timeout = 30.0  # Таймаут для запросов

    async def ask_question(self, question: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Отправить вопрос AI ассистенту.

        Args:
            question: Текст вопроса
            context: Контекст (данные о клиенте, сделки и т.д.)

        Returns:
            Ответ от AI
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/ask",
                    json={
                        "question": question,
                        "context": context or {},
                        "api_key": self.api_key
                    },
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="AI service timeout")
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"AI service error: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error communicating with AI service: {str(e)}"
                )

    async def analyze_data(self, data_type: str, data: Dict) -> Dict[str, Any]:
        """
        Отправить данные на анализ AI.

        Args:
            data_type: Тип данных (клиент, сделка, отчет)
            data: Данные для анализа
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/analyze",
                    json={
                        "data_type": data_type,
                        "data": data,
                        "api_key": self.api_key
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    async def get_recommendations(self, user_id: int, context: Dict) -> Dict[str, Any]:
        """
        Получить рекомендации от AI.

        Args:
            user_id: ID пользователя
            context: Контекст для рекомендаций
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/recommendations",
                    json={
                        "user_id": user_id,
                        "context": context,
                        "api_key": self.api_key
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))


# Создаем глобальный экземпляр AI клиента
ai_client = AIClient()


@router.post("/ask")
async def ask_ai_assistant(
        question: str,
        context: Optional[Dict] = None,
        background_tasks: BackgroundTasks = None
):
    """
    Задать вопрос AI ассистенту.
    """
    response = await ai_client.ask_question(question, context)

    # Отправляем уведомление о полученном ответе
    if background_tasks:
        background_tasks.add_task(
            manager.publish_notification,
            "ai_responses",
            {
                "type": "ai_response_ready",
                "data": {
                    "question": question[:50] + "...",
                    "response": response
                }
            }
        )

    return response


@router.post("/analyze/{data_type}")
async def analyze_with_ai(
        data_type: str,
        data: Dict
):
    """
    Отправить данные на анализ AI.

    - **data_type**: Тип данных (clients, deals, reports)
    - **data**: Данные для анализа
    """
    result = await ai_client.analyze_data(data_type, data)
    return result


@router.get("/recommendations/{user_id}")
async def get_personalized_recommendations(
        user_id: int,
        context: Optional[Dict] = None
):
    """
    Получить персонализированные рекомендации от AI.
    """
    recommendations = await ai_client.get_recommendations(user_id, context or {})
    return recommendations