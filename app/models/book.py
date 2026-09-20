from sqlalchemy import Column, String, Text
from pgvector.sqlalchemy import Vector
from app.models.base import BaseModel
from app.core.config import settings


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