import asyncio

from common import get_logger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.infrastructure.database.repositories.reading_entry_repository import (
    SqlAlchemyReadingEntryRepository,
)
from app.infrastructure.database.repositories.taste_profile_repository import (
    SqlAlchemyTasteProfileRepository,
)
from app.infrastructure.llm.langgraph.state import TasteProfileState
from app.infrastructure.llm.llm_client import LLMClient

logger = get_logger(__name__)


async def collect_notes(state: TasteProfileState) -> TasteProfileState:
    """Узел 1: Собрать заметки."""
    logger.info(f"[collect_notes] user_id={state['user_id']}")

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyReadingEntryRepository(session)
        entries = await repo.get_by_user_id(state["user_id"], limit=1000)

    notes = [e.note for e in entries if e.note]

    return {
        **state,
        "notes": notes,
        "entries_count": len(notes),
        "status": "processing",
    }


async def analyze_taste(state: TasteProfileState) -> TasteProfileState:
    """Узел 2: LLM анализ."""
    logger.info(f"[analyze_taste] notes={len(state['notes'])}")

    if not state["notes"]:
        return {
            **state,
            "analysis": None,
            "error": "No notes to analyze",
            "retryable": False,  # заметок не станет больше от повтора
        }

    try:
        llm = LLMClient()
        analysis = await llm.analyze_taste(state["notes"], state.get("feedback"))

        return {
            **state,
            "analysis": analysis,
            "error": None,
        }

    except Exception as e:
        logger.error(f"[analyze_taste] failed: {e}")
        return {
            **state,
            "analysis": None,
            "error": str(e),
        }


async def validate_analysis(state: TasteProfileState) -> TasteProfileState:
    """Узел 3: Проверка качества."""
    logger.info("[validate_analysis]")

    analysis = state.get("analysis")

    if not analysis:
        # Если analyze_taste уже записал причину (timeout и т.п.) — не затираем её
        return {**state, "error": state.get("error") or "No analysis"}

    # Проверяем обязательные поля
    required = ["themes", "style", "summary"]
    missing = [f for f in required if not analysis.get(f)]

    if missing:
        return {
            **state,
            "error": f"Missing fields: {missing}",
        }

    return {**state, "error": None}


async def retry_analysis(state: TasteProfileState) -> TasteProfileState:
    """Узел 4: пауза (backoff) и подготовка уточнённого промпта."""
    attempt = state["retry_count"] + 1
    logger.info(f"[retry_analysis] attempt={attempt}, reason={state['error']}")

    # Пауза растёт с каждой попыткой: 1с, 2с, 3с... — даём Ollama прийти в себя
    await asyncio.sleep(settings.TASTE_RETRY_BACKOFF_SECONDS * attempt)

    return {
        **state,
        "retry_count": attempt,
        "feedback": state["error"],  # в следующем промпте скажем LLM, что было не так
        "analysis": None,
        "error": None,
    }


async def save_profile(state: TasteProfileState) -> TasteProfileState:
    """Узел 5: Сохранить в БД."""
    logger.info(f"[save_profile] user_id={state['user_id']}")

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyTasteProfileRepository(session)

        from app.domain.entities.taste_profile import TasteProfileEntity
        profile = TasteProfileEntity(
            id=None,
            user_id=state["user_id"],
            analysis=state["analysis"],
            entries_count=state["entries_count"],
            status="done",
            error=None,
        )
        await repo.upsert(profile)
        await session.commit()

    return {**state, "status": "done"}


async def fail_profile(state: TasteProfileState) -> TasteProfileState:
    """Узел 6: Провал после N попыток."""
    logger.error(f"[fail_profile] user_id={state['user_id']}, error={state['error']}")

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyTasteProfileRepository(session)
        await repo.update_status(
            state["user_id"],
            "failed",
            state["error"] or "Unknown error",
            )
        await session.commit()

    return {**state, "status": "failed"}