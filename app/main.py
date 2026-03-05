from fastapi_offline import FastAPIOffline as FastAPI
from app.api.endpoints import clients
from app.api.endpoints import clients, deals, dashboard, interactions
from app.core.database import init_db
from contextlib import asynccontextmanager
from app.api.endpoints import clients, deals
from app.api.endpoints import clients, deals, dashboard
from datetime import datetime
from fastapi.responses import HTMLResponse
from app.api.endpoints import clients, deals, dashboard, interactions, segments

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
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(interactions.router, prefix="/api/v1")
app.include_router(segments.router, prefix="/api/v1")

@app.get("/", response_class=HTMLResponse)
async def root_html():
    """Красивая главная страница"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CRM System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container {
                text-align: center;
                padding: 2rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                backdrop-filter: blur(10px);
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            h1 {
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            p {
                font-size: 1.2rem;
                margin-bottom: 2rem;
                opacity: 0.9;
            }
            .button {
                display: inline-block;
                padding: 1rem 2rem;
                margin: 0 0.5rem;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                transition: transform 0.3s;
            }
            .button:hover {
                transform: translateY(-2px);
            }
            .button.docs {
                background: transparent;
                border: 2px solid white;
                color: white;
            }
            .version {
                margin-top: 2rem;
                font-size: 0.9rem;
                opacity: 0.7;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 CRM System</h1>
            <p>Система управления взаимоотношениями с клиентами</p>
            <div>
                <a href="/docs" class="button">📚 Документация API</a>
                <a href="/api/v1/dashboard" class="button docs">📊 Дашборд</a>
            </div>
            <div class="version">
                Версия 1.0.0 | Разработано с ❤️ на FastAPI
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)