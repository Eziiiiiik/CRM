"""
Настройки подключения к базе данных.
Используем SQLAlchemy с асинхронным драйвером.
Поддерживает SQLite (для разработки) и PostgreSQL (для продакшена).
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

# Определяем тип базы данных
if 'sqlite' in settings.DATABASE_URL:
    # Для SQLite нужны особые настройки
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,  # Логирование SQL запросов
        future=True,
        connect_args={"check_same_thread": False}  # Нужно для SQLite
    )
else:
    # Для PostgreSQL
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True
    )

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для моделей SQLAlchemy
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Зависимость для получения сессии базы данных.
    Используется в эндпоинтах FastAPI.
    Сессия автоматически закрывается после завершения запроса.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Инициализация базы данных (создание таблиц)."""
    async with engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)