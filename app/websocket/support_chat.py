from fastapi import WebSocket
from typing import Dict, Set, Optional
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.support_assistant import SupportAIAssistant

logger = logging.getLogger(__name__)


class SupportChatManager:
    """
    Менеджер чатов поддержки
    """

    def __init__(self):
        # Активные чаты: chat_id -> {websocket, client_id, operator_id, messages}
        self.active_chats: Dict[str, Dict] = {}

        # Очередь ожидания оператора
        self.waiting_queue: asyncio.Queue = asyncio.Queue()

        # Подключенные операторы
        self.available_operators: Set[WebSocket] = set()
        self.operator_sessions: Dict[WebSocket, str] = {}  # websocket -> operator_id

    async def connect_client(
            self,
            websocket: WebSocket,
            client_id: Optional[int],
            db: AsyncSession
    ):
        """Подключает клиента к чату"""
        await websocket.accept()

        # Создаём уникальный ID чата
        chat_id = f"chat_{datetime.now().timestamp()}_{client_id if client_id else 'guest'}"

        # Создаём AI-ассистента для этого чата
        ai_assistant = SupportAIAssistant(db)

        self.active_chats[chat_id] = {
            "websocket": websocket,
            "client_id": client_id,
            "operator_id": None,
            "ai_assistant": ai_assistant,
            "messages": [],
            "waiting_for_operator": False,
            "created_at": datetime.now()
        }

        logger.info(f"✅ Клиент {client_id or 'guest'} подключился к чату {chat_id}")

        # Отправляем приветствие
        await self.send_ai_response(chat_id, "Приветствие", client_id, db)

        return chat_id

    async def connect_operator(self, websocket: WebSocket, operator_id: str):
        """Подключает оператора"""
        await websocket.accept()
        self.available_operators.add(websocket)
        self.operator_sessions[websocket] = operator_id

        logger.info(f"✅ Оператор {operator_id} подключился")

        # Отправляем список ожидающих клиентов
        await self.send_waiting_queue(websocket)

    async def disconnect(self, websocket: WebSocket):
        """Отключает пользователя"""
        # Проверяем, был ли это оператор
        if websocket in self.available_operators:
            operator_id = self.operator_sessions.get(websocket)
            self.available_operators.remove(websocket)
            self.operator_sessions.pop(websocket, None)
            logger.info(f"❌ Оператор {operator_id} отключился")
            return

        # Проверяем, был ли это клиент
        for chat_id, chat in list(self.active_chats.items()):
            if chat["websocket"] == websocket:
                # Если клиент ждал оператора, удаляем из очереди
                if chat["waiting_for_operator"]:
                    # TODO: удалить из очереди ожидания
                    pass

                del self.active_chats[chat_id]
                logger.info(f"❌ Чат {chat_id} закрыт")
                break

    async def handle_client_message(
            self,
            chat_id: str,
            message: str,
    ):
        """Обрабатывает сообщение от клиента"""
        chat = self.active_chats.get(chat_id)
        if not chat:
            return

        # Сохраняем сообщение
        chat["messages"].append({
            "role": "client",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # Если клиент уже соединён с оператором
        if chat["operator_id"]:
            await self.send_to_operator(chat["operator_id"], {
                "type": "client_message",
                "chat_id": chat_id,
                "client_id": chat["client_id"],
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            return

        # Обрабатываем через AI
        response = await chat["ai_assistant"].process_message(
            message=message,
            client_id=chat["client_id"],
            session_id=chat_id
        )

        # Сохраняем ответ AI
        chat["messages"].append({
            "role": "ai",
            "content": response["message"],
            "timestamp": datetime.now().isoformat()
        })

        # Отправляем ответ клиенту
        await chat["websocket"].send_json(response)

        # Если клиент запросил оператора
        if response.get("transfer_to_human"):
            await self.add_to_waiting_queue(chat_id, chat["client_id"])
            chat["waiting_for_operator"] = True

    async def handle_operator_message(
            self,
            websocket: WebSocket,
            message: Dict
    ):
        """Обрабатывает сообщение от оператора"""
        message_type = message.get("type")

        if message_type == "take_chat":
            # Оператор берёт чат
            chat_id = message.get("chat_id")
            operator_id = self.operator_sessions.get(websocket)

            if chat_id in self.active_chats and operator_id:
                chat = self.active_chats[chat_id]
                chat["operator_id"] = operator_id

                # Уведомляем клиента
                await chat["websocket"].send_json({
                    "type": "operator_connected",
                    "message": "Оператор подключился к чату",
                    "operator_id": operator_id
                })

                # Уведомляем оператора
                await websocket.send_json({
                    "type": "chat_taken",
                    "chat_id": chat_id,
                    "client_id": chat["client_id"],
                    "history": chat["messages"][-10:]  # последние 10 сообщений
                })

        elif message_type == "operator_message":
            # Оператор отправляет сообщение клиенту
            chat_id = message.get("chat_id")
            text = message.get("message")

            if chat_id in self.active_chats:
                chat = self.active_chats[chat_id]

                # Сохраняем сообщение
                chat["messages"].append({
                    "role": "operator",
                    "content": text,
                    "timestamp": datetime.now().isoformat()
                })

                # Отправляем клиенту
                await chat["websocket"].send_json({
                    "type": "operator_message",
                    "message": text,
                    "timestamp": datetime.now().isoformat()
                })

    async def send_ai_response(
            self,
            chat_id: str,
            message: str,
            client_id: Optional[int],
            db: AsyncSession
    ):
        """Отправляет ответ от AI"""
        chat = self.active_chats.get(chat_id)
        if not chat:
            return

        # Создаём временный ассистент, если его нет
        if "ai_assistant" not in chat:
            chat["ai_assistant"] = SupportAIAssistant(db)

        response = await chat["ai_assistant"].process_message(
            message=message,
            client_id=client_id,
            session_id=chat_id
        )

        await chat["websocket"].send_json(response)

    async def add_to_waiting_queue(self, chat_id: str, client_id: Optional[int]):
        """Добавляет клиента в очередь ожидания оператора"""
        await self.waiting_queue.put({
            "chat_id": chat_id,
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        })

        # Уведомляем всех свободных операторов
        for operator_ws in self.available_operators:
            await operator_ws.send_json({
                "type": "new_client_waiting",
                "queue_size": self.waiting_queue.qsize()
            })

    async def send_waiting_queue(self, operator_ws: WebSocket):
        """Отправляет очередь ожидания оператору"""
        queue_size = self.waiting_queue.qsize()
        await operator_ws.send_json({
            "type": "waiting_queue",
            "size": queue_size,
            "clients": []  # TODO: добавить информацию о клиентах в очереди
        })

    async def send_to_operator(self, operator_id: str, message: Dict):
        """Отправляет сообщение оператору"""
        for ws, op_id in self.operator_sessions.items():
            if op_id == operator_id:
                await ws.send_json(message)
                break


# Глобальный экземпляр менеджера
manager = SupportChatManager()