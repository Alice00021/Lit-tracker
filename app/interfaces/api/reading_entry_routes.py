from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.reading_entry_service import ReadingEntryService
from app.interfaces.api.dependencies import get_reading_entry_service
from app.interfaces.schemas.reading_entry import (
    ReadingEntryCreateSchema,
    ReadingEntryUpdateSchema,
    ReadingEntryReadSchema,
    ReadingEntryPaginatedSchema,
)
from app.domain.exceptions import NotFoundError

router = APIRouter(prefix="/books/entries", tags=["reading-entries"])

# Временно, пока нет авторизации
CURRENT_USER_ID = 1


@router.post(
    "",
    response_model=ReadingEntryReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_entry(
        data: ReadingEntryCreateSchema,
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """
    Добавить запись о прочитанной книге.

    - Генерирует эмбеддинги заметки и книги через OpenAI
    - Создаёт книгу или находит существующую
    - Возвращает созданную запись
    """
    entry = await service.create_entry(CURRENT_USER_ID, data)
    return ReadingEntryReadSchema.model_validate(entry, from_attributes=True)


@router.get("", response_model=ReadingEntryPaginatedSchema)
async def list_entries(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """Список записей текущего пользователя с пагинацией."""
    return await service.list_entries(CURRENT_USER_ID, page, page_size)


@router.get("/{entry_id}", response_model=ReadingEntryReadSchema)
async def get_entry(
        entry_id: int,
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """Получить запись по ID."""
    try:
        entry = await service.get_entry(entry_id)
        return ReadingEntryReadSchema.model_validate(entry, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.patch("/{entry_id}", response_model=ReadingEntryReadSchema)
async def update_entry(
        entry_id: int,
        data: ReadingEntryUpdateSchema,
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """
    Обновить запись.

    Если изменилась заметка — пересчитывается эмбеддинг.
    """
    try:
        entry = await service.update_entry(entry_id, data)
        return ReadingEntryReadSchema.model_validate(entry, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
        entry_id: int,
        service: ReadingEntryService = Depends(get_reading_entry_service),
):
    """Удалить запись (soft delete)."""
    try:
        await service.delete_entry(entry_id)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))