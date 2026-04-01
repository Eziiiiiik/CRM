from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class NewsBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    slug: Optional[str] = None
    summary: Optional[str] = Field(None, max_length=500)
    content: str
    image_url: Optional[str] = None
    category: str = "news"
    is_published: bool = True


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_published: Optional[bool] = None


class NewsResponse(NewsBase):
    id: int
    views: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True