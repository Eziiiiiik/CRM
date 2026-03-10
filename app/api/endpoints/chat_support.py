from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.core.database import get_db
from app.websocket.support_chat import manager

router = APIRouter(prefix="/support", tags=["support"])

logger = logging.getLogger(__name__)


@router.websocket("/client")
async def support_client_websocket(
        websocket: WebSocket,
        client_id: Optional[int] = None,
        db: AsyncSession = Depends(get_db)
):
    """
    WebSocket для клиентов
    Подключение: ws://localhost:8001/api/v1/support/client?client_id=123
    """
    chat_id = None
    try:
        chat_id = await manager.connect_client(websocket, client_id, db)

        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            await manager.handle_client_message(chat_id, data, db)

    except WebSocketDisconnect:
        logger.info(f"Клиент отключился от чата {chat_id}")
        await manager.disconnect(websocket)


@router.websocket("/operator")
async def support_operator_websocket(
        websocket: WebSocket,
        operator_id: str
):
    """
    WebSocket для операторов
    Подключение: ws://localhost:8001/api/v1/support/operator?operator_id=op123
    """
    try:
        await manager.connect_operator(websocket, operator_id)

        while True:
            # Получаем сообщение от оператора
            data = await websocket.receive_json()
            await manager.handle_operator_message(websocket, data)

    except WebSocketDisconnect:
        logger.info(f"Оператор {operator_id} отключился")
        await manager.disconnect(websocket)


@router.get("/queue")
async def get_queue_status():
    """Получить статус очереди ожидания"""
    return {
        "waiting_clients": manager.waiting_queue.qsize(),
        "active_operators": len(manager.available_operators),
        "active_chats": len(manager.active_chats)
    }