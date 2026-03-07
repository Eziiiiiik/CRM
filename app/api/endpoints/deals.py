from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.models.deal import Deal
from app.models.client import Client
from app.models.enums import DealStatus
from app.schemas.deal import (
    DealCreate, DealUpdate, DealResponse,
    DealWithClientResponse, DealClose
)
from app.core.segment_engine import SegmentUpdater  # импорт вынесен наверх

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("/", response_model=List[DealResponse])
async def get_deals(
        skip: int = Query(0, ge=0, description="Сколько пропустить"),
        limit: int = Query(100, ge=1, le=1000, description="Сколько вернуть"),
        status_param: Optional[DealStatus] = Query(None, description="Фильтр по статусу"),  # переименовано
        client_id: Optional[int] = Query(None, description="Фильтр по клиенту"),
        min_amount: Optional[float] = Query(None, ge=0, description="Минимальная сумма"),
        max_amount: Optional[float] = Query(None, ge=0, description="Максимальная сумма"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить список сделок с возможностью фильтрации
    """
    query = select(Deal).options(selectinload(Deal.client))

    # Применяем фильтры
    filters = []
    if status_param:  # используем новое имя
        filters.append(Deal.status == status_param)
    if client_id:
        filters.append(Deal.client_id == client_id)
    if min_amount is not None:
        filters.append(Deal.amount >= min_amount)
    if max_amount is not None:
        filters.append(Deal.amount <= max_amount)

    if filters:
        query = query.where(and_(*filters))

    # Сортировка (сначала новые)
    query = query.order_by(Deal.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    deals = result.scalars().all()

    # Добавляем информацию о клиенте
    response = []
    for deal in deals:
        deal_dict = {
            **deal.__dict__,
            'client_name': deal.client.full_name if deal.client else None,
            'client_email': deal.client.email if deal.client else None
        }
        response.append(deal_dict)

    return response


@router.get("/stats", response_model=dict)
async def get_deals_stats(
        db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику по сделкам
    """
    # Получаем все сделки
    result = await db.execute(select(Deal))
    deals = result.scalars().all()

    # Считаем статистику
    total_count = len(deals)
    active_count = sum(1 for d in deals if d.is_active())
    closed_count = sum(1 for d in deals if d.is_closed())

    # Суммы по статусам
    total_amount = sum(d.amount for d in deals)
    won_amount = sum(d.amount for d in deals if d.status == DealStatus.WON)

    # Статистика по статусам
    status_stats = {}
    for deal_status in DealStatus:  # переименовано, чтобы не затенять
        count = sum(1 for d in deals if d.status == deal_status)
        amount = sum(d.amount for d in deals if d.status == deal_status)
        if count > 0:
            status_stats[deal_status.value] = {
                "count": count,
                "amount": amount
            }

    return {
        "total_deals": total_count,
        "active_deals": active_count,
        "closed_deals": closed_count,
        "total_amount": total_amount,
        "won_amount": won_amount,
        "by_status": status_stats
    }


@router.get("/{deal_id}", response_model=DealWithClientResponse)
async def get_deal(
        deal_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о сделке
    """
    query = select(Deal).where(Deal.id == deal_id).options(selectinload(Deal.client))
    result = await db.execute(query)
    deal = result.scalar_one_or_none()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal with id {deal_id} not found"
        )

    return deal


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
        deal_data: DealCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Создать новую сделку
    """
    # Проверяем, существует ли клиент
    client = await db.get(Client, deal_data.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {deal_data.client_id} not found"
        )

    # Создаем сделку
    deal = Deal(**deal_data.model_dump())
    db.add(deal)
    await db.commit()
    await db.refresh(deal)

    # Обновляем сегменты клиента (ПЕРЕД return)
    updater = SegmentUpdater(db)
    await updater.update_client_segments(client.id)

    return deal


@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(
        deal_id: int,
        deal_data: DealUpdate,
        db: AsyncSession = Depends(get_db)
):
    """
    Обновить информацию о сделке
    """
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal with id {deal_id} not found"
        )

    # Получаем клиента для обновления сегментов
    client = await db.get(Client, deal.client_id)

    # Обновляем поля
    update_data = deal_data.model_dump(exclude_unset=True)

    # Если меняем статус на закрывающий, обновляем дату закрытия
    if 'status' in update_data:
        new_status = update_data['status']
        if new_status in DealStatus.closed_statuses() and deal.status not in DealStatus.closed_statuses():
            update_data['actual_close_date'] = datetime.now()
        elif new_status not in DealStatus.closed_statuses() and deal.status in DealStatus.closed_statuses():
            # Если возвращаем из закрытого в активный, очищаем дату закрытия
            update_data['actual_close_date'] = None

    for field, value in update_data.items():
        setattr(deal, field, value)

    await db.commit()
    await db.refresh(deal)

    # Обновляем сегменты клиента (ПЕРЕД return)
    if client:
        updater = SegmentUpdater(db)
        await updater.update_client_segments(client.id)

    return deal


@router.post("/{deal_id}/close", response_model=DealResponse)
async def close_deal(
        deal_id: int,
        close_data: DealClose,
        db: AsyncSession = Depends(get_db)
):
    """
    Закрыть сделку (won/lost/postponed)
    """
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal with id {deal_id} not found"
        )

    # Проверяем, не закрыта ли уже сделка
    if deal.is_closed():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deal is already closed with status {deal.status}"
        )

    # Получаем клиента для обновления сегментов
    client = await db.get(Client, deal.client_id)

    # Обновляем статус и дату закрытия
    deal.status = close_data.status
    deal.close_reason = close_data.close_reason
    deal.actual_close_date = close_data.actual_close_date

    await db.commit()
    await db.refresh(deal)

    # Обновляем сегменты клиента (ПЕРЕД return)
    if client:
        updater = SegmentUpdater(db)
        await updater.update_client_segments(client.id)

    return deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
        deal_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Удалить сделку (полное удаление)
    """
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal with id {deal_id} not found"
        )

    # Получаем клиента для обновления сегментов ДО удаления
    client = await db.get(Client, deal.client_id)

    await db.delete(deal)
    await db.commit()

    # Обновляем сегменты клиента ПОСЛЕ удаления
    if client:
        updater = SegmentUpdater(db)
        await updater.update_client_segments(client.id)