from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional

from app.core.database import get_db
from app.models.news import News
from app.schemas.news import NewsCreate, NewsUpdate, NewsResponse

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/", response_model=List[NewsResponse])
async def get_news(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=50),
        category: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    """Получить список новостей"""
    query = select(News).where(News.is_published == True)

    if category:
        query = query.where(News.category == category)

    query = query.order_by(desc(News.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/latest", response_model=List[NewsResponse])
async def get_latest_news(
        limit: int = 3,
        db: AsyncSession = Depends(get_db)
):
    """Получить последние новости (для виджета)"""
    query = select(News).where(News.is_published == True).order_by(desc(News.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{news_id}", response_model=NewsResponse)
async def get_news_detail(
        news_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Получить детальную новость"""
    news = await db.get(News, news_id)
    if not news or not news.is_published:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Увеличиваем счётчик просмотров
    news.views += 1
    await db.commit()
    await db.refresh(news)
    return news


@router.get("/by-slug/{slug}", response_model=NewsResponse)
async def get_news_by_slug(
        slug: str,
        db: AsyncSession = Depends(get_db)
):
    """Получить новость по slug"""
    result = await db.execute(select(News).where(News.slug == slug, News.is_published == True))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    news.views += 1
    await db.commit()
    return news


@router.get("/categories", response_model=List[str])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Получить список категорий"""
    result = await db.execute(
        select(News.category).where(News.is_published == True).distinct()
    )
    return [cat for cat in result.scalars().all() if cat]


# Админские эндпоинты (для менеджеров)
@router.post("/", response_model=NewsResponse, status_code=201)
async def create_news(
        news_data: NewsCreate,
        db: AsyncSession = Depends(get_db)
):
    """Создать новость (только для админов)"""
    # Генерируем slug из заголовка
    import re
    slug = re.sub(r'[^\w\s-]', '', news_data.title.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    news_data.slug = slug

    news = News(**news_data.model_dump())
    db.add(news)
    await db.commit()
    await db.refresh(news)
    return news


@router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
        news_id: int,
        news_data: NewsUpdate,
        db: AsyncSession = Depends(get_db)
):
    """Обновить новость"""
    news = await db.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    update_data = news_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(news, field, value)

    await db.commit()
    await db.refresh(news)
    return news


@router.delete("/{news_id}")
async def delete_news(
        news_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Удалить новость"""
    news = await db.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    await db.delete(news)
    await db.commit()
    return {"message": "Новость удалена"}