from datetime import datetime, timezone

from app.domain.entities.book import BookEntity


class TestBookEntity:
    """Тесты BookEntity."""

    def test_create_book_with_required_fields(self):
        """Создание книги с обязательными полями."""
        book = BookEntity(
            id=1,
            title="1984",
            author="George Orwell",
            description=None
        )

        assert book.id == 1
        assert book.title == "1984"
        assert book.author == "George Orwell"
        assert book.embedding is None
        assert book.deleted_at is None

    def test_create_book_with_all_fields(self):
        """Создание книги со всеми полями."""
        embedding = [0.1] * 768
        book = BookEntity(
            id=1,
            title="1984",
            author="Orwell",
            description="Dystopian novel",
            embedding=embedding,
        )

        assert book.description == "Dystopian novel"
        assert book.embedding == embedding
        assert len(book.embedding) == 768

    def test_is_deleted_false_for_new_book(self):
        """Новая книга не удалена."""
        book = BookEntity(id=1, title="1984", author="Orwell", description=None)

        assert book.is_deleted() is False

    def test_is_deleted_true_for_soft_deleted(self):
        """Soft-deleted книга."""
        book = BookEntity(
            id=1,
            title="1984",
            author="Orwell",
            description=None,
            deleted_at=datetime.now(timezone.utc),
        )

        assert book.is_deleted() is True
