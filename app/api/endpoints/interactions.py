from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.interaction import Interaction, InteractionType, InteractionStatus
from app.models.client import Client
from app.models.deal import Deal
from app.schemas.interaction import (
    InteractionCreate, InteractionUpdate, InteractionResponse,
    InteractionWithClientResponse
)

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/", response_model=List[InteractionWithClientResponse])
async def get_interactions(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        client_id: Optional[int] = Query(None, description="Фильтр по клиенту"),
        deal_id: Optional[int] = Query(None, description="Фильтр по сделке"),
        interaction_type: Optional[InteractionType] = Query(None, description="Тип взаимодействия"),  # переименовано
        interaction_status: Optional[InteractionStatus] = Query(None, description="Статус"),  # переименовано
        date_from: Optional[datetime] = Query(None, description="Начало периода"),
        date_to: Optional[datetime] = Query(None, description="Конец периода"),
        search: Optional[str] = Query(None, description="Поиск по заголовку и описанию"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить список взаимодействий с фильтрацией
    """
    query = select(Interaction).options(
        selectinload(Interaction.client),
        selectinload(Interaction.deal)
    )

    # Применяем фильтры
    filters = []
    if client_id:
        filters.append(Interaction.client_id == client_id)
    if deal_id:
        filters.append(Interaction.deal_id == deal_id)
    if interaction_type:  # ← используем новое имя
        filters.append(Interaction.type == interaction_type)
    if interaction_status:  # ← используем новое имя
        filters.append(Interaction.status == interaction_status)
    if client_id:
        filters.append(Interaction.client_id == client_id)
    if deal_id:
        filters.append(Interaction.deal_id == deal_id)
    if type:
        filters.append(Interaction.type == type)
    if status:
        filters.append(Interaction.status == status)
    if date_from:
        filters.append(Interaction.created_at >= date_from)
    if date_to:
        filters.append(Interaction.created_at <= date_to)
    if search:
        search_filter = or_(
            Interaction.title.ilike(f"%{search}%"),
            Interaction.description.ilike(f"%{search}%"),
            Interaction.result.ilike(f"%{search}%")
        )
        filters.append(search_filter)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(Interaction.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    interactions = result.scalars().all()

    # Добавляем информацию о клиенте и сделке
    response = []
    for i in interactions:
        interaction_dict = {
            **i.__dict__,
            'client_name': i.client.full_name if i.client else "Неизвестно",
            'client_email': i.client.email if i.client else "",
            'deal_name': i.deal.name if i.deal else None,
            'is_overdue': i.is_overdue
        }
        response.append(interaction_dict)

    return response


@router.get("/upcoming", response_model=List[InteractionResponse])
async def get_upcoming_interactions(
        days: int = Query(7, ge=1, le=30),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить предстоящие запланированные взаимодействия
    """
    now = datetime.now()
    end_date = now + timedelta(days=days)

    query = select(Interaction).where(
        and_(
            Interaction.status == InteractionStatus.PLANNED,
            Interaction.scheduled_at >= now,
            Interaction.scheduled_at <= end_date
        )
    ).order_by(Interaction.scheduled_at.asc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/overdue", response_model=List[InteractionResponse])
async def get_overdue_interactions(
        db: AsyncSession = Depends(get_db)
):
    """
    Получить просроченные запланированные взаимодействия
    """
    now = datetime.now()

    query = select(Interaction).where(
        and_(
            Interaction.status == InteractionStatus.PLANNED,
            Interaction.scheduled_at < now
        )
    ).order_by(Interaction.scheduled_at.asc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/today", response_model=List[InteractionResponse])
async def get_today_interactions(
        db: AsyncSession = Depends(get_db)
):
    """
    Получить взаимодействия на сегодня
    """
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    query = select(Interaction).where(
        and_(
            Interaction.scheduled_at >= start_of_day,
            Interaction.scheduled_at <= end_of_day
        )
    ).order_by(Interaction.scheduled_at.asc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{interaction_id}", response_model=InteractionWithClientResponse)
async def get_interaction(
        interaction_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о взаимодействии
    """
    query = select(Interaction).where(Interaction.id == interaction_id).options(
        selectinload(Interaction.client),
        selectinload(Interaction.deal)
    )
    result = await db.execute(query)
    interaction = result.scalar_one_or_none()

    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction with id {interaction_id} not found"
        )

    return interaction


@router.post("/", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
async def create_interaction(
        interaction_data: InteractionCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Создать новое взаимодействие
    """
    # Проверяем существование клиента
    client = await db.get(Client, interaction_data.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {interaction_data.client_id} not found"
        )

    # Проверяем существование сделки, если указана
    if interaction_data.deal_id:
        deal = await db.get(Deal, interaction_data.deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal with id {interaction_data.deal_id} not found"
            )
        # Проверяем, что сделка принадлежит тому же клиенту
        if deal.client_id != interaction_data.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deal does not belong to this client"
            )

    # Создаём взаимодействие
    interaction = Interaction(**interaction_data.model_dump())
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    return interaction


@router.put("/{interaction_id}", response_model=InteractionResponse)
async def update_interaction(
        interaction_id: int,
        interaction_data: InteractionUpdate,
        db: AsyncSession = Depends(get_db)
):
    """
    Обновить информацию о взаимодействии
    """
    interaction = await db.get(Interaction, interaction_id)
    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction with id {interaction_id} not found"
        )

    # Обновляем поля
    update_data = interaction_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(interaction, field, value)

    # Если указаны времена начала и окончания, вычисляем длительность
    if interaction.started_at and interaction.ended_at:
        delta = interaction.ended_at - interaction.started_at
        interaction.duration_minutes = int(delta.total_seconds() / 60)

    await db.commit()
    await db.refresh(interaction)
    return interaction


@router.delete("/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interaction(
        interaction_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Удалить взаимодействие
    """
    interaction = await db.get(Interaction, interaction_id)
    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction with id {interaction_id} not found"
        )

    await db.delete(interaction)
    await db.commit()


@router.post("/{interaction_id}/complete", response_model=InteractionResponse)
async def complete_interaction(
        interaction_id: int,
        result: str = Query(..., description="Результат взаимодействия"),
        db: AsyncSession = Depends(get_db)
):
    """
    Отметить взаимодействие как выполненное
    """
    interaction = await db.get(Interaction, interaction_id)
    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interaction with id {interaction_id} not found"
        )

    interaction.status = InteractionStatus.COMPLETED
    interaction.result = result
    interaction.ended_at = datetime.now()

    if interaction.started_at:
        delta = interaction.ended_at - interaction.started_at
        interaction.duration_minutes = int(delta.total_seconds() / 60)

    await db.commit()
    await db.refresh(interaction)
    return interaction