from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BookEntity:
    id: Optional[int]
    title: str
    author: str
    description: Optional[str]
    embedding: Optional[list[float]] = None
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    def is_deleted(self) -> bool:
        return self.deleted_at is not None