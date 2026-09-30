from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import UserEntity
from app.domain.exceptions import ConflictError
from app.domain.interfaces.user_repository import IUserRepository
from app.models.user import User as UserModel


class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_entity(model: UserModel) -> UserEntity:
        return UserEntity(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            created_at=model.created_at,
            deleted_at=model.deleted_at,
        )

    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        stmt = select(UserModel).where(
            UserModel.id == user_id, UserModel.deleted_at.is_(None),
        )
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        stmt = select(UserModel).where(
            UserModel.email == email, UserModel.deleted_at.is_(None),
        )
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, email: str, hashed_password: str) -> UserEntity:
        model = UserModel(email=email, hashed_password=hashed_password)
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError:
            # гонка: два запроса с одним email прошли проверку get_by_email одновременно
            await self.session.rollback()
            raise ConflictError("Email already registered")
        return self._to_entity(model)
