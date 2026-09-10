from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
from app.core.database import Base


class BaseModel(Base):
    """Абстрактная базовая модель с общими полями"""

    __abstract__ = True  # Не создавать таблицу для этого класса

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # NULL = не удалено

    @classmethod
    @declared_attr
    def __tablename__(cls):
        """Автоматически генерирует имя таблицы из имени класса"""
        return cls.__name__.lower() + "s"  # User → users, Book → books

    def soft_delete(self):
        """Мягкое удаление — устанавливаем deleted_at"""
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Восстановить запись"""
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        """Проверить, удалена ли запись"""
        return self.deleted_at is not None

    def to_dict(self) -> dict:
        """Преобразовать модель в словарь (для сериализации)"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }