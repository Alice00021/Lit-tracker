from typing import List, Optional

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

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
            status=model.status,
            error=model.error,
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
                status=profile.status,
                error=profile.error,
            )
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "analysis": profile.analysis,
                    "entries_count": profile.entries_count,
                    "status": profile.status,
                    "error": profile.error,
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

    async def heartbeat(self, user_id: int) -> None:
        stmt = (
            update(TasteProfileModel)
            .where(TasteProfileModel.user_id == user_id)
            .values(status="processing", updated_at=func.now())
        )
        await self.session.execute(stmt)

    async def claim_stale(self, stale_after_seconds: int) -> List[int]:
        stmt = (
            update(TasteProfileModel)
            .where(
                TasteProfileModel.status.in_(["pending", "processing"]),
                TasteProfileModel.deleted_at.is_(None),
                TasteProfileModel.updated_at
                < func.now() - text(f"interval '{int(stale_after_seconds)} seconds'"),
            )
            .values(updated_at=func.now())
            .returning(TasteProfileModel.user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def commit(self) -> None:
        await self.session.commit()
