from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NewsBase(BaseModel):
    title: str
    slug: Optional[str] = None
    summary: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    category: str = "news"
    is_published: bool = True

class NewsCreate(NewsBase):
    pass

class NewsResponse(NewsBase):
    id: int
    views: int
    created_at: datetime

    class Config:
        from_attributes = True