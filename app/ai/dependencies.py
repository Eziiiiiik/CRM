from typing import Optional, AsyncGenerator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import time

from app.core.database import get_db
from app.ai.client_assistant import ClientAIAssistant


async def get_ai_assistant(
        request: Request,
        db: AsyncSession = Depends(get_db)
) -> AsyncGenerator[ClientAIAssistant, None]:
    """
    Зависимость для получения AI-ассистента
    """
    assistant = ClientAIAssistant(db)
    yield assistant
    # Если у ассистента есть метод close - вызовите его
    # await assistant.close()


async def get_session_id(
        request: Request,
        client_id: Optional[int] = None
) -> str:
    """
    Получает или создает session_id
    """
    # Проверяем заголовки
    session_id = request.headers.get("X-Session-ID")

    # Или из cookies
    if not session_id:
        session_id = request.cookies.get("session_id")

    # Или из query параметра
    if not session_id:
        session_id = request.query_params.get("session_id")

    # Генерируем новый, если ничего нет
    if not session_id:
        base = f"{client_id}_{time.time()}" if client_id else str(time.time())
        session_id = hashlib.md5(base.encode()).hexdigest()

    return session_id