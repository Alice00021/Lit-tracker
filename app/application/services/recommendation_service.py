from typing import Optional
from app.domain.entities.book import BookEntity
from app.domain.interfaces.book_repository import IBookRepository
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.domain.interfaces.taste_profile_repository import ITasteProfileRepository
from common.exceptions import NotFoundError
from app.infrastructure.llm.llm_client import LLMClient
from common import get_logger

logger = get_logger(__name__)


class RecommendationService:
    """
    Сервис рекомендаций книг.

    Логика:
    1. Получить Taste Profile (анализ вкуса через LLM)
    2. Получить прочитанные книги
    3. Усреднить эмбеддинги всех заметок - «вектор вкуса»
    4. Найти похожие книги через pgvector (top-N)
    5. LLM: объяснить, почему каждая книга подходит
    """

    def __init__(
            self,
            book_repo: IBookRepository,
            entry_repo: IReadingEntryRepository,
            profile_repo: ITasteProfileRepository,
            llm_client: LLMClient,
    ):
        self.book_repo = book_repo
        self.entry_repo = entry_repo
        self.profile_repo = profile_repo
        self.llm_client = llm_client

    async def get_recommendations(
            self,
            user_id: int,
            limit: int = 10,
            explain: bool = True,
    ) -> list[dict]:
        """
        Получить рекомендации книг для пользователя.

        Args:
            user_id: ID пользователя
            limit: Сколько книг рекомендовать
            explain: Использовать ли LLM для объяснений

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
        if explain:
            # LLM: объяснить, почему каждая подходит
            recommendations = await self._explain_with_llm(
                books_with_scores=similar_books,
                taste_analysis=profile.analysis,
            )
        else:
            # Просто similarity score
            recommendations = self._format_simple(similar_books)

        logger.info(f"Found {len(recommendations)} recommendations for user {user_id}")
        return recommendations

    async def _explain_with_llm(
            self,
            books_with_scores: list[tuple[BookEntity, float]],
            taste_analysis: dict,
    ) -> list[dict]:
        """
        Объяснить через LLM, почему каждая книга подходит.

        Один вызов LLM для всех книг — batch.
        """
        if not books_with_scores:
            return []

        # Формируем промпт
        books_text = "\n".join(
            f"{i+1}. \"{book.title}\" — {book.author} "
            f"(описание: {book.description or 'нет'}, similarity: {score:.2f})"
            for i, (book, score) in enumerate(books_with_scores)
        )

        prompt = f"""Пользователь имеет следующий профиль вкуса:
{self._format_taste_analysis(taste_analysis)}

Мы нашли {len(books_with_scores)} книг, которые могут ему понравиться:
{books_text}

Для каждой книги напиши краткое объяснение (1 предложение), почему она подходит под вкус пользователя.
Учти его любимые темы, стиль и то, что он ценит.

Верни ТОЛЬКО JSON массив без markdown:
[
  {{"index": 1, "reason": "Почему книга 1 подходит..."}},
  {{"index": 2, "reason": "Почему книга 2 подходит..."}}
]
"""

        try:
            # Вызов LLM (без structured output — свободный текст)
            explanation = await self.llm_client._call_llm(prompt)

            # Парсим
            import json
            reasons_data = json.loads(explanation)
            reasons_map = {item["index"]: item["reason"] for item in reasons_data}

            # Формируем ответ
            recommendations = []
            for i, (book, score) in enumerate(books_with_scores, start=1):
                recommendations.append({
                    "book": {
                        "id": book.id,
                        "title": book.title,
                        "author": book.author,
                        "description": book.description,
                    },
                    "similarity": round(score, 3),
                    "reason": reasons_map.get(i, f"Похожа на ваши прочитанные книги (score: {score:.2f})"),
                })
            return recommendations

        except Exception as e:
            logger.error(f"LLM explanation failed: {e}")
            # Fallback — без объяснений
            return self._format_simple(books_with_scores)

    def _format_simple(
            self,
            books_with_scores: list[tuple[BookEntity, float]],
    ) -> list[dict]:
        """Простой формат без LLM."""
        return [
            {
                "book": {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "description": book.description,
                },
                "similarity": round(score, 3),
                "reason": f"Похожа на ваши прочитанные книги (score: {score:.2f})",
            }
            for book, score in books_with_scores
        ]

    def _format_taste_analysis(self, analysis: dict) -> str:
        """Форматировать taste analysis для промпта."""
        if not analysis:
            return "Профиль вкуса недоступен"

        parts = []
        if analysis.get("themes"):
            parts.append(f"Любимые темы: {', '.join(analysis['themes'])}")
        if analysis.get("style"):
            parts.append(f"Стиль: {analysis['style']}")
        if analysis.get("loves"):
            parts.append(f"Что нравится: {', '.join(analysis['loves'])}")
        if analysis.get("dislikes"):
            parts.append(f"Что не нравится: {', '.join(analysis['dislikes'])}")
        if analysis.get("summary"):
            parts.append(f"Общее: {analysis['summary']}")

        return "\n".join(parts)

    @staticmethod
    def _average_embeddings(embeddings: list[list[float]]) -> list[float]:
        """
        Усреднить эмбеддинги покомпонентно.

        Args:
            embeddings: [[0.1, 0.2, ...], [0.3, 0.4, ...], ...] — N × dim

        Returns:
            [0.2, 0.3, ...] — усреднённый вектор
        """
        if not embeddings:
            raise ValueError("No embeddings to average")

        import numpy as np
        arr = np.array(embeddings)              # shape (N, dim)
        avg = np.mean(arr, axis=0)              # (dim,)
        return avg.tolist()