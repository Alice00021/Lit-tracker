"""
Unit-тесты для RecommendationService.
"""
import pytest

from app.application.services.recommendation_service import RecommendationService
from app.domain.entities.book import BookEntity
from app.domain.entities.reading_entry import ReadingEntryEntity
from app.domain.entities.taste_profile import TasteProfileEntity
from common.exceptions import NotFoundError


# Fakes

class FakeBookRepo:
    """Fake репозиторий книг."""

    def __init__(self, similar: list = None):
        self._similar = similar or []
        self.last_call_args = None

    async def find_similar_by_embedding(self, **kwargs):
        self.last_call_args = kwargs
        return self._similar


class FakeEntryRepo:
    """Fake репозиторий записей."""

    def __init__(self, entries: list = None):
        self._entries = entries or []

    async def get_by_user_id(self, *args, **kwargs):
        return self._entries


class FakeProfileRepo:
    """Fake репозиторий профилей."""

    def __init__(self, profile: TasteProfileEntity = None):
        self._profile = profile

    async def get_by_user_id(self, *args, **kwargs):
        return self._profile


# Helpers

def make_profile(status: str = "done") -> TasteProfileEntity:
    """Создать тестовый профиль."""
    return TasteProfileEntity(
        id=1,
        user_id=1,
        analysis={"themes": ["philosophy"]},
        entries_count=1,
        status=status,
    )


def make_entry(book_id: int = 1) -> ReadingEntryEntity:
    """Создать тестовую запись."""
    return ReadingEntryEntity(
        id=1,
        user_id=1,
        book_id=book_id,
        note="test note",
        note_embedding=[0.1] * 768,
        read_date=None,
    )


def make_book(book_id: int = 5, title: str = "Solaris") -> BookEntity:
    """Создать тестовую книгу."""
    return BookEntity(
        id=book_id,
        title=title,
        author="Author",
        description="Test description",
    )


# Tests

class TestRecommendationServiceErrors:
    """Тесты ошибок."""

    @pytest.mark.asyncio
    async def test_no_profile_raises(self):
        """Нет профиля → NotFoundError."""
        service = RecommendationService(
            FakeBookRepo(),
            FakeEntryRepo(),
            FakeProfileRepo(None),
        )

        with pytest.raises(NotFoundError) as exc:
            await service.get_recommendations(user_id=1)

        assert "TasteProfile" in str(exc.value)

    @pytest.mark.asyncio
    async def test_profile_not_done_raises(self):
        """Профиль не готов → NotFoundError."""
        profile = make_profile(status="processing")
        service = RecommendationService(
            FakeBookRepo(),
            FakeEntryRepo(),
            FakeProfileRepo(profile),
        )

        with pytest.raises(NotFoundError):
            await service.get_recommendations(user_id=1)

    @pytest.mark.asyncio
    async def test_no_entries_raises(self):
        """Нет записей → NotFoundError."""
        profile = make_profile()
        service = RecommendationService(
            FakeBookRepo(),
            FakeEntryRepo([]),
            FakeProfileRepo(profile),
        )

        with pytest.raises(NotFoundError) as exc:
            await service.get_recommendations(user_id=1)

        assert "ReadingEntries" in str(exc.value)

    @pytest.mark.asyncio
    async def test_no_embeddings_raises(self):
        """Нет эмбеддингов → NotFoundError."""
        profile = make_profile()
        entry = ReadingEntryEntity(
            id=1, user_id=1, book_id=1,
            note="test",
            note_embedding=None,   # ← нет эмбеддинга
            read_date=None,
        )
        service = RecommendationService(
            FakeBookRepo(),
            FakeEntryRepo([entry]),
            FakeProfileRepo(profile),
        )

        with pytest.raises(NotFoundError):
            await service.get_recommendations(user_id=1)


class TestRecommendationServiceSuccess:
    """Тесты успешных сценариев."""

    @pytest.mark.asyncio
    async def test_successful_recommendations(self):
        """Успешные рекомендации."""
        profile = make_profile()
        entries = [make_entry(book_id=1)]
        similar = [
            (make_book(5, "Solaris"), 0.85),
            (make_book(6, "Dune"), 0.70),
        ]

        service = RecommendationService(
            FakeBookRepo(similar),
            FakeEntryRepo(entries),
            FakeProfileRepo(profile),
        )

        result = await service.get_recommendations(user_id=1)

        assert len(result) == 2
        assert result[0]["book"]["title"] == "Solaris"
        assert result[0]["similarity"] == 0.85
        assert "reason" in result[0]

    @pytest.mark.asyncio
    async def test_empty_recommendations(self):
        """Нет похожих книг — пустой список."""
        profile = make_profile()
        entries = [make_entry(book_id=1)]

        service = RecommendationService(
            FakeBookRepo([]),  # ← пусто
            FakeEntryRepo(entries),
            FakeProfileRepo(profile),
        )

        result = await service.get_recommendations(user_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_exclude_read_books(self):
        """Прочитанные книги исключаются."""
        profile = make_profile()
        entries = [make_entry(book_id=42)]  # прочитал книгу 42
        book_repo = FakeBookRepo([])

        service = RecommendationService(
            book_repo,
            FakeEntryRepo(entries),
            FakeProfileRepo(profile),
        )

        await service.get_recommendations(user_id=1)

        # Проверяем, что book_id=42 передан в exclude
        assert book_repo.last_call_args is not None
        assert 42 in book_repo.last_call_args["exclude_book_ids"]

    @pytest.mark.asyncio
    async def test_reason_based_on_score(self):
        """Reason зависит от similarity."""
        profile = make_profile()
        entries = [make_entry(book_id=1)]
        similar = [
            (make_book(5, "Excellent"), 0.90),   # высокий
            (make_book(6, "Good"), 0.76),         # средний
            (make_book(7, "Low"), 0.50),          # низкий
        ]

        service = RecommendationService(
            FakeBookRepo(similar),
            FakeEntryRepo(entries),
            FakeProfileRepo(profile),
        )

        result = await service.get_recommendations(user_id=1)

        # У всех разный reason
        reasons = [r["reason"] for r in result]
        assert len(set(reasons)) == 3   # 3 разных reason