from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.infrastructure.database.repositories.book_repository import (
    SqlAlchemyBookRepository,
)
from app.infrastructure.database.repositories.reading_entry_repository import (
    SqlAlchemyReadingEntryRepository,
)
from app.infrastructure.llm.embedding_client import EmbeddingClient
from app.domain.interfaces.book_repository import IBookRepository
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.application.services.book_service import BookService
from app.application.services.reading_entry_service import ReadingEntryService


# Repositories

async def get_book_repository(
        session: AsyncSession = Depends(get_session),
) -> IBookRepository:
    return SqlAlchemyBookRepository(session)


async def get_reading_entry_repository(
        session: AsyncSession = Depends(get_session),
) -> IReadingEntryRepository:
    return SqlAlchemyReadingEntryRepository(session)


# Clients

async def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()


# Services

async def get_book_service(
        book_repo: IBookRepository = Depends(get_book_repository),
        embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> BookService:
    return BookService(book_repo, embedding_client)


async def get_reading_entry_service(
        entry_repo: IReadingEntryRepository = Depends(get_reading_entry_repository),
        book_repo: IBookRepository = Depends(get_book_repository),
        embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> ReadingEntryService:
    return ReadingEntryService(entry_repo, book_repo, embedding_client)