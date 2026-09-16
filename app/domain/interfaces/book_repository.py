from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.book import BookEntity


class IBookRepository(ABC):
    @abstractmethod
    async def create(self, book: BookEntity) -> BookEntity: ...

    @abstractmethod
    async def get_by_id(self, book_id: int) -> Optional[BookEntity]: ...

    @abstractmethod
    async def get_by_title_author(self, title: str, author: str) -> Optional[BookEntity]: ...

    @abstractmethod
    async def update(self, book: BookEntity) -> BookEntity: ...

    @abstractmethod
    async def delete(self, book_id: int) -> None: ...

    @abstractmethod
    async def get_all(self, limit: int, offset: int) -> list[BookEntity]: ...

    @abstractmethod
    async def count(self) -> int: ...