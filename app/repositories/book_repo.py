from sqlalchemy import select
from app.models.book import Book


class BookRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_id(self, book_id: int) -> Book | None:
        """Получить книгу по ID (только не удалённые)"""
        stmt = select(Book).where(
            Book.id == book_id,
            Book.deleted_at.is_(None)  # Только не удалённые
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Book]:
        """Получить все книги (только не удалённые)"""
        stmt = select(Book).where(
            Book.deleted_at.is_(None)
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def soft_delete(self, book_id: int) -> bool:
        """Мягкое удаление книги"""
        book = await self.get_by_id(book_id)
        if not book:
            return False
        book.soft_delete()
        await self.session.commit()
        return True