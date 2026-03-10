from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.ai.client_assistant import ClientAIAssistant
from app.ai.dependencies import get_ai_assistant, get_session_id
from app.ai.models import ChatRequest, ChatResponse
from app.models.interaction import Interaction

router = APIRouter(prefix="/chat", tags=["ai-chat"])


@router.post("/message", response_model=ChatResponse)
async def chat_message(
        request: ChatRequest,
        session_id: str = Depends(get_session_id),
        assistant: ClientAIAssistant = Depends(get_ai_assistant),
        db: AsyncSession = Depends(get_db)
):
    """
    Отправить сообщение AI-ассистенту
    """
    try:
        # Передаем session_id в ассистент
        response_data = await assistant.process_message(
            message=request.message,
            client_id=request.client_id,
            session_id=session_id
        )

        # Добавляем session_id в ответ
        response_data["session_id"] = session_id

        # Преобразуем словарь в модель ChatResponse
        return ChatResponse(
            message=response_data.get("message", ""),
            session_id=session_id,
            intent=response_data.get("intent", "general_question"),
            suggestions=response_data.get("suggestions", []),
            quick_replies=response_data.get("quick_replies", []),
            actions=response_data.get("actions", []),
            requires_human=response_data.get("requires_human", False)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обработки сообщения: {str(e)}"
        )


@router.get("/history/{client_id}")
async def get_chat_history(
        client_id: int,
        limit: int = 50,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить историю чатов клиента
    """
    # Получаем взаимодействия клиента с AI
    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.client_id == client_id,
            Interaction.type == "chat"
        )
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )

    interactions = result.scalars().all()

    return [
        {
            "id": i.id,
            "message": i.description,
            "response": i.result,
            "created_at": i.created_at,
            "sentiment": i.additional_data.get("sentiment") if i.additional_data else None
        }
        for i in interactions
    ]


@router.post("/feedback/{session_id}")
async def send_feedback(
        session_id: str,
        rating: int = 5,
        comment: Optional[str] = None
):

    return {"status": "ok", "message": "Спасибо за обратную связь!"}