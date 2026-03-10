import uvicorn
from frontend.main import router as frontend_router

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 CRM System запускается...")
    print("=" * 50)
    print("🌐 Главная страница: http://127.0.0.1:8001")
    print("📚 Документация API: http://127.0.0.1:8001/docs")
    print("📊 Дашборд: http://127.0.0.1:8001/api/v1/dashboard")
    print("=" * 50)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        log_level="info"
    )