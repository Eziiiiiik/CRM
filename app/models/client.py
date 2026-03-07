from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Date, JSON, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.segment import client_segments


# Таблица для связи многие-ко-многим (теги клиентов)
client_tags = Table(
    'client_tags',
    Base.metadata,
    Column('client_id', Integer, ForeignKey('clients.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'))
)


class Tag(Base):
    """Теги для группировки клиентов"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    color = Column(String(7), default="#808080")  # HEX цвет
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Client(Base):
    __tablename__ = "clients"

    # Основная информация
    id = Column(Integer, primary_key=True, index=True)

    # ФИО (раздельно)
    last_name = Column(String(100), nullable=False, index=True)  # Фамилия
    first_name = Column(String(100), nullable=False, index=True)  # Имя
    middle_name = Column(String(100))  # Отчество

    # Личная информация
    birth_date = Column(Date)  # Дата рождения
    gender = Column(String(10))  # male, female, other
    marital_status = Column(String(20))  # married, single, divorced, widowed

    # Контактная информация
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), index=True)
    alternative_phone = Column(String(20))

    # Мессенджеры (храним как JSON для гибкости)
    messengers = Column(JSON, default=list)
    social_networks = Column(JSON, default=list)
    addresses = Column(JSON, default=list)

    # Профессиональная информация
    company = Column(String(255))
    position = Column(String(255))
    industry = Column(String(100))
    website = Column(String(255))

    # Связи
    segments = relationship(
        "Segment",
        secondary=client_segments,
        back_populates="clients",
        passive_deletes=True
    )

    communication_preferences = Column(JSON, default=dict)
    notes = Column(Text)

    # Теги (связь многие-ко-многим)
    tags = relationship("Tag", secondary=client_tags, backref="clients")

    # Системная информация
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    source = Column(String(50))

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_contact_at = Column(DateTime(timezone=True))

    # Связи с другими таблицами
    deals = relationship("Deal", back_populates="client", cascade="all, delete-orphan")
    interactions = relationship(
        "Interaction",
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="Interaction.created_at.desc()"
    )

    @property
    def full_name(self) -> str:
        """Полное имя"""
        # Вариант 1: Игнорировать предупреждение
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)  # type: ignore

    @property
    def short_name(self) -> str:
        """Краткое имя (Иванов И.И.)"""
        initials = ""
        if self.first_name:
            initials += self.first_name[0].upper() + "."
        if self.middle_name:
            initials += self.middle_name[0].upper() + "."
        return f"{self.last_name} {initials}".strip()  # type: ignore

    def __repr__(self):
        return f"<Client(id={self.id}, name={self.full_name})>"