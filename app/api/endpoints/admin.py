from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.client import Client
from app.models.deal import Deal
from app.models.user import User
from app.schemas.client import ClientResponse
from app.schemas.deal import DealResponse
from app.schemas.user import UserResponse, UserCreate
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


# ========== Проверка прав администратора ==========

async def check_admin(current_user: User = Depends(get_current_user)):
    """Проверка, что пользователь — администратор"""
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ========== Статистика для админки ==========

@router.get("/stats")
async def get_admin_stats(
        _admin: User = Depends(check_admin),  # _admin показывает, что параметр не используется
        db: AsyncSession = Depends(get_db)
):
    """Получить общую статистику для админ-панели"""

    total_clients = await db.scalar(select(func.count()).select_from(Client)) or 0
    total_deals = await db.scalar(select(func.count()).select_from(Deal)) or 0
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    total_amount = await db.scalar(select(func.sum(Deal.amount))) or 0

    today = datetime.now().date()
    new_clients_today = await db.scalar(
        select(func.count()).select_from(Client).where(
            func.date(Client.created_at) == today
        )
    ) or 0

    return {
        "total_clients": total_clients,
        "total_deals": total_deals,
        "total_users": total_users,
        "total_amount": float(total_amount),
        "new_clients_today": new_clients_today
    }


# ========== Управление клиентами (CRUD) ==========

@router.get("/clients", response_model=List[ClientResponse])
async def admin_get_clients(
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Получить список всех клиентов (админ-доступ)"""
    query = select(Client)

    if search:
        query = query.where(
            (Client.last_name.ilike(f"%{search}%")) |
            (Client.first_name.ilike(f"%{search}%")) |
            (Client.email.ilike(f"%{search}%"))
        )

    query = query.order_by(desc(Client.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/clients/{client_id}")
async def admin_delete_client(
        client_id: int,
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Удалить клиента (полностью)"""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await db.delete(client)
    await db.commit()
    return {"message": "Client deleted"}


# ========== Управление сделками ==========

@router.get("/deals", response_model=List[DealResponse])
async def admin_get_deals(
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,  # переименовано, чтобы не затенять status
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Получить список всех сделок (админ-доступ)"""
    query = select(Deal)

    if status_filter:
        query = query.where(Deal.status == status_filter)

    query = query.order_by(desc(Deal.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/deals/{deal_id}/status")
async def admin_update_deal_status(
        deal_id: int,
        new_status: str,  # переименовано, чтобы не затенять status
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Обновить статус сделки"""
    from app.models.enums import DealStatus

    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    deal.status = DealStatus(new_status)
    await db.commit()
    return {"message": "Status updated"}


# ========== Управление пользователями ==========

@router.get("/users", response_model=List[UserResponse])
async def admin_get_users(
        skip: int = 0,
        limit: int = 50,
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Получить список всех пользователей"""
    query = select(User).order_by(desc(User.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/users", response_model=UserResponse)
async def admin_create_user(
        user_data: UserCreate,
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Создать нового пользователя (админ)"""
    from app.api.endpoints.auth import get_password_hash

    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def admin_delete_user(
        user_id: int,
        admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Удалить пользователя"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


# ========== Модерирование ==========

@router.get("/pending-deals")
async def get_pending_deals(
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Сделки, требующие внимания"""
    from app.models.enums import DealStatus

    query = select(Deal).options(selectinload(Deal.client)).where(
        Deal.status.in_([DealStatus.PROPOSAL, DealStatus.CONTRACT])
    ).order_by(Deal.expected_close_date)

    result = await db.execute(query)
    deals = result.scalars().all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "client_name": d.client.full_name if d.client else "Unknown",
            "amount": d.amount,
            "status": d.status.value,
            "expected_close_date": d.expected_close_date
        }
        for d in deals
    ]


# ========== Экспорт данных ==========

@router.get("/export/clients")
async def export_clients_csv(
        _admin: User = Depends(check_admin),
        db: AsyncSession = Depends(get_db)
):
    """Экспорт клиентов в CSV"""
    import csv
    from io import StringIO
    from fastapi.responses import Response

    result = await db.execute(select(Client))
    clients = result.scalars().all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "ФИО", "Email", "Телефон", "Компания", "Создан"])

    for c in clients:
        writer.writerow([
            c.id,
            c.full_name,
            c.email,
            c.phone or "",
            c.company or "",
            c.created_at.strftime("%Y-%m-%d") if c.created_at else ""
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clients.csv"}
    )