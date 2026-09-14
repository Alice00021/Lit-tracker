from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import selectinload
from app.domain.entities.reading_entry import ReadingEntryEntity
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.models.reading_entry import ReadingEntry as ReadingEntryModel


class SqlAlchemyReadingEntryRepository(IReadingEntryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: ReadingEntryModel) -> ReadingEntryEntity:
        return ReadingEntryEntity(
            id=model.id,
            user_id=model.user_id,
            book_id=model.book_id,
            note=model.note,
            note_embedding=model.note_embedding,
            read_date=model.read_date,
            rating=model.rating,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            book=model.book,
        )

    async def count(self) -> int:

        stmt = (
            select(func.count())
            .select_from(ReadingEntryModel)
            .where(ReadingEntryModel.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def paginate(
            self,
            limit: int,
            offset: int,
    ) -> List[ReadingEntryEntity]:
        stmt = (
            select(ReadingEntryModel)
            .where(ReadingEntryModel.deleted_at.is_(None))
            .order_by(ReadingEntryModel.read_date.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(ReadingEntryModel.book))
        )
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def create(self, entry: ReadingEntryEntity) -> ReadingEntryEntity:
        model = ReadingEntryModel(
            user_id=entry.user_id,
            book_id=entry.book_id,
            note=entry.note,
            note_embedding=entry.note_embedding,
            read_date=entry.read_date,
            rating=entry.rating,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, id: int) -> Optional[ReadingEntryEntity] :
        stmt = (
            select(ReadingEntryModel).where(
            ReadingEntryModel.id == id, ReadingEntryModel.deleted_at.is_(None)
        ))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, entry: ReadingEntryEntity) -> ReadingEntryEntity:
        stmt = select(ReadingEntryModel).where(ReadingEntryModel.id == entry.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()

        model.note = entry.note
        model.note_embedding = entry.note_embedding
        model.read_date = entry.read_date
        model.rating = entry.rating

        await self.session.flush()
        await self.session.refresh(model, attribute_names=["book"])
        return self._to_entity(model)

    async def delete(self, id: int) -> None:
        stmt = select(ReadingEntryModel).where(ReadingEntryModel.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        model.deleted_at = datetime.utcnow()
        await self.session.flush()

    async def count_by_user(self, user_id: int) -> int:
        """Посчитать количество записей пользователя."""

        stmt = (
            select(func.count())
            .select_from(ReadingEntryModel)
            .where(
                ReadingEntryModel.user_id == user_id,
                ReadingEntryModel.deleted_at.is_(None),
                )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_user_id(
            self,
            user_id: int,
            limit: int = 100,
            offset: int = 0,
    ) -> List[ReadingEntryEntity]:
        """Список записей пользователя с пагинацией."""
        stmt = (
        select(ReadingEntryModel)
        .where(
            ReadingEntryModel.user_id == user_id,
            ReadingEntryModel.deleted_at.is_(None),
            )
        .order_by(ReadingEntryModel.read_date.desc())
        .offset(offset)
        .limit(limit)
        .options(selectinload(ReadingEntryModel.book))
    )
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
