import hashlib
import re

from common import RedisCache, get_logger
from app.infrastructure.llm.langchain.agent import smart_search_agent
from app.interfaces.schemas.smart_search import (
    SmartSearchRequest,
    SmartSearchResponse,
)

logger = get_logger(__name__)


class SmartSearchService:
    """Сервис умного поиска с кэшем."""

    def __init__(self):
        self.cache = RedisCache(prefix="search", default_ttl=3600)

    def _normalize_query(self, query: str) -> str:
        """Нормализация запроса."""
        query = query.strip().lower()
        query = " ".join(query.split())             # убрать кратные пробелы
        query = re.sub(r'[^\w\s]', '', query)      # убрать пунктуацию
        return query

    def _make_cache_key(self, query: str) -> str:
        """Стабильный ключ."""
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()

    async def search(self, request: SmartSearchRequest) -> SmartSearchResponse:
        """Выполнить умный поиск."""
        cache_key = self._make_cache_key(request.query)

        # Проверяем кэш
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info(f"CACHE HIT: '{request.query}'")
            return SmartSearchResponse(**cached)

        logger.info(f"CACHE MISS: '{request.query}'")

        # LLM
        result = await smart_search_agent.search(request.query)

        # Формируем ответ
        response = SmartSearchResponse(
            query=result["query"],
            answer=result["answer"],
        )

        # Сохраняем в кэш
        await self.cache.set(cache_key, response.model_dump())

        return response