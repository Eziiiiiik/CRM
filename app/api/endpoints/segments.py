from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.models.segment import Segment, client_segments
from app.models.client import Client
from app.schemas.segment import (
    SegmentCreate, SegmentUpdate, SegmentResponse,
    SegmentDetailResponse
)

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get("/", response_model=List[SegmentResponse])
async def get_segments(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех сегментов
    """
    query = select(Segment)

    if is_active is not None:
        query = query.where(Segment.is_active == is_active)

    query = query.offset(skip).limit(limit).order_by(Segment.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{segment_id}", response_model=SegmentDetailResponse)
async def get_segment(
        segment_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о сегменте
    """
    segment = await db.get(Segment, segment_id)
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment with id {segment_id} not found"
        )

    # Получаем несколько клиентов для примера
    query = select(Client).join(
        client_segments,
        Client.id == client_segments.c.client_id
    ).where(
        client_segments.c.segment_id == segment_id
    ).limit(5)

    result = await db.execute(query)
    sample_clients = result.scalars().all()

    # Преобразуем в словари
    sample_data = []
    for client in sample_clients:
        sample_data.append({
            "id": client.id,
            "full_name": client.full_name,
            "email": client.email,
            "company": client.company
        })

    # Добавляем в ответ
    response = {
        **segment.__dict__,
        "sample_clients": sample_data
    }

    return response


@router.post("/", response_model=SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
        segment_data: SegmentCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Создать новый сегмент
    """
    # Проверяем уникальность имени
    query = select(Segment).where(Segment.name == segment_data.name)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Segment with name '{segment_data.name}' already exists"
        )

    segment = Segment(**segment_data.model_dump())
    db.add(segment)
    await db.commit()
    await db.refresh(segment)
    return segment


@router.put("/{segment_id}", response_model=SegmentResponse)
async def update_segment(
        segment_id: int,
        segment_data: SegmentUpdate,
        db: AsyncSession = Depends(get_db)
):
    """
    Обновить сегмент
    """
    segment = await db.get(Segment, segment_id)
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment with id {segment_id} not found"
        )

    update_data = segment_data.model_dump(exclude_unset=True)

    # Если меняется имя, проверяем уникальность
    if "name" in update_data and update_data["name"] != segment.name:
        query = select(Segment).where(Segment.name == update_data["name"])
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Segment with name '{update_data['name']}' already exists"
            )

    for field, value in update_data.items():
        setattr(segment, field, value)

    await db.commit()
    await db.refresh(segment)
    return segment


@router.delete("/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
        segment_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Удалить сегмент
    """
    segment = await db.get(Segment, segment_id)
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment with id {segment_id} not found"
        )

    await db.delete(segment)
    await db.commit()


@router.get("/{segment_id}/clients")
async def get_segment_clients(
        segment_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить клиентов в сегменте
    """
    segment = await db.get(Segment, segment_id)
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment with id {segment_id} not found"
        )

    query = select(Client).join(
        client_segments,
        Client.id == client_segments.c.client_id
    ).where(
        client_segments.c.segment_id == segment_id
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    clients = result.scalars().all()

    return [
        {
            "id": c.id,
            "full_name": c.full_name,
            "email": c.email,
            "phone": c.phone,
            "company": c.company,
            "created_at": c.created_at
        }
        for c in clients
    ]

@router.post("/refresh-all")
async def refresh_all_segments(
        db: AsyncSession = Depends(get_db)
):
    """
    Запустить пересчёт всех активных сегментов
    """
    from app.core.segment_engine import SegmentUpdater

    updater = SegmentUpdater(db)
    result = await updater.update_all_segments()

    return {
        "message": "Segments refresh completed",
        "updated_segments": result["updated_segments"],
        "timestamp": datetime.now().isoformat()
    }


@router.post("/{segment_id}/refresh")
async def refresh_segment(
        segment_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Пересчитать конкретный сегмент
    """
    from app.core.segment_engine import SegmentUpdater

    updater = SegmentUpdater(db)
    result = await updater.update_segment(segment_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    return {
        "message": "Segment refresh completed",
        "data": result,
        "timestamp": datetime.now().isoformat()
    }