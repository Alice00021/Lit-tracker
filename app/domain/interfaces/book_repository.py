from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.book import BookEntity


class IBookRepository(ABC):
    @abstractmethod
    async def create(self, book: BookEntity) -> BookEntity: ...

    @abstractmethod
    async def get_by_id(self, book_id: int) -> Optional[BookEntity]: ...

    @abstractmethod
    async def update(self, book: BookEntity) -> BookEntity: ...

    @abstractmethod
    async def delete(self, book_id: int) -> None: ...

    @abstractmethod
    async def get_all(self, limit: int, offset: int) -> list[BookEntity]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def find_similar_by_embedding(
            self,
            embedding: list[float],
            exclude_book_ids: list[int],
            limit: int = 10,
            min_similarity: float = 0.5,
    ) -> list[tuple[BookEntity, float]]: ...