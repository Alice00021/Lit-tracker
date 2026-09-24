from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.recommendation_service import RecommendationService
from app.interfaces.api.dependencies import get_recommendation_service
from app.interfaces.schemas.recommendation import RecommendationsResponseSchema
from app.domain.exceptions import NotFoundError

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

CURRENT_USER_ID = 1


@router.get("", response_model=RecommendationsResponseSchema)
async def get_recommendations(
        limit: int = Query(10, ge=1, le=50),
        service: RecommendationService = Depends(get_recommendation_service),
):
    """
    Получить рекомендации книг.
    """
    try:
        recommendations = await service.get_recommendations(
            CURRENT_USER_ID,
            limit=limit,
        )
        return {
            "recommendations": recommendations,
            "total": len(recommendations),
        }
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))