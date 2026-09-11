from app.domain.interfaces.book_repository import IBookRepository
from app.domain.entities.book import BookEntity
from app.domain.exceptions import NotFoundError
from app.interfaces.schemas.book import BookCreateSchema, BookUpdateSchema


class BookService:
    def __init__(self, repo: IBookRepository, embedding_client):
        self.repo = repo
        self.embedding_client = embedding_client

    async def create_book(self, data: BookCreateSchema) -> BookEntity:
        text = f"{data.title} {data.author} {data.description or ''}"
        embedding = await self.embedding_client.get_embedding(text)
        book = BookEntity(
            id=None, title=data.title, author=data.author,
            description=data.description, embedding=embedding,
        )
        return await self.repo.create(book)

    async def get_book(self, id: int) -> BookEntity:
        book = await self.repo.get_by_id(id)
        if not book:
            raise NotFoundError("Book", id)
        return book

    async def update_book(self, id: int, data: BookUpdateSchema) -> BookEntity:
        book = await self.get_book(id)
        if data.title is not None:
            book.title = data.title
        if data.author is not None:
            book.author = data.author
        if data.description is not None:
            book.description = data.description
        return await self.repo.update(book)

    async def delete_book(self, id: int) -> None:
        await self.get_book(id)
        await self.repo.soft_delete(id)

    async def list_books(self, page: int, page_size: int) -> dict:
        offset = (page - 1) * page_size
        items = await self.repo.get_all(limit=page_size, offset=offset)
        total = await self.repo.count()
        return {
            "items": items, "total": total, "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1)
        }