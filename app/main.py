from fastapi_offline import FastAPIOffline as FastAPI
from contextlib import asynccontextmanager
from app.ai.routers.chat import router as chat_router
from app.ai.routers.meetings import router as meetings_router
import asyncio
import logging
from app.api.endpoints import news
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints import clients, deals, dashboard, interactions, segments


from frontend.main import router as frontend_router
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import clients, deals, dashboard, interactions, segments
from app.core.database import init_db, AsyncSessionLocal
from app.core.segment_engine import SegmentUpdater

logger = logging.getLogger(__name__)


async def update_segments_periodically(shutdown_event: asyncio.Event):
    """Запускает обновление сегментов каждый час"""
    while not shutdown_event.is_set():
        try:
            logger.info("🔄 Запуск автоматического обновления сегментов...")

            async with AsyncSessionLocal() as db:
                updater = SegmentUpdater(db)
                result = await updater.update_all_segments()
                logger.info(f"✅ Обновлено {result['updated_segments']} сегментов")

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении сегментов: {e}")
            import traceback
            logger.error(traceback.format_exc())

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break

    logger.info("🛑 Фоновая задача обновления сегментов остановлена")


@asynccontextmanager
async def lifespan(_app):
    print("🚀 Создаем таблицы в БД...")
    await init_db()
    print("✅ База данных готова")

    shutdown_event = asyncio.Event()
    task = asyncio.create_task(update_segments_periodically(shutdown_event))
    print("🔄 Фоновая задача обновления сегментов запущена")

    try:
        yield
    finally:
        print("🛑 Останавливаем фоновую задачу...")
        shutdown_event.set()

        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            print("⚠️ Фоновая задача не завершилась вовремя, принудительно отменяем")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        except Exception as e:
            print(f"⚠️ Ошибка при остановке фоновой задачи: {e}")

        print("👋 Приложение остановлено")


app = FastAPI(
    title="CRM System",
    version="1.0.0",
    lifespan=lifespan
)

# Подключаем статические файлы фронтенда
BASE_DIR = Path(__file__).parent.parent  # поднимаемся на уровень выше
STATIC_DIR = BASE_DIR / "frontend" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


app.include_router(frontend_router)
print("Frontend router included")

print("Все маршруты:")
for route in app.routes:
    print(route.path)

app.include_router(news.router, prefix="/api/v1")

# Подключаем API роутеры
app.include_router(clients.router, prefix="/api/v1")
app.include_router(deals.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(interactions.router, prefix="/api/v1")
app.include_router(segments.router, prefix="/api/v1")

# Подключаем AI роутеры
app.include_router(chat_router, prefix="/api/v1/ai")
app.include_router(meetings_router, prefix="/api/v1/ai")

app.include_router(auth_router, prefix="/api/v1")