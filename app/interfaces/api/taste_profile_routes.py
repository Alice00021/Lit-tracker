from common import AuthenticatedUser
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.application.services.taste_profile_service import TasteProfileService
from app.core.security import get_current_user
from app.domain.exceptions import NotFoundError
from app.interfaces.api.dependencies import get_taste_profile_service
from app.interfaces.schemas.taste_profile import TasteProfileReadSchema

router = APIRouter(prefix="/taste-profile", tags=["taste-profile"])


@router.post(
    "/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
)
async def analyze_taste(
        background_tasks: BackgroundTasks,
        user: AuthenticatedUser = Depends(get_current_user),
        service: TasteProfileService = Depends(get_taste_profile_service),
):
    """
    Запустить анализ вкуса (async).

    Возвращает сразу 202 Accepted.
    Анализ выполняется в фоне.
    Проверить результат: GET /taste-profile
    """
    # 1. Создать запись со статусом pending
    await service.start_analysis(user.id)

    # 2. Запустить в фоне
    background_tasks.add_task(service.run_analysis, user.id)

    return {
        "status": "processing",
        "message": "Analysis started. Check GET /taste-profile",
    }


@router.get("", response_model=TasteProfileReadSchema)
async def get_taste_profile(
        user: AuthenticatedUser = Depends(get_current_user),
        service: TasteProfileService = Depends(get_taste_profile_service),
):
    try:
        profile = await service.get_profile(user.id)
        return TasteProfileReadSchema.model_validate(profile, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))