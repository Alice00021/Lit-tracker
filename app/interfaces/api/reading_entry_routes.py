from common import AuthenticatedUser
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.reading_entry_service import ReadingEntryService
from app.core.security import get_current_user
from app.domain.exceptions import NotFoundError
from app.interfaces.api.dependencies import get_reading_entry_service
from app.interfaces.schemas.reading_entry import (
    ReadingEntryCreateSchema,
    ReadingEntryPaginatedSchema,
    ReadingEntryReadSchema,
    ReadingEntryUpdateSchema,
)

router = APIRouter(prefix="/books", tags=["reading-entries"])

@router.post(
    "/{book_id}/entries",
    response_model=ReadingEntryReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_entry_for_book(
        book_id: int,
        data: ReadingEntryCreateSchema,
        user: AuthenticatedUser = Depends(get_current_user),
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """
    Добавить запись о прочитанной книге.

    - book_id передаётся через URL
    - Генерирует эмбеддинг заметки
    - Возвращает созданную запись
    """
    try:
        entry = await service.create_entry(user.id, book_id, data)
        return ReadingEntryReadSchema.model_validate(entry, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))

@router.get("/entries", response_model=ReadingEntryPaginatedSchema)
async def list_entries(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        user: AuthenticatedUser = Depends(get_current_user),
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """Список записей текущего пользователя с пагинацией."""
    return await service.list_entries(user.id, page, page_size)

@router.get("/entries/{entry_id}", response_model=ReadingEntryReadSchema)
async def get_entry(
        entry_id: int,
        user: AuthenticatedUser = Depends(get_current_user),
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """Получить запись по ID."""
    try:
        entry = await service.get_entry(entry_id, user.id)
        return ReadingEntryReadSchema.model_validate(entry, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.patch("/entries/{entry_id}", response_model=ReadingEntryReadSchema)
async def update_entry(
        entry_id: int,
        data: ReadingEntryUpdateSchema,
        user: AuthenticatedUser = Depends(get_current_user),
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """
    Обновить запись.

    Если изменилась заметка — пересчитывается эмбеддинг.
    """
    try:
        entry = await service.update_entry(entry_id, user.id, data)
        return ReadingEntryReadSchema.model_validate(entry, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
        entry_id: int,
        user: AuthenticatedUser = Depends(get_current_user),
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """Удалить запись (soft delete)."""
    try:
        await service.delete_entry(entry_id, user.id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))