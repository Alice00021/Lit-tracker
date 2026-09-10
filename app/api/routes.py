from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.reading_service import ReadingService
from app.schemas.reading_entry import ReadingEntryResponseSchema
from common import get_logger, AppException

@router.get("/entries", response_model=List[ReadingEntryResponseSchema])
async def get_reading_entries(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    service = ReadingService(db)
    return await service.get_reading_entries(CURRENT_USER_ID, limit, offset)