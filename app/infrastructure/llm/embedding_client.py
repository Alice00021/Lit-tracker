import httpx
from typing import List
from app.core.config import settings
from common import get_logger, ServiceError

logger = get_logger(__name__)


class EmbeddingClient:
    """
    Клиент для генерации эмбеддингов через Ollama API.
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        logger.info(
            f"✅ Ollama EmbeddingClient: {self.model} (dim={self.dimension})"
        )

    async def get_embedding(self, text: str) -> List[float]:
        """Получить эмбеддинг для текста."""
        if not text or not text.strip():
            return [0.0] * self.dimension

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text.strip(),
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["embedding"]

        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise ServiceError(f"Failed to call Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise ServiceError(f"Failed to generate embedding: {str(e)}")