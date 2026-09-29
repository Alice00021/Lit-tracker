from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, String, Text

from app.core.config import settings
from app.models.base import BaseModel


class Book(BaseModel):
    __tablename__ = "books"

    title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "title": self.title,
            "author": self.author,
            "description": self.description,
        })
        return data