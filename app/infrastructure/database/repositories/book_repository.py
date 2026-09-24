from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
from app.domain.entities.book import BookEntity
from app.domain.interfaces.book_repository import IBookRepository
from app.models.book import Book as BookModel
from common import RedisCache


class SqlAlchemyBookRepository(IBookRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = RedisCache(prefix="book", default_ttl=300)

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

    async def get_by_id(self, book_id: int) -> Optional[BookEntity] :
        cached = await self.cache.get(str(book_id))
        if cached:
            return BookEntity(**cached)

        stmt = select(BookModel).where(
            BookModel.id == book_id, BookModel.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None

        book = self._to_entity(model)

        # Сохраняем в кэш
        await self.cache.set(
            str(book_id),
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "description": book.description,
                "created_at": book.created_at.isoformat() if book.created_at else None,
            },
        )

        return book

    async def update(self, book: BookEntity) -> BookEntity:
        stmt = select(BookModel).where(BookModel.id == book.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        model.title = book.title
        model.author = book.author
        model.description = book.description
        await self.session.flush()
        await self.session.refresh(model)

        await self.cache.delete(str(book.id))

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



    async def find_similar_by_embedding(
            self,
            embedding: list[float],
            exclude_book_ids: list[int],
            limit: int = 10,
            min_similarity: float = 0.5,
    ) -> list[tuple[BookEntity, float]]:
        """
        Найти похожие книги по эмбеддингу.

        """
        # cosine_distance = 1 - cosine_similarity
        distance = BookModel.embedding.cosine_distance(embedding).label("distance")

        stmt = (
            select(BookModel, distance)
            .where(
                BookModel.deleted_at.is_(None),
                BookModel.embedding.isnot(None),
            )
        )

        if exclude_book_ids:
            stmt = stmt.where(BookModel.id.notin_(exclude_book_ids))

        stmt = (
            stmt
            .order_by(distance)
            .limit(limit * 2)  # берём с запасом для фильтра
        )

        result = await self.session.execute(stmt)

        books_with_scores = []
        for model, dist in result.all():
            similarity = 1 - dist  # cosine similarity
            if similarity >= min_similarity:
                books_with_scores.append((self._to_entity(model), similarity))

        return books_with_scores[:limit]