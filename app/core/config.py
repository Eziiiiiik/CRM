"""
Конфигурация приложения.
Загружает настройки из переменных окружения.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Загружаем .env файл (PyCharm автоматически подхватит)
load_dotenv()


class Settings(BaseSettings):
    """Класс с настройками приложения."""

    # Настройки приложения
    APP_NAME: str = "CRM System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development/production

    # Настройки сервера
    HOST: str = "127.0.0.1"  # localhost для разработки
    PORT: int = 8000

    # Настройки базы данных (используем SQLite для простоты старта)
    DATABASE_URL: str = "sqlite+aiosqlite:///./crm.db"
    # Для PostgreSQL (раскомментировать когда будет готов)
    # DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost/crm_db"

    # Настройки Redis для уведомлений
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False  # Отключаем Redis для начала

    # Настройки AI ассистента
    AI_API_URL: str = "http://localhost:8001"
    AI_API_KEY: str = "dev-ai-key-12345"
    AI_ENABLED: bool = False  # Можно отключить AI для тестирования

    # Настройки безопасности
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Пути к файлам
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    class Config:
        """Конфигурация Pydantic."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Возвращает экземпляр настроек с кэшированием.
    Использование lru_cache гарантирует, что настройки будут загружены только один раз.
    """
    return Settings()