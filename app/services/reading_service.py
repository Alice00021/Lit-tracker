from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List
from app.models.reading_entry import ReadingEntry
from app.schemas.reading_entry import ReadingEntryResponseSchema, BookResponseSchema

async def get_reading_entries(self, user_id: int, limit: int = 100, offset: int = 0):
    entries = await self.entry_repo.get_by_user_id(user_id, limit, offset)

    return [
        ReadingEntryResponseSchema(
            id=e.id,
            user_id=e.user_id,
            book=BookResponseSchema(
                id=e.book.id,
                title=e.book.title,
                author=e.book.author,
                description=e.book.description,
                created_at=e.book.created_at
            ),
            note=e.note,
            read_date=e.read_date,
            rating=e.rating,
            created_at=e.created_at
        )
        for e in entries
    ]