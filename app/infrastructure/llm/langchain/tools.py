"""
LangChain tools для агента.

Каждый tool — функция, которую LLM может вызвать.
Обёрнута через @tool для LangChain.
"""
from langchain_core.tools import tool

from app.infrastructure.database.repositories.book_repository import (
    SqlAlchemyBookRepository,
)
from app.infrastructure.llm.embedding_client import embedding_service
from app.core.database import AsyncSessionLocal
from common import get_logger

logger = get_logger(__name__)


@tool
async def search_similar_books(query: str, limit: int = 5) -> str:
    """
    Найти книги, семантически похожие на запрос.

    Используй, когда пользователь описывает ЧТО он хочет читать
    (темы, настроение, атмосфера, сюжет).

    Args:
        query: Текстовое описание (например, "грустное про потерю")
        limit: Сколько книг вернуть (по умолчанию 5)

    Returns:
        Список книг в текстовом формате.
    """
    logger.info(f"Tool: search_similar_books('{query}', limit={limit})")

    try:
        # 1. Эмбеддинг запроса
        embedding = await embedding_service.get_embedding(query)

        # 2. Поиск через pgvector
        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyBookRepository(session)
            similar = await repo.find_similar_by_embedding(
                embedding=embedding,
                exclude_book_ids=[],
                limit=limit,
                min_similarity=0.3,
            )

        if not similar:
            return "Не нашёл книг по этому запросу."

        # 3. Форматируем в текст (LLM лучше понимает текст, чем JSON)
        lines = []
        for book, score in similar:
            lines.append(
                f"- {book.title} ({book.author}) — "
                f"similarity: {score:.2f}. "
                f"Описание: {book.description or 'нет'}"
            )

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"search_similar_books failed: {e}")
        return f"Ошибка поиска: {str(e)}"


@tool
async def filter_books_by_author(author: str, limit: int = 10) -> str:
    """
    Найти книги конкретного автора.

    Используй, когда пользователь упоминает имя автора.

    Args:
        author: Имя автора (например, "Сартр", "Кафка")
        limit: Сколько книг вернуть (по умолчанию 10)

    Returns:
        Список книг автора в текстовом формате.
    """
    logger.info(f"Tool: filter_books_by_author('{author}')")

    try:
        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyBookRepository(session)
            all_books = await repo.get_all(limit=1000, offset=0)

        # Фильтруем по автору
        matched = [
                      b for b in all_books
                      if author.lower() in b.author.lower()
                  ][:limit]

        if not matched:
            return f"Книг автора '{author}' не найдено."

        lines = [
            f"- {book.title} ({book.author})"
            for book in matched
        ]
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"filter_books_by_author failed: {e}")
        return f"Ошибка поиска по автору: {str(e)}"


@tool
async def get_all_books(limit: int = 20) -> str:
    """
    Получить все книги в каталоге.

    Используй, когда нужен общий обзор или когда другие tools не подходят.

    Args:
        limit: Сколько книг вернуть (по умолчанию 20)

    Returns:
        Список книг в текстовом формате.
    """
    logger.info(f"Tool: get_all_books(limit={limit})")

    try:
        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyBookRepository(session)
            books = await repo.get_all(limit=limit, offset=0)

        if not books:
            return "Каталог пуст."

        lines = [
            f"- {book.title} ({book.author})"
            for book in books
        ]
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"get_all_books failed: {e}")
        return f"Ошибка: {str(e)}"


# Список всех tools для агента
ALL_TOOLS = [
    search_similar_books,
    filter_books_by_author,
    get_all_books,
]