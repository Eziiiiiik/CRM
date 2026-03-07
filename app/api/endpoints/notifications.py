"""
WebSocket эндпоинты для уведомлений в реальном времени.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.notifications import manager
import logging
from datetime import datetime  # ← добавьте эту строку!

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        user_id: int
):
    """
    WebSocket endpoint для получения уведомлений в реальном времени.

    Подключение: ws://localhost:8000/ws/{user_id}
    """
    await manager.connect(websocket, user_id)
    try:
        # Отправляем приветственное сообщение
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Connected as user {user_id}"
        })

        # Обрабатываем входящие сообщения
        while True:
            data = await websocket.receive_text()
            logger.info(f"WebSocket сообщение от пользователя {user_id}: {data}")

            # Отправляем подтверждение с временной меткой
            await websocket.send_json({
                "type": "message_received",
                "data": data,
                "timestamp": datetime.now().isoformat()  # ← здесь используется datetime
            })

    except WebSocketDisconnect:
        logger.info(f"Пользователь {user_id} отключился")
        await manager.disconnect(websocket, user_id)
        await manager.publish_notification(
            "system",
            {"type": "user_disconnected", "user_id": user_id}
        )