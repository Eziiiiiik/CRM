"""
Эндпоинты для работы с клиентами.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.core.notifications import manager

# Создаем роутер с префиксом /api/v1/clients
router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=List[ClientResponse])
async def get_clients(
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех клиентов.

    - **skip**: количество пропускаемых записей (для пагинации)
    - **limit**: максимальное количество записей
    """
    # Создаем запрос к базе данных
    query = select(Client).offset(skip).limit(limit)
    result = await db.execute(query)
    clients = result.scalars().all()
    return clients


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
        client_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о конкретном клиенте по ID.
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )
    return client


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
        client_data: ClientCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Создать нового клиента.
    """
    # Проверяем, не существует ли уже клиент с таким email
    query = select(Client).where(Client.email == client_data.email)
    result = await db.execute(query)
    existing_client = result.scalar_one_or_none()

    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client with this email already exists"
        )

    # Создаем нового клиента
    client = Client(**client_data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)

    # Отправляем уведомление о создании клиента
    await manager.publish_notification(
        "clients",
        {"type": "client_created", "data": {"id": client.id, "email": client.email}}
    )

    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
        client_id: int,
        client_data: ClientUpdate,
        db: AsyncSession = Depends(get_db)
):
    """
    Обновить информацию о клиенте.
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )

    # Обновляем только переданные поля
    update_data = client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)

    # Отправляем уведомление
    await manager.publish_notification(
        f"user:{client_id}",
        {"type": "client_updated", "data": update_data}
    )

    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
        client_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Удалить клиента (мягкое удаление - деактивация).
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )

    # Мягкое удаление - просто деактивируем
    client.is_active = False
    await db.commit()

    await manager.publish_notification(
        "clients",
        {"type": "client_deleted", "data": {"id": client_id}}
    )