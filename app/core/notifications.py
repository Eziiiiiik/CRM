"""
Система уведомлений с использованием WebSocket.
Упрощенная версия без Redis для начала разработки.
"""
from typing import Dict, Set
from fastapi import WebSocket
import asyncio
from app.core.config import get_settings

settings = get_settings()


class ConnectionManager:
    """
    Менеджер WebSocket соединений.
    Отслеживает активные подключения и отправляет уведомления.
    """

    def __init__(self):
        # Храним активные подключения: user_id -> список WebSocket
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Очередь уведомлений (вместо Redis для простоты)
        self.notification_queues: Dict[int, asyncio.Queue] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Принимает WebSocket соединение и сохраняет его.

        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
            self.notification_queues[user_id] = asyncio.Queue()
        self.active_connections[user_id].add(websocket)

        print(f"✅ User {user_id} connected")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """Закрывает соединение и удаляет его из активных."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.notification_queues:
                    del self.notification_queues[user_id]

        print(f"❌ User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: int):
        """
        Отправляет персональное сообщение конкретному пользователю.

        Args:
            message: Сообщение для отправки
            user_id: ID получателя
        """
        if user_id in self.active_connections:
            # Сохраняем сообщение в очередь
            if user_id in self.notification_queues:
                await self.notification_queues[user_id].put(message)

            # Отправляем всем соединениям пользователя
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                except (RuntimeError, ConnectionError) as e:  # ← конкретные исключения
                    # Если отправка не удалась (соединение закрыто или ошибка сети), удаляем соединение
                    print(f"⚠️ Ошибка отправки пользователю {user_id}: {e}")
                    await self.disconnect(connection, user_id)

    async def broadcast(self, message: dict):
        """
        Отправляет сообщение всем подключенным пользователям.

        Args:
            message: Сообщение для рассылки
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    async def get_user_notifications(self, user_id: int) -> list:
        """Получить все уведомления пользователя из очереди."""
        notifications = []
        if user_id in self.notification_queues:
            queue = self.notification_queues[user_id]
            while not queue.empty():
                try:
                    notification = queue.get_nowait()
                    notifications.append(notification)
                except asyncio.QueueEmpty:
                    break
        return notifications


# Создаем глобальный экземпляр менеджера подключений
manager = ConnectionManager()