from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
from app.domain.entities.book import BookEntity
from app.domain.interfaces.book_repository import IBookRepository
from app.models.book import Book as BookModel


class SqlAlchemyBookRepository(IBookRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: BookModel) -> BookEntity:
        return BookEntity(
            id=model.id, title=model.title, author=model.author,
            description=model.description, embedding=model.embedding,
            created_at=model.created_at, deleted_at=model.deleted_at,
        )

    async def create(self, book: BookEntity) -> BookEntity:
        model = BookModel(
            title=book.title, author=book.author,
            description=book.description, embedding=book.embedding,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, id: int) -> Optional[BookEntity] :
        stmt = select(BookModel).where(
            BookModel.id == id, BookModel.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_title_author(self, title: str, author: str) -> Optional[BookEntity]:
        """Найти книгу по названию и автору."""
        stmt = select(BookModel).where(
            BookModel.title == title,
            BookModel.author == author,
            BookModel.deleted_at.is_(None),
            )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, book: BookEntity) -> BookEntity:
        stmt = select(BookModel).where(BookModel.id == book.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        model.title = book.title
        model.author = book.author
        model.description = book.description
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, id: int) -> None:
        stmt = select(BookModel).where(BookModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        model.deleted_at = datetime.utcnow()
        await self.session.flush()

    async def get_all(self, limit: int, offset: int) -> list[BookEntity]:
        stmt = select(BookModel).where(
            BookModel.deleted_at.is_(None)
        ).order_by(BookModel.id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        stmt = select(func.count()).select_from(BookModel).where(BookModel.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()