from common import get_logger

from app.core.config import settings
from app.domain.entities.taste_profile import TasteProfileEntity
from app.domain.exceptions import NotFoundError
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.domain.interfaces.taste_profile_repository import ITasteProfileRepository
from app.infrastructure.llm.langgraph.graph import taste_profile_graph
from app.infrastructure.llm.langgraph.state import TasteProfileState
from app.infrastructure.llm.llm_client import LLMClient

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
        """
        Запустить анализ через LangGraph.
        """
        logger.info(f"Running analysis for user {user_id} via LangGraph")

        initial_state: TasteProfileState = {
            "user_id": user_id,
            "notes": [],
            "analysis": None,
            "error": None,
            "retryable": True,
            "feedback": None,
            "retry_count": 0,
            "max_retries": settings.TASTE_MAX_RETRIES,
            "status": "pending",
            "entries_count": 0,
        }

        try:
            final_state = await taste_profile_graph.ainvoke(initial_state)
            logger.info(
                f"Graph finished: status={final_state['status']}, "
                f"retries={final_state['retry_count']}"
            )
        except Exception as e:
            logger.error(f"Graph failed: {e}")
            await self.profile_repo.update_status(user_id, "failed", str(e))

    async def get_profile(self, user_id: int) -> TasteProfileEntity:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundError("TasteProfile", user_id)
        return profile