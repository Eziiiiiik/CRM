"""
Скрипт для запуска приложения в режиме разработки.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8001,  # ← измени здесь!
        reload=True
    )