from app.domain.entities.book import BookEntity
from app.domain.interfaces.book_repository import IBookRepository
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.domain.interfaces.taste_profile_repository import ITasteProfileRepository
from common.exceptions import NotFoundError
from common import get_logger

logger = get_logger(__name__)


class RecommendationService:
    """
    Сервис рекомендаций книг.

    Логика:
    1. Получить Taste Profile (анализ вкуса через LLM)
    2. Получить прочитанные книги
    3. Усреднить эмбеддинги всех заметок → «вектор вкуса»
    4. Найти похожие книги через pgvector (top-N)
    5. Сформировать reason на основе similarity score
    """

    def __init__(
            self,
            book_repo: IBookRepository,
            entry_repo: IReadingEntryRepository,
            profile_repo: ITasteProfileRepository,
    ):
        self.book_repo = book_repo
        self.entry_repo = entry_repo
        self.profile_repo = profile_repo

    async def get_recommendations(
            self,
            user_id: int,
            limit: int = 10,
    ) -> list[dict]:
        """
        Получить рекомендации книг для пользователя.

        Args:
            user_id: ID пользователя
            limit: Сколько книг рекомендовать

        Returns:
            [
                {
                    "book": {id, title, author, description},
                    "similarity": float,
                    "reason": str,
                },
                ...
            ]

        Raises:
            NotFoundError: Если нет Taste Profile, заметок или эмбеддингов
        """
        logger.info(f"Getting recommendations for user {user_id}, limit={limit}")

        # 1. Taste Profile (должен быть готов)
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundError("TasteProfile", user_id)
        if profile.status != "done":
            raise NotFoundError(
                "TasteProfile",
                user_id,
                details={"status": profile.status, "hint": "Run POST /taste-profile/analyze"},
            )

        # 2. Прочитанные книги (исключаем)
        entries = await self.entry_repo.get_by_user_id(user_id, limit=1000)
        if not entries:
            raise NotFoundError("ReadingEntries", user_id)
        read_book_ids = [e.book_id for e in entries]

        # 3. Усреднить эмбеддинги всех заметок → «вектор вкуса»
        embeddings = [e.note_embedding for e in entries if e.note_embedding]
        if not embeddings:
            raise NotFoundError("NoteEmbeddings", user_id)

        avg_embedding = self._average_embeddings(embeddings)
        logger.debug(f"Averaged {len(embeddings)} embeddings for user {user_id}")

        # 4. Найти похожие книги через pgvector
        similar_books = await self.book_repo.find_similar_by_embedding(
            embedding=avg_embedding,
            exclude_book_ids=read_book_ids,
            limit=limit,
            min_similarity=0.3,
        )

        if not similar_books:
            logger.warning(f"No similar books for user {user_id}")
            return []

        # 5. Формируем рекомендации с reason
        recommendations = self._format_recommendations(similar_books)
        logger.info(f"Found {len(recommendations)} recommendations for user {user_id}")
        return recommendations

    def _format_recommendations(
            self,
            books_with_scores: list[tuple[BookEntity, float]],
    ) -> list[dict]:
        """Формируем рекомендации с reason на основе score."""
        return [
            {
                "book": {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "description": book.description,
                },
                "similarity": round(score, 3),
                "reason": self._generate_reason(book, score),
            }
            for book, score in books_with_scores
        ]

    def _generate_reason(self, book: BookEntity, score: float) -> str:
        """
        Генерация причины на основе similarity score.

        Градации:
        - 0.85+ : очень высокая близость
        - 0.75+ : высокая близость
        - 0.65+ : средняя близость
        - ниже : слабая близость
        """
        if score >= 0.85:
            return "Очень близка к вашим любимым книгам — высокое совпадение по стилю и темам"
        elif score >= 0.75:
            return "Совпадает с вашим вкусом по темам и настроению"
        elif score >= 0.65:
            return "Может вам понравиться — есть общие мотивы с прочитанным"
        else:
            return "Интересная книга в вашем направлении"

    @staticmethod
    def _average_embeddings(embeddings: list[list[float]]) -> list[float]:
        """
        Усреднить эмбеддинги покомпонентно (pure Python, без numpy).

        Args:
            embeddings: [[0.1, 0.2, ...], [0.3, 0.4, ...], ...] — N × dim

        Returns:
            [0.2, 0.3, ...] — усреднённый вектор
        """
        if not embeddings:
            raise ValueError("No embeddings to average")

        n = len(embeddings)
        dim = len(embeddings[0])

        result = [0.0] * dim
        for emb in embeddings:
            for i, val in enumerate(emb):
                result[i] += val

        return [x / n for x in result]