from typing import Optional
from app.domain.entities.reading_entry import ReadingEntryEntity
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.domain.interfaces.book_repository import IBookRepository
from app.domain.exceptions import NotFoundError
from app.infrastructure.llm.embedding_client import EmbeddingClient
from app.interfaces.schemas.reading_entry import (
    ReadingEntryCreateSchema,
    ReadingEntryUpdateSchema,
)
from common import get_logger

logger = get_logger(__name__)


class ReadingEntryService:

    def __init__(
            self,
            entry_repo: IReadingEntryRepository,
            book_repo: IBookRepository,
            embedding_client: EmbeddingClient,
    ):
        self.entry_repo = entry_repo
        self.book_repo = book_repo
        self.embedding_client = embedding_client


    async def create_entry(
            self,
            user_id: int,
            data: ReadingEntryCreateSchema,
    ) -> ReadingEntryEntity:
        """
        Создать запись о чтении.

        Шаги:
        1. Сгенерировать эмбеддинг заметки
        2. Найти или создать книгу (с эмбеддингом)
        3. Создать запись
        """
        logger.info(f"Creating entry for user {user_id}: {data.book_title}")

        #  Эмбеддинг заметки
        note_embedding = await self.embedding_client.get_embedding(data.note)

        #  Эмбеддинг книги
        book_text = f"{data.book_title} {data.book_author}"
        if data.book_description:
            book_text += f" {data.book_description}"
        book_embedding = await self.embedding_client.get_embedding(book_text)

        #  Найти или создать книгу
        book = await self.book_repo.create(
            title=data.book_title,
            author=data.book_author,
            description=data.book_description,
            embedding=book_embedding,
        )

        #  Создать запись
        entry = ReadingEntryEntity(
            id=None,
            user_id=user_id,
            book_id=book.id,
            note=data.note,
            note_embedding=note_embedding,
            read_date=data.read_date,
            rating=data.rating,
            book=book,
        )

        result = await self.entry_repo.create(entry)
        logger.info(f"Entry created: {result.id}")
        return result


    async def get_entry(self, id: int) -> ReadingEntryEntity:
        entry = await self.entry_repo.get_by_id(id)
        if not entry:
            raise NotFoundError("ReadingEntry", id)
        return entry

    async def list_entries(
            self,
            user_id: int,
            page: int = 1,
            page_size: int = 20,
    ) -> dict:

        logger.info(f"Listing entries for user {user_id}, page={page}")

        offset = (page - 1) * page_size

        items = await self.entry_repo.get_by_user_id(
            user_id,
            limit=page_size,
            offset=offset,
        )
        total = await self.entry_repo.count_by_user(user_id)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }


    async def update_entry(
            self,
            entry_id: int,
            data: ReadingEntryUpdateSchema,
    ) -> ReadingEntryEntity:
        """Обновить запись."""
        entry = await self.get_entry(entry_id)

        # Если заметка изменилась — пересчитать эмбеддинг
        if data.note is not None and data.note != entry.note:
            logger.info(f"Note changed, re-generating embedding")
            entry.note = data.note
            entry.note_embedding = await self.embedding_client.get_embedding(data.note)

        if data.read_date is not None:
            entry.read_date = data.read_date

        if data.rating is not None:
            entry.rating = data.rating

        return await self.entry_repo.update(entry)


    async def delete_entry(self, entry_id: int) -> None:
        await self.get_entry(entry_id)  # проверка на существование
        await self.entry_repo.delete(entry_id)
        logger.info(f"Entry deleted: {entry_id}")