from sqlalchemy import Column, Integer, ForeignKey, JSON, DateTime, String
from sqlalchemy.sql import func
from app.models.base import BaseModel


class TasteProfile(BaseModel):
    __tablename__ = "taste_profiles"

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )
    analysis = Column(JSON, nullable=False)
    entries_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    error = Column(String(500), nullable=True)