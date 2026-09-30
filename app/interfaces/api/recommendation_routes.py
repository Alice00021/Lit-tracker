from common import AuthenticatedUser
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.services.recommendation_service import RecommendationService
from app.core.security import get_current_user
from app.domain.exceptions import NotFoundError
from app.interfaces.api.dependencies import get_recommendation_service
from app.interfaces.schemas.recommendation import RecommendationsResponseSchema

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationsResponseSchema)
async def get_recommendations(
        limit: int = Query(10, ge=1, le=50),
        user: AuthenticatedUser = Depends(get_current_user),
        service: RecommendationService = Depends(get_recommendation_service),
):
    """
    Получить рекомендации книг.
    """
    try:
        recommendations = await service.get_recommendations(
            user.id,
            limit=limit,
        )
        return {
            "recommendations": recommendations,
            "total": len(recommendations),
        }
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))