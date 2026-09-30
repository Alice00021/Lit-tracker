from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


def to_psycopg_url(database_url: str) -> str:
    """postgresql+asyncpg://... (SQLAlchemy) -> postgresql://... (psycopg)."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _pool(database_url: str, max_size: int) -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=to_psycopg_url(database_url),
        min_size=1,
        max_size=max_size,
        # требования AsyncPostgresSaver: autocommit и dict_row
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )


@asynccontextmanager
async def open_checkpointer(database_url: str, max_size: int = 5):
    """Чекпоинтер LangGraph в Postgres (пул соединений живёт, пока открыт контекст)."""
    pool = _pool(database_url, max_size)
    await pool.open()
    try:
        yield AsyncPostgresSaver(pool)
    finally:
        await pool.close()


async def setup_checkpointer_tables(database_url: str) -> None:
    """Создать таблицы чекпоинтера (идемпотентно). Вызывать один раз, из миграций."""
    async with open_checkpointer(database_url, max_size=1) as saver:
        await saver.setup()
