import random
from typing import List
from app.core.config import settings
from common import get_logger

logger = get_logger(__name__)


class EmbeddingClient:
    """
    Клиент для генерации эмбеддингов.

    Сейчас — МОК (случайный вектор).
    Потом заменим на реальный OpenAI API.
    """

    def __init__(self):
        self.dimension = settings.OPENAI_EMBEDDING_DIMENSION
        self.model = settings.OPENAI_EMBEDDING_MODEL
        logger.warning(
            f"⚠️ EmbeddingClient using MOCK mode "
            f"(dimension={self.dimension}, model={self.model})"
        )

    async def get_embedding(self, text: str) -> List[float]:
        """Получить эмбеддинг для текста (МОК)."""
        if not text or not text.strip():
            return [0.0] * self.dimension

        # Генерируем случайный вектор и нормализуем (unit vector)
        vec = [random.gauss(0, 1) for _ in range(self.dimension)]
        norm = sum(x * x for x in vec) ** 0.5
        return [x / norm for x in vec] if norm > 0 else vec

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Получить эмбеддинги для списка текстов."""
        return [await self.get_embedding(t) for t in texts]