from fastapi_offline import FastAPIOffline as FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from contextlib import asynccontextmanager
from sqlalchemy import select
from pathlib import Path
import asyncio
import logging

# Ваши существующие импорты API
from app.ai.routers.chat import router as chat_router
from app.ai.routers.meetings import router as meetings_router
from app.api.endpoints import news
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints import clients, deals, dashboard, interactions, segments
from app.core.database import init_db, AsyncSessionLocal
from app.core.segment_engine import SegmentUpdater
from app.models.user import User

# Функция чтения HTML (убедитесь, что путь корректный)
from frontend.main import read_html

logger = logging.getLogger(__name__)

# ... (весь код lifespan и периодического обновления сегментов остаётся без изменений)

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

# ===== СТАТИЧЕСКИЕ ФАЙЛЫ =====
BASE_DIR = Path(__file__).parent.parent  # на уровень выше папки backend
STATIC_DIR = BASE_DIR / "frontend" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ===== ФРОНТЕНД-РОУТЕР (отдаёт HTML-страницы) =====
frontend_router = APIRouter(prefix="", tags=["frontend"])

@frontend_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return HTMLResponse(content=read_html("index.html"))

@frontend_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return HTMLResponse(content=read_html("dashboard.html"))

@frontend_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return HTMLResponse(content=read_html("login.html"))

@frontend_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return HTMLResponse(content=read_html("register.html"))

@frontend_router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return HTMLResponse(content=read_html("profile.html"))

@frontend_router.get("/news", response_class=HTMLResponse)
async def news_page(request: Request):
    return HTMLResponse(content=read_html("news.html"))

@frontend_router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return HTMLResponse(content=read_html("chat.html"))

@frontend_router.get("/clients", response_class=HTMLResponse)
async def clients_page(request: Request):
    return HTMLResponse(content=read_html("clients.html"))

@frontend_router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Админ-панель с проверкой существования администратора"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.is_admin == True))
        admin_exists = result.scalar_one_or_none() is not None
    if not admin_exists:
        return RedirectResponse(url="/admin/setup", status_code=303)
    return HTMLResponse(content=read_html("admin/index.html"))

# ===== WEBSOCKET ДЛЯ УВЕДОМЛЕНИЙ =====
@app.websocket("/ws/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: int):
    await websocket.accept()
    logger.info(f"WebSocket подключён для user_id={user_id}")
    try:
        while True:
            # В реальном приложении здесь будет логика отправки уведомлений по мере их появления.
            # Пока просто держим соединение открытым.
            data = await websocket.receive_text()
            # Можно обрабатывать входящие сообщения от клиента, если нужно
            await websocket.send_text(f"Эхо: {data}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket отключён для user_id={user_id}")
    except Exception as e:
        logger.error(f"Ошибка WebSocket: {e}")

# ===== ПОДКЛЮЧЕНИЕ РОУТЕРОВ =====
app.include_router(frontend_router)                     # фронтенд-страницы
app.include_router(auth_router, prefix="/api/v1")       # авторизация
app.include_router(news.router, prefix="/api/v1")       # новости
app.include_router(clients.router, prefix="/api/v1")    # клиенты (CRUD)
app.include_router(deals.router, prefix="/api/v1")      # сделки
app.include_router(dashboard.router, prefix="/api/v1")  # дашборд
app.include_router(interactions.router, prefix="/api/v1") # взаимодействия
app.include_router(segments.router, prefix="/api/v1")   # сегменты
app.include_router(chat_router, prefix="/api/v1/ai")    # AI-чат
app.include_router(meetings_router, prefix="/api/v1/ai")# AI-встречи