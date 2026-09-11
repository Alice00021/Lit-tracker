from sqlalchemy import Column, Integer, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.models.base import BaseModel
from app.core.config import settings


class ReadingEntry(BaseModel):
    __tablename__ = "reading_entries"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    note = Column(Text, nullable=False)
    note_embedding = Column(Vector(settings.OPENAI_EMBEDDING_DIMENSION), nullable=True)
    read_date = Column(Date, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5

    # Отношения
    user = relationship("User")
    book = relationship("Book")

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "book_id": self.book_id,
            "note": self.note,
            "read_date": self.read_date.isoformat() if self.read_date else None,
            "rating": self.rating,
        })
        return data