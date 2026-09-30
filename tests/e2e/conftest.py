"""
Фикстуры e2e-тестов: настоящее приложение (lifespan, Postgres, Redis, чекпоинтер),
но без внешнего Ollama — эмбеддинги и LLM подменены заглушками.

Нужны: Postgres с pgvector и применённые миграции (alembic upgrade head +
python -m scripts.setup_checkpointer), Redis. Адреса — из DATABASE_URL / REDIS_URL.
"""
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.infrastructure.llm.langgraph import nodes
from app.interfaces.api.dependencies import get_embedding_client
from app.main import app
from scripts.seed import seed_users

VALID_ANALYSIS = {
    "themes": ["sci-fi", "politics"],
    "style": "epic",
    "summary": "Любит масштабные миры",
    "loves": ["worldbuilding"],
    "dislikes": [],
}


class FakeEmbeddingClient:
    async def get_embedding(self, text: str) -> list[float]:
        return [1.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 1)


class FakeLLM:
    """LLM-заглушка; поведение переключается через FakeLLM.fail."""

    fail = False

    async def analyze_taste(self, notes, feedback=None):
        if FakeLLM.fail:
            raise RuntimeError("Ollama is down")
        return VALID_ANALYSIS


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def running_app():
    """Приложение с реальным lifespan: Redis, чекпоинтер LangGraph, цикл восстановления."""
    async with app.router.lifespan_context(app):
        await seed_users()  # роуты работают от user_id=1
        yield app


@pytest_asyncio.fixture(loop_scope="session")
async def client(running_app, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    FakeLLM.fail = False
    monkeypatch.setattr(nodes, "LLMClient", FakeLLM)
    monkeypatch.setattr(settings, "TASTE_RETRY_BACKOFF_SECONDS", 0)
    app.dependency_overrides[get_embedding_client] = FakeEmbeddingClient

    transport = ASGITransport(app=running_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
