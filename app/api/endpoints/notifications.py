"""
WebSocket эндпоинты для уведомлений в реальном времени.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.notifications import manager

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

        # Слушаем входящие сообщения (если нужно)
        while True:
            data = await websocket.receive_text()
            # Здесь можно обрабатывать сообщения от клиента
            # Например, подписка на определенные события

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        await manager.publish_notification(
            "system",
            {"type": "user_disconnected", "user_id": user_id}
        )