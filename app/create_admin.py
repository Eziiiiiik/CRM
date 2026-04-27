import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.api.endpoints.auth import get_password_hash


async def create_admin():
    async with AsyncSessionLocal() as db:
        # Проверяем, нет ли уже админа
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "admin@example.com"))
        existing = result.scalar_one_or_none()
        if existing:
            print("Admin already exists")
            return

        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_admin=True
        )
        db.add(admin)
        await db.commit()
        print("Admin created: admin@example.com / admin123")


if __name__ == "__main__":
    asyncio.run(create_admin())