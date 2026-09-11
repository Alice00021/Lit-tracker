from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.interfaces.schemas.book import BookCreateSchema, BookUpdateSchema, BookReadSchema, BookPaginatedSchema
from app.application.services.book_service import BookService
from app.interfaces.api.dependencies import get_book_service
from app.domain.exceptions import NotFoundError

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=BookReadSchema, status_code=status.HTTP_201_CREATED)
async def create_book(data: BookCreateSchema, service: BookService = Depends(get_book_service)):
    book = await service.create_book(data)
    return BookReadSchema.model_validate(book, from_attributes=True)


@router.get("", response_model=BookPaginatedSchema)
async def list_books(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        service: BookService = Depends(get_book_service),
):
    return await service.list_books(page, page_size)


@router.get("/{book_id}", response_model=BookReadSchema)
async def get_book(id: int, service: BookService = Depends(get_book_service)):
    try:
        book = await service.get_book(id)
        return BookReadSchema.model_validate(book, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.patch("/{book_id}", response_model=BookReadSchema)
async def update_book(id: int, data: BookUpdateSchema, service: BookService = Depends(get_book_service)):
    try:
        book = await service.update_book(id, data)
        return BookReadSchema.model_validate(book, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(id: int, service: BookService = Depends(get_book_service)):
    try:
        await service.delete_book(id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))