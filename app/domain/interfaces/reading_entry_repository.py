from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities.reading_entry import ReadingEntryEntity


class IReadingEntryRepository(ABC):
    @abstractmethod
    async def create(self, entry: ReadingEntryEntity) -> ReadingEntryEntity: ...

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[ReadingEntryEntity]: ...

    @abstractmethod
    async def update(self, entry: ReadingEntryEntity) -> ReadingEntryEntity: ...

    @abstractmethod
    async def delete(self, id: int) -> None: ...

    @abstractmethod
    async def paginate(self, limit: int, offset: int) -> list[ReadingEntryEntity]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def get_by_user_id(
            self,
            user_id: int,
            limit: int = 100,
            offset: int = 0,
    ) -> List[ReadingEntryEntity]: ...