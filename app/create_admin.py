import asyncio
import sqlite3
from app.core.database import AsyncSessionLocal
from sqlalchemy import text


async def add_column():
    # 1. Добавляем колонку через прямое SQL-соединение (не асинхронно)
    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()

    # Проверяем, существует ли колонка
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'is_admin' not in columns:
        print("➕ Добавляем колонку is_admin в таблицу users...")
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        conn.commit()
        print("✅ Колонка добавлена")
    else:
        print("✅ Колонка is_admin уже существует")

    conn.close()

    # 2. Создаём администратора, если его нет
    async with AsyncSessionLocal() as db:
        from app.models.user import User
        from app.api.endpoints.auth import get_password_hash

        result = await db.execute(text("SELECT * FROM users WHERE email = 'admin@example.com'"))
        admin = result.fetchone()

        if not admin:
            print("👤 Создаём администратора...")
            hashed = get_password_hash("admin123")
            await db.execute(
                text(
                    "INSERT INTO users (username, email, hashed_password, is_active, is_admin) VALUES ('admin', 'admin@example.com', :pwd, 1, 1)"),
                {"pwd": hashed}
            )
            await db.commit()
            print("✅ Администратор создан (логин: admin@example.com / пароль: admin123)")
        else:
            print("✅ Администратор уже существует")


if __name__ == "__main__":
    asyncio.run(add_column())