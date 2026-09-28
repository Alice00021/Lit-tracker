"""
Unit-тесты для BookService.

Используем fake-репозиторий — не нужна реальная БД.
"""
import pytest
from datetime import datetime, timezone
from typing import Optional

from app.application.services.book_service import BookService
from app.domain.entities.book import BookEntity
from app.interfaces.schemas.book import BookCreateSchema, BookUpdateSchema
from common.exceptions import NotFoundError


# Fakes

class FakeBookRepository:
    """In-memory репозиторий для тестов."""

    def __init__(self):
        self.books: dict[int, BookEntity] = {}
        self.next_id = 1

    async def create(self, book: BookEntity) -> BookEntity:
        book.id = self.next_id
        book.created_at = datetime.now(timezone.utc)
        self.books[book.id] = book
        self.next_id += 1
        return book

    async def get_by_id(self, book_id: int) -> Optional[BookEntity]:
        return self.books.get(book_id)

    async def update(self, book: BookEntity) -> BookEntity:
        self.books[book.id] = book
        return book

    async def soft_delete(self, book_id: int) -> None:
        if book_id in self.books:
            self.books[book_id].deleted_at = datetime.now(timezone.utc)

    async def get_all(self, limit: int, offset: int) -> list[BookEntity]:
        books = list(self.books.values())
        return books[offset:offset + limit]

    async def count(self) -> int:
        return len(self.books)


class FakeEmbeddingClient:
    """Fake embedding client."""

    async def get_embedding(self, text: str) -> list[float]:
        return [0.1] * 768


# ============ Fixtures ============

@pytest.fixture
def fake_repo():
    return FakeBookRepository()


@pytest.fixture
def fake_embedding():
    return FakeEmbeddingClient()


@pytest.fixture
def service(fake_repo, fake_embedding):
    return BookService(fake_repo, fake_embedding)


# ============ Helpers ============

def make_book_entity(
        book_id: Optional[int] = None,
        title: str = "1984",
        author: str = "Orwell",
        description: str = "Test description",     # ← helper
) -> BookEntity:
    """Создать BookEntity с обязательным description."""
    return BookEntity(
        id=book_id,
        title=title,
        author=author,
        description=description,
    )


# ============ Tests ============

class TestBookServiceCreate:
    """Тесты создания книги."""

    @pytest.mark.asyncio
    async def test_create_book_success(self, service):
        """Успешное создание."""
        data = BookCreateSchema(
            title="1984",
            author="George Orwell",
            description="Dystopian novel",
        )

        book = await service.create_book(data)

        assert book.id == 1
        assert book.title == "1984"
        assert book.author == "George Orwell"
        assert book.description == "Dystopian novel"
        assert book.embedding is not None
        assert len(book.embedding) == 768

    @pytest.mark.asyncio
    async def test_create_book_generates_embedding(self, service):
        """Embedding генерируется."""
        data = BookCreateSchema(
            title="Test",
            author="Author",
            description="Test desc",
        )

        book = await service.create_book(data)

        assert book.embedding == [0.1] * 768


class TestBookServiceGet:
    """Тесты получения книги."""

    @pytest.mark.asyncio
    async def test_get_existing_book(self, service, fake_repo):
        """Получение существующей книги."""
        # ← используем helper
        book = await fake_repo.create(make_book_entity())

        result = await service.get_book(book.id)

        assert result.id == book.id
        assert result.title == "1984"

    @pytest.mark.asyncio
    async def test_get_missing_book_raises(self, service):
        """Несуществующая книга → NotFoundError."""
        with pytest.raises(NotFoundError):
            await service.get_book(999)


class TestBookServiceUpdate:
    """Тесты обновления книги."""

    @pytest.mark.asyncio
    async def test_update_book_success(self, service, fake_repo):
        """Успешное обновление."""
        book = await fake_repo.create(make_book_entity())

        data = BookUpdateSchema(description="Updated")
        result = await service.update_book(book.id, data)

        assert result.description == "Updated"
        assert result.title == "1984"

    @pytest.mark.asyncio
    async def test_update_missing_book_raises(self, service):
        """Несуществующая книга → NotFoundError."""
        data = BookUpdateSchema(description="Updated")

        with pytest.raises(NotFoundError):
            await service.update_book(999, data)


class TestBookServiceDelete:
    """Тесты удаления книги."""

    @pytest.mark.asyncio
    async def test_delete_book_success(self, service, fake_repo):
        """Успешное удаление."""
        book = await fake_repo.create(make_book_entity())

        await service.delete_book(book.id)

        assert book.is_deleted() is True

    @pytest.mark.asyncio
    async def test_delete_missing_book_raises(self, service):
        """Несуществующая книга → NotFoundError."""
        with pytest.raises(NotFoundError):
            await service.delete_book(999)


class TestBookServiceList:
    """Тесты пагинации."""

    @pytest.mark.asyncio
    async def test_list_empty(self, service):
        """Пустой список."""
        result = await service.list_books(page=1, page_size=10)

        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_with_books(self, service, fake_repo):
        """Список с книгами."""
        for i in range(5):
            await fake_repo.create(make_book_entity(
                title=f"Book {i}",
                author="Author",
                description=f"Description {i}",
            ))

        result = await service.list_books(page=1, page_size=10)

        assert len(result["items"]) == 5
        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_list_pagination(self, service, fake_repo):
        """Пагинация."""
        for i in range(25):
            await fake_repo.create(make_book_entity(
                title=f"Book {i}",
                author="Author",
                description=f"Description {i}",
            ))

        page1 = await service.list_books(page=1, page_size=10)
        assert len(page1["items"]) == 10

        page2 = await service.list_books(page=2, page_size=10)
        assert len(page2["items"]) == 10

        page3 = await service.list_books(page=3, page_size=10)
        assert len(page3["items"]) == 5