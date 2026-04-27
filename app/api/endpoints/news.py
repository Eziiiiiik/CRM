from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional

from app.core.database import get_db
from app.models.news import News
from app.schemas.news import NewsCreate, NewsResponse

router = APIRouter(prefix="/news", tags=["news"])

@router.get("/", response_model=List[NewsResponse])
async def get_news_list(
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(News).where(News.is_published == True)
    if category:
        query = query.where(News.category == category)
    query = query.order_by(desc(News.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/latest", response_model=List[NewsResponse])
async def get_latest_news(limit: int = 3, db: AsyncSession = Depends(get_db)):
    query = select(News).where(News.is_published == True).order_by(desc(News.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/categories", response_model=List[str])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(News.category).where(News.is_published == True).distinct())
    cats = result.scalars().all()
    return [c for c in cats if c]

@router.get("/{news_id}", response_model=NewsResponse)
async def get_news_detail(news_id: int, db: AsyncSession = Depends(get_db)):
    news = await db.get(News, news_id)
    if not news or not news.is_published:
        raise HTTPException(404, "Not found")
    news.views += 1
    await db.commit()
    await db.refresh(news)
    return news

@router.post("/", response_model=NewsResponse)
async def create_news(news_data: NewsCreate, db: AsyncSession = Depends(get_db)):
    import re
    slug = re.sub(r'[^\w\s-]', '', news_data.title.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    # Убираем slug из дампа, чтобы передать его отдельно (или присвоить после создания)
    data = news_data.model_dump()
    data.pop('slug', None)  # удаляем slug, если он есть
    news = News(**data)
    news.slug = slug
    db.add(news)
    await db.commit()
    await db.refresh(news)
    return news