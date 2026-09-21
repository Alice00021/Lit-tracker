from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from typing import Optional

from app.domain.entities.taste_profile import TasteProfileEntity
from app.domain.interfaces.taste_profile_repository import ITasteProfileRepository
from app.models.taste_profile import TasteProfile as TasteProfileModel


class SqlAlchemyTasteProfileRepository(ITasteProfileRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: TasteProfileModel) -> TasteProfileEntity:
        return TasteProfileEntity(
            id=model.id,
            user_id=model.user_id,
            analysis=model.analysis,
            entries_count=model.entries_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    async def get_by_user_id(
            self, user_id: int,
    ) -> Optional[TasteProfileEntity]:
        stmt = select(TasteProfileModel).where(
            TasteProfileModel.user_id == user_id,
            TasteProfileModel.deleted_at.is_(None),
            )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def upsert(
            self, profile: TasteProfileEntity,
    ) -> TasteProfileEntity:
        stmt = (
            insert(TasteProfileModel)
            .values(
                user_id=profile.user_id,
                analysis=profile.analysis,
                entries_count=profile.entries_count,
            )
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "analysis": profile.analysis,
                    "entries_count": profile.entries_count,
                },
            )
            .returning(TasteProfileModel)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        return self._to_entity(model)

    async def update_status(
            self,
            user_id: int,
            status: str,
            error: Optional[str] = None,
    ) -> None:
        stmt = select(TasteProfileModel).where(
            TasteProfileModel.user_id == user_id,
            )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.status = status
            model.error = error
            await self.session.flush()