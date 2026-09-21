from app.domain.entities.taste_profile import TasteProfileEntity
from app.domain.interfaces.taste_profile_repository import ITasteProfileRepository
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.domain.exceptions import NotFoundError
from app.infrastructure.llm.llm_client import LLMClient
from common import get_logger

logger = get_logger(__name__)


class TasteProfileService:
    def __init__(
            self,
            profile_repo: ITasteProfileRepository,
            entry_repo: IReadingEntryRepository,
            llm_client: LLMClient,
    ):
        self.profile_repo = profile_repo
        self.entry_repo = entry_repo
        self.llm_client = llm_client

    async def start_analysis(self, user_id: int) -> TasteProfileEntity:
        """Создать запись со статусом 'pending' и вернуть сразу."""
        profile = TasteProfileEntity(
            id=None,
            user_id=user_id,
            analysis={},
            entries_count=0,
            status="pending",
            error=None,
        )
        return await self.profile_repo.upsert(profile)

    async def run_analysis(self, user_id: int) -> None:
        """Выполнить анализ (background task)."""
        logger.info(f"Running analysis for user {user_id}")

        try:
            await self.profile_repo.update_status(user_id, "processing")

            entries = await self.entry_repo.get_by_user_id(user_id, limit=1000)
            notes = [e.note for e in entries]

            analysis = await self.llm_client.analyze_taste(notes)

            profile = TasteProfileEntity(
                id=None,
                user_id=user_id,
                analysis=analysis,
                entries_count=len(notes),
                status="done",
                error=None,
            )
            await self.profile_repo.upsert(profile)
            logger.info(f"Analysis done for user {user_id}")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            await self.profile_repo.update_status(user_id, "failed", str(e))

    async def get_profile(self, user_id: int) -> TasteProfileEntity:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundError("TasteProfile", user_id)
        return profile