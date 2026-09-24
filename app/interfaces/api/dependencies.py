from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.services.recommendation_service import RecommendationService

from app.core.database import get_session
from app.infrastructure.database.repositories.book_repository import (
    SqlAlchemyBookRepository,
)
from app.infrastructure.database.repositories.reading_entry_repository import (
    SqlAlchemyReadingEntryRepository,
)
from app.infrastructure.database.repositories.taste_profile_repository import (
    SqlAlchemyTasteProfileRepository,
)
from app.infrastructure.llm.embedding_client import EmbeddingClient
from app.infrastructure.llm.llm_client import LLMClient

from app.domain.interfaces.book_repository import IBookRepository
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.domain.interfaces.taste_profile_repository import ITasteProfileRepository

from app.application.services.book_service import BookService
from app.application.services.reading_entry_service import ReadingEntryService
from app.application.services.taste_profile_service import TasteProfileService


# Repositories

async def get_book_repository(
        session: AsyncSession = Depends(get_session),
) -> IBookRepository:
    return SqlAlchemyBookRepository(session)


async def get_reading_entry_repository(
        session: AsyncSession = Depends(get_session),
) -> IReadingEntryRepository:
    return SqlAlchemyReadingEntryRepository(session)


async def get_taste_profile_repository(
        session: AsyncSession = Depends(get_session),
) -> ITasteProfileRepository:
    return SqlAlchemyTasteProfileRepository(session)


# Clients

async def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()


async def get_llm_client() -> LLMClient:
    return LLMClient()


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


async def get_taste_profile_service(
        profile_repo: ITasteProfileRepository = Depends(get_taste_profile_repository),
        entry_repo: IReadingEntryRepository = Depends(get_reading_entry_repository),
        llm_client: LLMClient = Depends(get_llm_client),
) -> TasteProfileService:
    return TasteProfileService(profile_repo, entry_repo, llm_client)

async def get_recommendation_service(
        book_repo: IBookRepository = Depends(get_book_repository),
        entry_repo: IReadingEntryRepository = Depends(get_reading_entry_repository),
        profile_repo: ITasteProfileRepository = Depends(get_taste_profile_repository),
) -> RecommendationService:
    return RecommendationService(book_repo, entry_repo, profile_repo)