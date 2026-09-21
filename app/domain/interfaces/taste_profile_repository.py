from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.taste_profile import TasteProfileEntity


class ITasteProfileRepository(ABC):
    @abstractmethod
    async def get_by_user_id(
            self, user_id: int,
    ) -> Optional[TasteProfileEntity]: ...

    @abstractmethod
    async def upsert(
            self, profile: TasteProfileEntity,
    ) -> TasteProfileEntity: ...