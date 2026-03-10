import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.client import Client
from app.models.deal import Deal

logger = logging.getLogger(__name__)


class SupportAIAssistant:
    """
    AI-ассистент для поддержки клиентов
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.knowledge_base = self._init_knowledge_base()

    @staticmethod
    def _init_knowledge_base() -> Dict[str, str]:
        """База знаний для частых вопросов (статический метод)"""
        return {
            "как зарегистрироваться": "Для регистрации нажмите кнопку 'Регистрация' в правом верхнем углу и заполните форму.",
            "как войти в систему": "Используйте кнопку 'Войти' и введите ваш email и пароль.",
            "забыл пароль": "На странице входа нажмите 'Забыли пароль?' и следуйте инструкциям.",
            "как пополнить баланс": "В личном кабинете выберите раздел 'Пополнение' и выберите удобный способ.",
            "как вывести средства": "В разделе 'Вывод средств' укажите сумму и реквизиты для вывода.",
            "как работает аналитика": "Аналитика показывает текущие тренды рынка, ваши активы и рекомендации.",
            "почему не приходит код": "Проверьте папку 'Спам' или запросите код повторно через 60 секунд.",
            "безопасно ли у вас": "Мы используем 256-битное шифрование и двухфакторную аутентификацию.",
            "как связаться с поддержкой": "Напишите 'оператор' и я подключу живого специалиста.",
            "сколько комиссия": "Комиссия составляет 0.1% за торговую операцию и 0% за пополнение.",
            "какие лимиты": "Минимальная сумма пополнения - 1000₽, максимальная - 5 000 000₽ в день.",
        }

    async def process_message(
            self,
            message: str,
            client_id: Optional[int] = None,
            session_id: str = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает сообщение от клиента
        """
        message_lower = message.lower().strip()

        # Проверяем запрос на оператора
        if self._wants_human(message_lower):
            return {
                "type": "human_requested",
                "message": "Соединяю вас с живым оператором. Пожалуйста, подождите...",
                "transfer_to_human": True,
                "session_id": session_id
            }

        # Проверяем приветствие
        if self._is_greeting(message_lower):
            return await self._handle_greeting(client_id, session_id)

        # Проверяем базу знаний
        for question, answer in self.knowledge_base.items():
            if question in message_lower:
                return {
                    "type": "answer",
                    "message": answer,
                    "suggestions": self._get_suggestions(message_lower),
                    "session_id": session_id
                }

        # Если клиент авторизован, проверяем его данные
        if client_id:
            if "статус" in message_lower or "где мой" in message_lower:
                return await self._handle_status_check(client_id, session_id)

        # Если ничего не нашли, предлагаем оператора
        return {
            "type": "unknown",
            "message": "Я не совсем понял ваш вопрос. Хотите поговорить с живым оператором?",
            "suggestions": ["Да, позовите оператора", "Задать другой вопрос", "Показать частые вопросы"],
            "session_id": session_id
        }

    @staticmethod
    def _wants_human(message: str) -> bool:
        """Проверяет, хочет ли клиент оператора (статический метод)"""
        keywords = ["оператор", "человек", "живой", "специалист", "помогите", "срочно"]
        return any(keyword in message for keyword in keywords)

    @staticmethod
    def _is_greeting(message: str) -> bool:
        """Проверяет приветствие (статический метод)"""
        greetings = ["привет", "здравствуй", "добрый", "хай", "hello", "hi"]
        return any(greet in message for greet in greetings)

    async def _handle_greeting(self, client_id: Optional[int], session_id: str) -> Dict[str, Any]:
        """Обрабатывает приветствие"""
        if client_id:
            client = await self.db.get(Client, client_id)
            if client:
                # Безопасное получение имени
                name = client.first_name
                if not name and hasattr(client, 'full_name'):
                    full_name = client.full_name
                    if isinstance(full_name, str):
                        name = full_name.split()[0]
                    else:
                        name = "Клиент"
                elif not name:
                    name = "Клиент"

                return {
                    "type": "greeting",
                    "message": f"Здравствуйте, {name}! Я AI-ассистент поддержки. Чем могу помочь?",
                    "suggestions": ["Статус заказа", "Пополнение", "Вывод", "Оператор"],
                    "session_id": session_id
                }

        return {
            "type": "greeting",
            "message": "Здравствуйте! Я AI-ассистент поддержки. Чем могу помочь?",
            "suggestions": ["Регистрация", "Вход", "Пополнение", "Оператор"],
            "session_id": session_id
        }

    async def _handle_status_check(self, client_id: int, session_id: str) -> Dict[str, Any]:
        """Проверяет статус заказов/сделок"""
        try:
            deals_query = select(Deal).where(Deal.client_id == client_id).order_by(Deal.created_at.desc()).limit(3)
            deals_result = await self.db.execute(deals_query)
            deals = deals_result.scalars().all()

            if not deals:
                return {
                    "type": "status",
                    "message": "У вас пока нет активных заказов.",
                    "suggestions": ["Сделать заказ", "Пополнить баланс", "Оператор"],
                    "session_id": session_id
                }

            deals_text = []
            for deal in deals:
                status_text = {
                    "new": "🆕 Новый",
                    "contact": "📞 Контакт",
                    "negotiation": "🤝 Переговоры",
                    "proposal": "📄 Предложение",
                    "contract": "📝 Договор",
                    "won": "✅ Завершён",
                    "lost": "❌ Отменён",
                    "postponed": "⏸ Отложен"
                }.get(deal.status.value if deal.status else "", deal.status.value if deal.status else "неизвестно")

                deals_text.append(f"• {deal.name}: {status_text} ({deal.amount} {deal.currency})")

            return {
                "type": "status",
                "message": "Ваши последние заказы:\n" + "\n".join(deals_text),
                "suggestions": ["Подробнее", "Пополнить", "Оператор"],
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Ошибка при проверке статуса: {e}")
            return {
                "type": "error",
                "message": "Не удалось получить статус заказов. Попробуйте позже.",
                "suggestions": ["Повторить", "Оператор"],
                "session_id": session_id
            }

    @staticmethod
    def _get_suggestions(message: str) -> List[str]:
        """Возвращает подсказки на основе сообщения (статический метод)"""
        message_lower = message.lower()
        if any(word in message_lower for word in ["пополнить", "баланс", "деньг"]):
            return ["Минимальная сумма", "Способы пополнения", "Комиссия"]
        elif any(word in message_lower for word in ["вывод", "снять"]):
            return ["Минимальная сумма", "Сроки вывода", "Реквизиты"]
        elif any(word in message_lower for word in ["регистрация", "аккаунт"]):
            return ["Как зарегистрироваться", "Подтверждение email", "Проблемы"]
        else:
            return ["Оператор", "Пополнение", "Вывод", "Статус"]