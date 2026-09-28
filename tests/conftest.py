"""
Общие fixtures для всех тестов.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport

from app.main import app


# ============ Event Loop ============

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Один event loop на всю сессию тестов.
    
    Нужен, чтобы async-фикстуры работали корректно.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============ HTTP Client (E2E) ============

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP-клиент для E2E-тестов.
    
    Использует ASGITransport — не поднимает реальный сервер.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac
