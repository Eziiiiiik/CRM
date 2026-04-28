import hashlib
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict

from fastapi import HTTPException

logger = logging.getLogger(__name__)

class SimpleCache:
    """Простой in-memory кэш с TTL и ограничением размера."""
    def __init__(self, maxsize=128, ttl_seconds=300):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl_seconds

    def _make_key(self, question: str, context: Optional[Dict]) -> str:
        data = {"q": question, "ctx": context or {}}
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def get(self, question: str, context: Optional[Dict]) -> Optional[Dict]:
        key = self._make_key(question, context)
        if key in self.cache:
            entry, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return entry
            else:
                del self.cache[key]
        return None

    def set(self, question: str, context: Optional[Dict], response: Dict):
        key = self._make_key(question, context)
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)
        self.cache[key] = (response, datetime.now())


class RateLimiter:
    """Простой rate limiter: не более N запросов в секунду для одного пользователя."""
    def __init__(self, requests_per_second: int = 5):
        self.rate = requests_per_second
        self.tokens = {}
        self.lock = asyncio.Lock()

    async def acquire(self, user_id: str) -> bool:
        async with self.lock:
            now = datetime.now()
            if user_id not in self.tokens:
                self.tokens[user_id] = (self.rate, now)
                return True
            tokens, last = self.tokens[user_id]
            elapsed = (now - last).total_seconds()
            tokens = min(self.rate, tokens + elapsed * self.rate)
            if tokens >= 1:
                self.tokens[user_id] = (tokens - 1, now)
                return True
            else:
                self.tokens[user_id] = (tokens, now)
                return False


class AIService:
    """
    Единый сервис для взаимодействия с AI.
    Заглушка – эхо с задержкой 1 сек, плюс кэширование и rate limit.
    """
    def __init__(self):
        self.cache = SimpleCache(maxsize=128, ttl_seconds=300)
        self.rate_limiter = RateLimiter(requests_per_second=2)  # 2 запроса в секунду на пользователя

    async def ask(
        self, question: str, context: Optional[Dict] = None, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Задать вопрос AI-ассистенту.
        Если user_id передан, применяется rate limiting.
        """
        if user_id:
            allowed = await self.rate_limiter.acquire(user_id)
            if not allowed:
                raise HTTPException(status_code=429, detail="Too many requests. Please wait.")

        # Проверяем кэш
        cached = self.cache.get(question, context)
        if cached:
            logger.info(f"AI cache hit for question: {question[:50]}")
            return cached

        # Имитация работы AI (замена на реальный httpx-запрос)
        logger.info(f"AI processing question: {question[:50]}")
        await asyncio.sleep(1)  # имитация задержки
        response = {
            "answer": f"AI ответ на: '{question}'. Контекст: {context}",
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat(),
        }

        # Сохраняем в кэш
        self.cache.set(question, context, response)
        return response

    async def analyze(self, data_type: str, data: Dict) -> Dict[str, Any]:
        """Аналитика (заглушка)."""
        await asyncio.sleep(0.5)
        return {
            "analysis": f"Проанализирован {data_type}",
            "summary": "Это тестовый анализ. Интегрируйте реальный AI.",
            "input_length": len(str(data)),
        }

    async def recommend(self, user_id: int, limit: int = 5) -> Dict[str, Any]:
        """Персональные рекомендации (заглушка)."""
        await asyncio.sleep(0.5)
        return {
            "user_id": user_id,
            "recommendations": [
                {"type": "product", "id": 1, "name": "Расширенная поддержка"},
                {"type": "service", "id": 2, "name": "Аналитический отчёт"},
            ],
            "limit": limit,
        }


# Глобальный экземпляр для использования в роутерах
ai_service = AIService()