from abc import ABC, abstractmethod
from typing import List, Optional

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

    @abstractmethod
    async def update_status(
            self, user_id: int, status: str, error: Optional[str] = None,
    ) -> None: ...

    @abstractmethod
    async def heartbeat(self, user_id: int) -> None:
        """Отметить, что анализ жив: status='processing' и свежий updated_at."""

    @abstractmethod
    async def claim_stale(self, stale_after_seconds: int) -> List[int]:
        """
        Атомарно забрать зависшие анализы (pending/processing без движения).

        Возвращает user_id, которые этот вызов «захватил»: updated_at у них
        обновляется, поэтому параллельный вызов с другого инстанса их уже не вернёт.
        """

    @abstractmethod
    async def commit(self) -> None:
        """Зафиксировать изменения текущей сессии."""
