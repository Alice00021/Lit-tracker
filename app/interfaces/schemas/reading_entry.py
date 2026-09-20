from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date
from app.interfaces.schemas.book import BookReadSchema


class ReadingEntryCreateSchema(BaseModel):

    note: str = Field(
        ...,
        min_length=10,
        description="Заметка о книге (минимум 10 символов)",
    )

    read_date: date = Field(
        ...,
        description="Дата прочтения",
    )

    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Оценка от 1 до 5 (опционально)",
    )

class ReadingEntryUpdateSchema(BaseModel):
    note: Optional[str] = Field(
        None,
        min_length=10,
        description="Новая заметка",
    )

    read_date: Optional[date] = Field(
        None,
        description="Новая дата прочтения",
    )

    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Новая оценка",
    )

class ReadingEntryReadSchema(BaseModel):
    """Схема ответа с записью."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book: BookReadSchema
    note: str
    read_date: date
    rating: Optional[int] = None
    created_at: datetime


class ReadingEntryPaginatedSchema(BaseModel):
    """Схема пагинированного ответа."""

    items: list[ReadingEntryReadSchema]
    total: int
    page: int
    page_size: int
    total_pages: int