"""
Движок для автоматической сегментации клиентов
Вычисляет, подходит ли клиент под правила сегмента
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import operator

from app.models.client import Client
from app.models.deal import Deal
from app.models.interaction import Interaction
from app.models.enums import DealStatus
from app.models.segment import Segment, client_segments

logger = logging.getLogger(__name__)

class SegmentEngine:
    """Движок для вычисления принадлежности клиента к сегментам"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_client(self, client_id: int, rules: List[Dict[str, Any]]) -> bool:
        """
        Проверяет, соответствует ли клиент правилам сегмента

        Args:
            client_id: ID клиента
            rules: Список правил для проверки

        Returns:
            True если клиент подходит под все правила
        """
        if not rules:
            return False

        # Собираем все данные о клиенте
        client_data = await self._get_client_data(client_id)

        # Проверяем каждое правило
        for rule in rules:
            if not self._evaluate_rule(client_data, rule):
                return False

        return True

    async def _get_client_data(self, client_id: int) -> Dict[str, Any]:
        """
        Собирает все необходимые данные о клиенте для проверки правил
        """
        # Получаем клиента
        client = await self.db.get(Client, client_id)
        if not client:
            return {}

        # Получаем сделки клиента
        deals_query = select(Deal).where(Deal.client_id == client_id)
        deals_result = await self.db.execute(deals_query)
        deals = deals_result.scalars().all()

        # Получаем взаимодействия клиента
        interactions_query = select(Interaction).where(Interaction.client_id == client_id)
        interactions_result = await self.db.execute(interactions_query)
        interactions = interactions_result.scalars().all()

        # Вычисляем агрегированные данные
        total_deals_sum = sum(d.amount or 0 for d in deals)
        won_deals = [d for d in deals if d.status == DealStatus.WON]
        lost_deals = [d for d in deals if d.status == DealStatus.LOST]

        # Последнее взаимодействие
        last_interaction = max(interactions, key=lambda x: x.created_at) if interactions else None
        days_since_last_interaction = None
        if last_interaction and last_interaction.created_at:
            days_since_last_interaction = (datetime.now() - last_interaction.created_at).days

        # Дни с регистрации
        days_from_registration = None
        if client.created_at:
            days_from_registration = (datetime.now() - client.created_at).days

        # Город из первого адреса
        city = None
        if client.addresses and len(client.addresses) > 0:
            city = client.addresses[0].get("city")

        return {
            # Основные поля клиента
            "id": client.id,
            "last_name": client.last_name,
            "first_name": client.first_name,
            "email": client.email,
            "phone": client.phone,
            "company": client.company,
            "position": client.position,
            "industry": client.industry,
            "city": city,
            "gender": client.gender,
            "marital_status": client.marital_status,
            "source": client.source,
            "is_verified": client.is_verified,
            "birth_month": client.birth_date.month if client.birth_date else None,

            # Статистика по сделкам
            "total_deals_sum": total_deals_sum,
            "deals_count": len(deals),
            "won_deals_count": len(won_deals),
            "lost_deals_count": len(lost_deals),
            "avg_deal_amount": total_deals_sum / len(deals) if deals else 0,

            # Статистика по взаимодействиям
            "interactions_count": len(interactions),
            "calls_count": len([i for i in interactions if i.type == "call"]),
            "meetings_count": len([i for i in interactions if i.type == "meeting"]),
            "last_interaction_days": days_since_last_interaction,

            # Временные метки
            "days_from_registration": days_from_registration,
            "created_at": client.created_at,
        }

    def _evaluate_rule(self, client_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """
        Проверяет одно правило для клиента
        """
        field = rule.get("field")
        operator_str = rule.get("operator")
        expected_value = rule.get("value")

        if not field or not operator_str or expected_value is None:
            return False

        # Получаем фактическое значение поля у клиента
        actual_value = client_data.get(field)

        if actual_value is None:
            return False

        # Применяем оператор
        ops = {
            "equals": operator.eq,
            "not_equals": operator.ne,
            "greater_than": operator.gt,
            "less_than": operator.lt,
            "greater_than_or_equals": operator.ge,
            "less_than_or_equals": operator.le,
            "contains": lambda a, b: b in a if isinstance(a, str) else False,
            "not_contains": lambda a, b: b not in a if isinstance(a, str) else False,
            "in": lambda a, b: a in b if isinstance(b, list) else False,
            "not_in": lambda a, b: a not in b if isinstance(b, list) else False,
        }

        op_func = ops.get(operator_str)
        if not op_func:
            return False

        try:
            return op_func(actual_value, expected_value)
        except Exception:
            return False


class SegmentUpdater:
    """Класс для автоматического обновления сегментов"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = SegmentEngine(db)

    async def update_all_segments(self):
        """
        Обновляет все активные сегменты
        """
        # Получаем все сегменты
        query = select(Segment).where(Segment.is_active == True)
        result = await self.db.execute(query)
        segments = result.scalars().all()

        updated_count = 0
        for segment in segments:
            await self.update_segment(segment.id)
            updated_count += 1

        return {"updated_segments": updated_count}

    async def update_segment(self, segment_id: int):
        """
        Пересчитывает один сегмент
        """
        try:
            # Получаем сегмент
            segment = await self.db.get(Segment, segment_id)
            if not segment or not segment.is_active:
                return {"error": "Segment not found or inactive", "segment_id": segment_id}

            # Получаем всех клиентов
            clients_query = select(Client)
            clients_result = await self.db.execute(clients_query)
            clients = clients_result.scalars().all()

            # Проверяем каждого клиента
            matched_client_ids = []
            for client in clients:
                if await self.engine.evaluate_client(client.id, segment.rules):
                    matched_client_ids.append(client.id)

            # Обновляем связи в БД
            # Удаляем старые связи
            await self.db.execute(
                client_segments.delete().where(client_segments.c.segment_id == segment_id)
            )

            # Добавляем новые связи
            for client_id in matched_client_ids:
                await self.db.execute(
                    client_segments.insert().values(
                        segment_id=segment_id,
                        client_id=client_id
                    )
                )

            # Обновляем статистику сегмента
            segment.clients_count = len(matched_client_ids)
            segment.last_calculated_at = datetime.now()

            await self.db.commit()

            return {
                "segment_id": segment_id,
                "clients_count": len(matched_client_ids)
            }
        except Exception as e:
            # Логируем ошибку и пробрасываем дальше
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating segment {segment_id}: {e}")
            raise

    async def update_client_segments(self, client_id: int):
        """
        Обновляет все сегменты для конкретного клиента
        Вызывается после изменения данных клиента
        """
        # Получаем все активные сегменты
        query = select(Segment).where(Segment.is_active == True)
        result = await self.db.execute(query)
        segments = result.scalars().all()

        updated_segments = []
        for segment in segments:
            belongs = await self.engine.evaluate_client(client_id, segment.rules)

            # Проверяем, есть ли уже такая связь
            exists_query = select(client_segments).where(
                (client_segments.c.client_id == client_id) &
                (client_segments.c.segment_id == segment.id)
            )
            exists_result = await self.db.execute(exists_query)
            exists = exists_result.first() is not None

            if belongs and not exists:
                # Добавляем связь
                await self.db.execute(
                    client_segments.insert().values(
                        segment_id=segment.id,
                        client_id=client_id
                    )
                )
                segment.clients_count += 1
                updated_segments.append({"segment_id": segment.id, "action": "added"})

            elif not belongs and exists:
                # Удаляем связь
                await self.db.execute(
                    client_segments.delete().where(
                        (client_segments.c.client_id == client_id) &
                        (client_segments.c.segment_id == segment.id)
                    )
                )
                segment.clients_count -= 1
                updated_segments.append({"segment_id": segment.id, "action": "removed"})

        await self.db.commit()
        return {"updated_segments": updated_segments}