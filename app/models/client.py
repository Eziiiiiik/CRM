from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship

class Client(Base):
    """Модель клиента CRM"""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    company = Column(String(255))
    notes = Column(Text)
    is_active = Column(Boolean, default=True)

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    #Сделки
    deals = relationship("Deal", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client(id={self.id}, name={self.full_name})>"