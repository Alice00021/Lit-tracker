"""
Фикстуры e2e-тестов: настоящее приложение (lifespan, Postgres, Redis, чекпоинтер),
но без внешнего Ollama — эмбеддинги и LLM подменены заглушками.

Пользователи создаются через настоящий /auth/register + /auth/login.

Нужны: Postgres с pgvector и применённые миграции (alembic upgrade head +
python -m scripts.setup_checkpointer), Redis. Адреса — из DATABASE_URL / REDIS_URL.
"""
import random
import uuid
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.infrastructure.llm.langgraph import nodes
from app.interfaces.api.dependencies import get_embedding_client
from app.main import app

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


PASSWORD = "E2e-Passw0rd!"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def running_app():
    """Приложение с реальным lifespan: Redis, чекпоинт LangGraph, цикл восстановления."""
    async with app.router.lifespan_context(app):
        yield app


def _http(running_app, headers=None) -> AsyncClient:
    # У каждого клиента свой «IP» (X-Real-IP): счётчики лимитов не мешают друг другу
    # и не копятся между запусками.
    ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
    return AsyncClient(
        transport=ASGITransport(app=running_app),
        base_url="http://test",
        headers={"X-Real-IP": ip, **(headers or {})},
    )


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(running_app) -> dict:
    """Новый пользователь: регистрация + вход. Возвращает email, пароль, токены, заголовки."""
    email = f"e2e-{uuid.uuid4().hex[:10]}@example.com"
    async with _http(running_app) as ac:
        r = await ac.post("/auth/register", json={"email": email, "password": PASSWORD})
        assert r.status_code == 201, r.text
        r = await ac.post("/auth/login", data={"username": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        tokens = r.json()
    return {
        "email": email,
        "password": PASSWORD,
        "tokens": tokens,
        "headers": auth_headers(tokens),
    }


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def user_a(running_app) -> dict:
    return await _register_and_login(running_app)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def user_b(running_app) -> dict:
    return await _register_and_login(running_app)


@pytest_asyncio.fixture(loop_scope="session")
async def fresh_user(running_app) -> dict:
    """Новый пользователь на один тест: для сценариев, где токены отзываются."""
    return await _register_and_login(running_app)


@pytest_asyncio.fixture(loop_scope="session")
async def _fakes(monkeypatch):
    FakeLLM.fail = False
    monkeypatch.setattr(nodes, "LLMClient", FakeLLM)
    monkeypatch.setattr(settings, "TASTE_RETRY_BACKOFF_SECONDS", 0)
    app.dependency_overrides[get_embedding_client] = FakeEmbeddingClient
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def client(running_app, user_a, _fakes) -> AsyncGenerator[AsyncClient, None]:
    """Клиент, авторизованный как user_a."""
    async with _http(running_app, user_a["headers"]) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def other_client(running_app, user_b, _fakes) -> AsyncGenerator[AsyncClient, None]:
    """Клиент, авторизованный как user_b (другой пользователь)."""
    async with _http(running_app, user_b["headers"]) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def anon_client(running_app) -> AsyncGenerator[AsyncClient, None]:
    """Клиент без токена."""
    async with _http(running_app) as ac:
        yield ac
