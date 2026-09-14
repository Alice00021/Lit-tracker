from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from app.domain.entities.book import BookEntity


@dataclass
class ReadingEntryEntity:
    id: Optional[int]
    user_id: int
    book_id: int
    note: str
    note_embedding: Optional[list[float]]
    read_date: date
    rating: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    book: Optional[BookEntity] = None

    def is_deleted(self) -> bool:
        return self.deleted_at is not None