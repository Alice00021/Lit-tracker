from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.infrastructure.database.repositories.book_repository import SqlAlchemyBookRepository
from app.infrastructure.llm.embedding_client import EmbeddingClient
from app.domain.interfaces.book_repository import IBookRepository
from app.application.services.book_service import BookService


async def get_book_repository(session: AsyncSession = Depends(get_session)) -> IBookRepository:
    return SqlAlchemyBookRepository(session)


async def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()


async def get_book_service(
        repo: IBookRepository = Depends(get_book_repository),
        embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> BookService:
    return BookService(repo, embedding_client)