from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.client import Client, Tag
from app.models.deal import Deal
from app.models.interaction import Interaction
from app.models.user import User
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse,
    ClientDetailResponse, TagCreate, TagResponse
)
from app.core.segment_engine import SegmentUpdater
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/clients", tags=["clients"])


# ========== Эндпоинты для клиентов ==========

@router.get("/", response_model=List[ClientResponse])
async def get_clients(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        search: Optional[str] = Query(None, description="Поиск по имени, email, телефону"),
        tag: Optional[str] = Query(None, description="Фильтр по тегу"),
        is_active: Optional[bool] = Query(None, description="Фильтр по статусу"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить список клиентов с расширенной фильтрацией
    """
    query = select(Client).options(selectinload(Client.tags))

    if search:
        search_filter = or_(
            Client.last_name.ilike(f"%{search}%"),
            Client.first_name.ilike(f"%{search}%"),
            Client.email.ilike(f"%{search}%"),
            Client.phone.ilike(f"%{search}%"),
            Client.company.ilike(f"%{search}%")
        )
        query = query.where(search_filter)

    if tag:
        query = query.join(Client.tags).where(Tag.name == tag)

    if is_active is not None:
        query = query.where(Client.is_active == is_active)

    query = query.offset(skip).limit(limit).order_by(Client.created_at.desc())
    result = await db.execute(query)
    clients = result.scalars().all()
    return clients


@router.get("/stats", response_model=dict)
async def get_clients_stats(
        db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику по клиентам
    """
    result = await db.execute(select(Client))
    clients = result.scalars().all()

    total = len(clients)
    active = sum(1 for c in clients if c.is_active)
    verified = sum(1 for c in clients if c.is_verified)

    male = sum(1 for c in clients if c.gender == "male")
    female = sum(1 for c in clients if c.gender == "female")

    sources = {}
    for c in clients:
        if c.source:
            sources[c.source] = sources.get(c.source, 0) + 1

    return {
        "total_clients": total,
        "active_clients": active,
        "verified_clients": verified,
        "by_gender": {"male": male, "female": female, "other": total - male - female},
        "by_source": sources
    }


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(
        client_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о клиенте (со сделками)
    """
    query = select(Client).where(Client.id == client_id).options(
        selectinload(Client.tags),
        selectinload(Client.deals)
    )
    result = await db.execute(query)
    client = result.scalar_one_or_none()

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
    Создать нового клиента
    """
    query = select(Client).where(Client.email == client_data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client with this email already exists"
        )

    client = Client(**client_data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)

    updater = SegmentUpdater(db)
    await updater.update_client_segments(client.id)

    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
        client_id: int,
        client_data: ClientUpdate,
        db: AsyncSession = Depends(get_db)
):
    """
    Обновить информацию о клиенте
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )

    update_data = client_data.model_dump(exclude_unset=True)

    for field in ['messengers', 'social_networks', 'addresses', 'communication_preferences']:
        if field in update_data and update_data[field] is not None:
            setattr(client, field, update_data[field])

    for field, value in update_data.items():
        if field not in ['messengers', 'social_networks', 'addresses', 'communication_preferences']:
            setattr(client, field, value)

    await db.commit()
    await db.refresh(client)

    updater = SegmentUpdater(db)
    await updater.update_client_segments(client.id)

    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
        client_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Удалить клиента (мягкое удаление - деактивация)
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )

    client.is_active = False
    await db.commit()

    updater = SegmentUpdater(db)
    await updater.update_client_segments(client.id)


@router.post("/{client_id}/restore", response_model=ClientResponse)
async def restore_client(
        client_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Восстановить удалённого клиента
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {client_id} not found"
        )

    client.is_active = True
    await db.commit()
    await db.refresh(client)
    return client


# ========== Эндпоинты для тегов ==========

@router.get("/tags", response_model=List[TagResponse])
async def get_tags(
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    """Получить список всех тегов"""
    query = select(Tag).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/tags", response_model=TagResponse)
async def create_tag(
        tag_data: TagCreate,
        db: AsyncSession = Depends(get_db)
):
    """Создать новый тег"""
    tag = Tag(**tag_data.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.post("/{client_id}/tags/{tag_id}")
async def add_tag_to_client(
        client_id: int,
        tag_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Добавить тег клиенту"""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if tag not in client.tags:
        client.tags.append(tag)
        await db.commit()

    return {"message": "Tag added"}


@router.delete("/{client_id}/tags/{tag_id}")
async def remove_tag_from_client(
        client_id: int,
        tag_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Удалить тег у клиента"""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if tag in client.tags:
        client.tags.remove(tag)
        await db.commit()

    return {"message": "Tag removed"}


# ========== Эндпоинты для личного кабинета ==========

@router.get("/me", response_model=ClientResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Client).where(Client.email == current_user.email))
    client = result.scalar_one_or_none()
    if not client:
        # автоматически создаём клиента при первом входе
        client = Client(
            email=current_user.email,
            first_name=current_user.username,
            last_name=""
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)
    return client

@router.put("/me", response_model=ClientResponse)
async def update_my_profile(
    client_data: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Client).where(Client.email == current_user.email))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Client not found")
    for field, value in client_data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.commit()
    await db.refresh(client)
    return client

@router.get("/my/deals")
async def get_my_deals(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Получить сделки текущего клиента"""
    result = await db.execute(select(Client).where(Client.email == current_user.email))
    client = result.scalar_one_or_none()

    if not client:
        return {"deals": []}

    deals_result = await db.execute(
        select(Deal).where(Deal.client_id == client.id).order_by(Deal.created_at.desc())
    )
    deals = deals_result.scalars().all()

    return {
        "client": {
            "id": client.id,
            "full_name": client.full_name,
            "email": client.email,
            "phone": client.phone,
            "company": client.company
        },
        "deals": [
            {
                "id": d.id,
                "name": d.name,
                "amount": d.amount,
                "currency": d.currency,
                "status": d.status.value,
                "probability": d.probability,
                "created_at": d.created_at,
                "expected_close_date": d.expected_close_date
            }
            for d in deals
        ],
        "stats": {
            "total_deals": len(deals),
            "active_deals": len([d for d in deals if d.is_active()]),
            "won_deals": len([d for d in deals if d.status.value == "won"]),
            "total_amount": sum(d.amount for d in deals)
        }
    }


@router.get("/my/interactions")
async def get_my_interactions(
        limit: int = 20,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Получить историю взаимодействий текущего клиента"""
    result = await db.execute(select(Client).where(Client.email == current_user.email))
    client = result.scalar_one_or_none()

    if not client:
        return {"interactions": []}

    interactions_result = await db.execute(
        select(Interaction)
        .where(Interaction.client_id == client.id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    interactions = interactions_result.scalars().all()

    return [
        {
            "id": i.id,
            "type": i.type,
            "title": i.title,
            "description": i.description,
            "created_at": i.created_at,
            "status": i.status
        }
        for i in interactions
    ]


@router.put("/my")
async def update_my_profile(
        client_data: ClientUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Обновить профиль текущего клиента"""
    result = await db.execute(select(Client).where(Client.email == current_user.email))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)

    return {"message": "Profile updated", "client_id": client.id}