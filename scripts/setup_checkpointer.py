"""Создать таблицы чекпоинтера LangGraph. Запускается после alembic в сервисе migrate."""
import asyncio

from app.core.config import settings
from app.infrastructure.llm.langgraph.checkpointer import setup_checkpointer_tables

if __name__ == "__main__":
    asyncio.run(setup_checkpointer_tables(settings.DATABASE_URL))
    print("LangGraph checkpointer tables are ready")
