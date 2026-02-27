"""
Главный файл приложения FastAPI.
Инициализация и настройка всех компонентов.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db
from app.api.endpoints import clients, ai_assistant, notifications

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Выполняется при запуске и остановке.
    """
    # Startup: инициализируем базу данных
    print("🚀 Инициализация базы данных...")
    await init_db()

    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} запущен")
    print(f"📝 Документация: http://{settings.HOST}:{settings.PORT}/api/docs")
    print(f"🔧 Режим: {settings.ENVIRONMENT}")

    yield

    # Shutdown
    print("👋 Приложение остановлено")


# Создаем экземпляр FastAPI с lifespan
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc",  # ReDoc
)

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React
        "http://localhost:5173",  # Vite
        "http://localhost:8080",  # Vue
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(clients.router, prefix="/api/v1")
app.include_router(ai_assistant.router, prefix="/api/v1")
app.include_router(notifications.router)  # WebSocket роутер


@app.get("/")
async def root():
    """Корневой эндпоинт для проверки работы API."""
    return {
        "message": f"Добро пожаловать в {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/api/docs",
        "status": "работает"
    }


@app.get("/health")
async def health_check():
    """Эндпоинт для проверки здоровья сервиса."""
    return {
        "status": "healthy",
        "database": "connected",
        "ai_service": "disabled" if not settings.AI_ENABLED else "enabled"
    }


@app.get("/api/v1/test")
async def test_endpoint():
    """Тестовый эндпоинт для проверки работы API."""
    return {
        "message": "API работает корректно!",
        "timestamp": "2024-01-01T00:00:00Z"
    }