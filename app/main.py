from fastapi_offline import FastAPIOffline as FastAPI
from app.api.endpoints import clients
from app.core.database import init_db
from contextlib import asynccontextmanager
from app.api.endpoints import clients, deals

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: создаем таблицы
    print("🚀 Создаем таблицы в БД...")
    await init_db()
    print("✅ База данных готова")
    yield
    # Shutdown
    print("👋 Приложение остановлено")

app = FastAPI(
    title="CRM System",
    version="1.0.0",
    lifespan=lifespan
)

# Подключаем роутер клиентов
app.include_router(clients.router, prefix="/api/v1")
app.include_router(deals.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "CRM System работает!"}