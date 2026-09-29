from common import get_logger
from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.smart_search_service import SmartSearchService
from app.interfaces.api.dependencies import get_smart_search_service
from app.interfaces.schemas.smart_search import (
    SmartSearchRequest,
    SmartSearchResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/books/search", tags=["smart-search"])


@router.post(
    "/smart",
    response_model=SmartSearchResponse,
    status_code=status.HTTP_200_OK,
)
async def smart_search(
        request: SmartSearchRequest,
        service: SmartSearchService = Depends(get_smart_search_service),
):
    """
    Умный поиск книг через LangChain Agent.

    Понимает запросы в свободной форме:
    - "хочу что-то грустное про потерю"
    - "книги Сартра"
    - "философские романы про смысл жизни"
    """
    try:
        return await service.search(request)
    except Exception as e:
        logger.error(f"Smart search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )