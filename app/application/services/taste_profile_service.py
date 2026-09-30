import asyncio
from typing import Optional

from common import get_logger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domain.entities.taste_profile import TasteProfileEntity
from app.domain.exceptions import NotFoundError
from app.domain.interfaces.reading_entry_repository import IReadingEntryRepository
from app.domain.interfaces.taste_profile_repository import ITasteProfileRepository
from app.infrastructure.database.repositories.taste_profile_repository import (
    SqlAlchemyTasteProfileRepository,
)
from app.infrastructure.llm.langgraph.graph import taste_profile_graph
from app.infrastructure.llm.langgraph.state import TasteProfileState
from app.infrastructure.llm.llm_client import LLMClient

logger = get_logger(__name__)


def _thread_config(user_id: int) -> dict:
    """Один «поток» чекпоинтов на пользователя: по нему находим и продолжаем запуск."""
    return {"configurable": {"thread_id": f"taste-profile-{user_id}"}}


def _initial_state(user_id: int) -> TasteProfileState:
    return {
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


class TasteProfileService:
    def __init__(
            self,
            profile_repo: ITasteProfileRepository,
            entry_repo: IReadingEntryRepository,
            llm_client: LLMClient,
            graph=None,
    ):
        self.profile_repo = profile_repo
        self.entry_repo = entry_repo
        self.llm_client = llm_client
        # граф с чекпоинтером (из lifespan); без него — граф без сохранения шагов
        self.graph = graph or taste_profile_graph

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
        profile = await self.profile_repo.upsert(profile)
        # Коммитим сразу, до фоновой задачи: иначе строка остаётся заблокированной
        # сессией запроса (она коммитится только после фоновой задачи), и задача
        # зависает на UPDATE этой же строки.
        await self.profile_repo.commit()
        return profile

    async def run_analysis(self, user_id: int) -> None:
        """Запустить анализ через LangGraph с нуля."""
        logger.info(f"Running analysis for user {user_id} via LangGraph")
        await self._invoke(user_id, _initial_state(user_id))

    async def resume_analysis(self, user_id: int) -> None:
        """
        Продолжить прерванный анализ с последнего сохранённого шага.

        Если чекпоинтов нет (упали до первого узла) или прошлый запуск уже дошёл
        до конца, а в БД осталось pending — стартуем заново.
        """
        snapshot = await self.graph.aget_state(_thread_config(user_id))
        if snapshot.next:
            logger.info(f"Resuming analysis for user {user_id} from {snapshot.next}")
            await self._invoke(user_id, None)
        else:
            logger.info(f"No checkpoint to resume for user {user_id}, restarting")
            await self._invoke(user_id, _initial_state(user_id))

    async def _invoke(self, user_id: int, graph_input: Optional[TasteProfileState]) -> None:
        try:
            final_state = await self.graph.ainvoke(graph_input, _thread_config(user_id))
            logger.info(
                f"Graph finished: status={final_state['status']}, "
                f"retries={final_state['retry_count']}"
            )
        except Exception as e:
            # CancelledError (остановка сервиса) сюда не попадает: запись остаётся
            # 'processing', и анализ подхватит recover_stale_analyses.
            logger.error(f"Graph failed: {e}")
            await self._mark_failed(user_id, str(e))

    @staticmethod
    async def _mark_failed(user_id: int, error: str) -> None:
        # Своя сессия: сессия запроса к этому моменту уже закрыта, и без commit статус бы потерялся
        async with AsyncSessionLocal() as session:
            await SqlAlchemyTasteProfileRepository(session).update_status(
                user_id, "failed", error[:500],
            )
            await session.commit()

    async def get_profile(self, user_id: int) -> TasteProfileEntity:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundError("TasteProfile", user_id)
        return profile


async def recover_stale_analyses(graph, tasks: set) -> int:
    """
    Найти зависшие анализы (pending/processing без движения) и продолжить их.

    Захват атомарный (UPDATE ... RETURNING), поэтому при нескольких инстансах
    приложения каждый зависший анализ подхватит ровно один из них.
    """
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyTasteProfileRepository(session)
        user_ids = await repo.claim_stale(settings.TASTE_STALE_AFTER_SECONDS)
        await session.commit()

    for user_id in user_ids:
        service = TasteProfileService(None, None, None, graph=graph)
        task = asyncio.create_task(service.resume_analysis(user_id))
        tasks.add(task)  # держим ссылку, иначе задачу может собрать GC
        task.add_done_callback(tasks.discard)

    if user_ids:
        logger.warning(f"Recovered {len(user_ids)} stale taste analyses: {user_ids}")
    return len(user_ids)


async def recovery_loop(graph, tasks: set) -> None:
    """Раз в TASTE_RECOVERY_INTERVAL_SECONDS искать зависшие анализы (первый проход — сразу)."""
    while True:
        try:
            await recover_stale_analyses(graph, tasks)
        except Exception as e:
            logger.error(f"Taste recovery pass failed: {e}")
        await asyncio.sleep(settings.TASTE_RECOVERY_INTERVAL_SECONDS)
