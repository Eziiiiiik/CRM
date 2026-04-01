from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True)  # для ЧПУ
    summary = Column(String(500))  # краткое описание
    content = Column(Text, nullable=False)  # полный текст
    image_url = Column(String(500))  # картинка
    category = Column(String(50), default="news")  # news, article, update
    views = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Автор (если есть система пользователей)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)