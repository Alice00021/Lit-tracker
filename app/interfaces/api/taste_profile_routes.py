from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.application.services.taste_profile_service import TasteProfileService
from app.interfaces.api.dependencies import get_taste_profile_service
from app.interfaces.schemas.taste_profile import TasteProfileReadSchema
from app.domain.exceptions import NotFoundError

router = APIRouter(prefix="/taste-profile", tags=["taste-profile"])

CURRENT_USER_ID = 1


@router.post(
    "/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
)
async def analyze_taste(
        background_tasks: BackgroundTasks,
        service: TasteProfileService = Depends(get_taste_profile_service),
):
    """
    Запустить анализ вкуса (async).

    Возвращает сразу 202 Accepted.
    Анализ выполняется в фоне.
    Проверить результат: GET /taste-profile
    """
    # 1. Создать запись со статусом pending
    await service.start_analysis(CURRENT_USER_ID)

    # 2. Запустить в фоне
    background_tasks.add_task(service.run_analysis, CURRENT_USER_ID)

    return {
        "status": "processing",
        "message": "Analysis started. Check GET /taste-profile",
    }


@router.get("", response_model=TasteProfileReadSchema)
async def get_taste_profile(
        service: TasteProfileService = Depends(get_taste_profile_service),
):
    try:
        profile = await service.get_profile(CURRENT_USER_ID)
        return TasteProfileReadSchema.model_validate(profile, from_attributes=True)
    except NotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))