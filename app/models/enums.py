from enum import Enum


class DealStatus(str, Enum):
    """Статусы сделок в CRM"""
    NEW = "new"  # Новая сделка
    CONTACT = "contact"  # Установлен контакт
    NEGOTIATION = "negotiation"  # Переговоры
    PROPOSAL = "proposal"  # Отправлено предложение
    CONTRACT = "contract"  # Подписание договора
    WON = "won"  # Победа (успешно закрыта)
    LOST = "lost"  # Проигрыш (неуспешно закрыта)
    POSTPONED = "postponed"  # Отложена

    @classmethod
    def active_statuses(cls):
        """Активные статусы (ещё не закрытые сделки)"""
        return [cls.NEW, cls.CONTACT, cls.NEGOTIATION, cls.PROPOSAL, cls.CONTRACT]

    @classmethod
    def closed_statuses(cls):
        """Закрытые статусы"""
        return [cls.WON, cls.LOST, cls.POSTPONED]