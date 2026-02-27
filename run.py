# FastAPI и сервер
fastapi==0.104.1
uvicorn[standard]==0.24.0

# База данных
sqlalchemy==2.0.23
asyncpg==0.29.0  # для PostgreSQL
psycopg2-binary==2.9.9  # для совместимости (если нужно)

# Валидация и сериализация
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

# HTTP клиент для AI
httpx==0.25.1

# WebSocket и уведомления
websockets==12.0
redis==5.0.1

# Дополнительные утилиты
python-multipart==0.0.6  # для обработки форм
email-validator==2.1.0  # для валидации email