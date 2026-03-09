import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import get_settings
from app.models.client import Client
from app.models.deal import Deal
from app.models.interaction import Interaction, InteractionType

logger = logging.getLogger(__name__)
settings = get_settings()


class ClientAIAssistant:
    """
    Умный ассистент для помощи клиентам
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.context: Dict[str, Any] = {}

    async def process_message(
            self,
            message: str,
            client_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Основной метод обработки сообщений от клиента
        """
        # 1. Определяем намерение клиента
        intent = await self._detect_intent(message)

        # 2. Загружаем контекст (если есть client_id)
        if client_id:
            client_context = await self._load_client_context(client_id)
            self.context.update(client_context)

        # 3. Выбираем действие на основе намерения
        response = await self._route_intent(intent, message, client_id)

        # 4. Сохраняем взаимодействие в историю
        if client_id:
            await self._save_interaction(client_id, message, response, intent)

        return response

    async def _detect_intent(self, message: str) -> str:
        """
        Определяет намерение клиента по сообщению
        """
        # Используем NLP или простые ключевые слова
        message_lower = message.lower()

        if any(word in message_lower for word in ['привет', 'здравствуй', 'добрый']):
            return 'greeting'
        elif any(word in message_lower for word in ['встреч', 'записаться', 'прийти']):
            return 'schedule_meeting'
        elif any(word in message_lower for word in ['статус', 'где заказ', 'готов']):
            return 'check_status'
        elif any(word in message_lower for word in ['помоги', 'как', 'что делать']):
            return 'help'
        elif any(word in message_lower for word in ['цена', 'стоит', 'прайс']):
            return 'pricing'
        elif any(word in message_lower for word in ['пока', 'до свидания']):
            return 'farewell'
        else:
            return 'general_question'

    async def _load_client_context(self, client_id: int) -> Dict[str, Any]:
        """
        Загружает всю информацию о клиенте для контекста
        """
        client = await self.db.get(Client, client_id)
        if not client:
            return {}

        # Получаем активные сделки
        deals_query = select(Deal).where(
            Deal.client_id == client_id
        ).order_by(Deal.created_at.desc()).limit(5)
        deals_result = await self.db.execute(deals_query)
        deals = deals_result.scalars().all()

        # Получаем последние взаимодействия
        interactions_query = select(Interaction).where(
            Interaction.client_id == client_id
        ).order_by(Interaction.created_at.desc()).limit(10)
        interactions_result = await self.db.execute(interactions_query)
        interactions = interactions_result.scalars().all()

        return {
            'client': client,
            'active_deals': [d for d in deals if not d.is_closed()],
            'recent_interactions': interactions,
            'total_deals_count': len(deals),
            'last_contact': interactions[0].created_at if interactions else None
        }

    async def _route_intent(
            self,
            intent: str,
            message: str,
            client_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Маршрутизирует запрос на основе намерения
        """
        if intent == 'greeting':
            return await self._handle_greeting(client_id)
        elif intent == 'schedule_meeting':
            return await self._handle_meeting_request(message, client_id)
        elif intent == 'check_status':
            return await self._handle_status_check(client_id)
        elif intent == 'help':
            return await self._handle_help()
        elif intent == 'pricing':
            return await self._handle_pricing()
        elif intent == 'farewell':
            return await self._handle_farewell()
        else:
            return await self._handle_general_question(message, client_id)

    async def _handle_greeting(self, client_id: Optional[int]) -> Dict[str, Any]:
        """Обработка приветствия"""
        if client_id and self.context.get('client'):
            client = self.context['client']
            name = client.first_name or client.full_name.split()[0]
            return {
                'message': f"👋 Здравствуйте, {name}! Рад вас видеть. Чем могу помочь сегодня?",
                'suggestions': [
                    'Проверить статус заказа',
                    'Записаться на встречу',
                    'Получить консультацию',
                    'Задать вопрос'
                ],
                'quick_replies': ['Статус', 'Встреча', 'Помощь']
            }
        else:
            return {
                'message': "👋 Здравствуйте! Я виртуальный ассистент CRM. Как я могу вам помочь?",
                'suggestions': [
                    'Представиться',
                    'Проверить статус',
                    'Записаться на встречу'
                ]
            }

    async def _handle_meeting_request(
            self,
            message: str,
            client_id: Optional[int]
    ) -> Dict[str, Any]:
        """Обработка запроса на встречу"""
        # Здесь будет логика с календарем
        return {
            'message': "📅 Конечно, я помогу вам записаться на встречу. Выберите удобное время:",
            'actions': [
                {
                    'type': 'date_picker',
                    'title': 'Выберите дату',
                    'min_date': datetime.now().strftime('%Y-%m-%d'),
                    'max_date': (datetime.now().replace(day=28) + timedelta(days=30)).strftime('%Y-%m-%d')
                }
            ],
            'suggestions': ['Сегодня', 'Завтра', 'На этой неделе', 'Следующая неделя']
        }

    async def _handle_status_check(self, client_id: Optional[int]) -> Dict[str, Any]:
        """Проверка статуса заказов/сделок"""
        if not client_id:
            return {
                'message': "Чтобы проверить статус, пожалуйста, авторизуйтесь или укажите номер заказа.",
                'suggestions': ['Авторизоваться', 'Ввести номер заказа']
            }

        deals = self.context.get('active_deals', [])
        if not deals:
            return {
                'message': "📭 У вас нет активных заказов в данный момент.",
                'suggestions': ['Посмотреть историю', 'Сделать заказ']
            }

        deals_info = []
        for deal in deals[:3]:
            deals_info.append(f"• {deal.name}: {deal.status.value} (вероятность {deal.probability}%)")

        deals_text = '\n'.join(deals_info)

        return {
            'message': f"📊 Ваши активные заказы:\n{deals_text}",
            'suggestions': ['Подробнее', 'Связаться с менеджером']
        }

    async def _handle_help(self) -> Dict[str, Any]:
        """Справка по возможностям"""
        return {
            'message': "🆘 Я могу помочь вам со следующими вопросами:",
            'suggestions': [
                '📅 Запись на встречу',
                '📊 Статус заказа',
                '💰 Информация о ценах',
                '📞 Связаться с менеджером',
                '❓ Часто задаваемые вопросы'
            ]
        }

    async def _handle_pricing(self) -> Dict[str, Any]:
        """Информация о ценах"""
        return {
            'message': "💰 Наши тарифы:\n• Базовый: 10,000 ₽/мес\n• Профессиональный: 25,000 ₽/мес\n• Корпоративный: индивидуально",
            'suggestions': ['Сравнить тарифы', 'Заказать звонок']
        }

    async def _handle_farewell(self) -> Dict[str, Any]:
        """Прощание"""
        return {
            'message': "👋 До свидания! Буду рад помочь снова. Хорошего дня! 🌟",
            'suggestions': ['Вернуться в меню', 'Задать вопрос']
        }

    async def _handle_general_question(
            self,
            message: str,
            client_id: Optional[int]
    ) -> Dict[str, Any]:
        """Общий вопрос - передаем в LLM"""
        # Здесь будет интеграция с OpenAI или другой LLM
        return {
            'message': "🤔 Дайте подумать... К сожалению, я еще учусь отвечать на такие вопросы. Могу предложить:",
            'suggestions': [
                'Связаться с менеджером',
                'Посмотреть FAQ',
                'Задать другой вопрос'
            ]
        }

    async def _save_interaction(
            self,
            client_id: int,
            user_message: str,
            assistant_response: Dict[str, Any],
            intent: str
    ):
        """Сохраняет взаимодействие в историю"""
        interaction = Interaction(
            client_id=client_id,
            type=InteractionType.MESSAGE,
            title=f"AI диалог: {intent}",
            description=user_message,
            result=assistant_response.get('message', ''),
            created_at=datetime.now()
        )
        self.db.add(interaction)
        await self.db.commit()