"""Тесты устойчивости анализа: чекпоинты, продолжение после обрыва, восстановление."""
import asyncio

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.application.services import taste_profile_service as svc_module
from app.application.services.taste_profile_service import (
    TasteProfileService,
    recover_stale_analyses,
)
from app.core.config import settings
from app.infrastructure.llm.langgraph import nodes
from app.infrastructure.llm.langgraph.checkpointer import to_psycopg_url
from app.infrastructure.llm.langgraph.graph import build_taste_profile_graph
from tests.unit.infrastructure.test_taste_graph import (  # noqa: F401  (fixture patched — autouse)
    VALID,
    FakeEntryRepo,
    FakeProfileRepo,
    patched,
)


class CountingEntryRepo(FakeEntryRepo):
    calls = 0

    async def get_by_user_id(self, user_id, limit):
        CountingEntryRepo.calls += 1
        return await super().get_by_user_id(user_id, limit)


def crashing_llm(crash_first: bool):
    """LLM, который в первый вызов «зависает» (ждём остановки сервиса), потом отвечает нормально."""
    state = {"calls": 0, "started": asyncio.Event()}

    class FakeLLM:
        async def analyze_taste(self, notes, feedback=None):
            state["calls"] += 1
            if crash_first and state["calls"] == 1:
                state["started"].set()
                await asyncio.sleep(3600)
            return VALID

    FakeLLM.state = state
    return FakeLLM


async def run_and_kill(service, user_id, llm):
    """Запустить анализ и отменить задачу посреди вызова LLM — как при остановке сервиса."""
    task = asyncio.create_task(service.run_analysis(user_id))
    await llm.state["started"].wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def make_service(graph):
    return TasteProfileService(None, None, None, graph=graph)


@pytest.fixture
def graph(monkeypatch):
    CountingEntryRepo.calls = 0
    monkeypatch.setattr(nodes, "SqlAlchemyReadingEntryRepository", CountingEntryRepo)
    return build_taste_profile_graph(InMemorySaver())


async def test_resume_continues_from_last_checkpoint(graph, monkeypatch):
    llm = crashing_llm(crash_first=True)
    monkeypatch.setattr(nodes, "LLMClient", llm)
    service = make_service(graph)

    await run_and_kill(service, 1, llm)  # «процесс убили» внутри analyze_taste
    assert FakeProfileRepo.saved is None

    await service.resume_analysis(1)

    assert FakeProfileRepo.saved is not None
    assert llm.state["calls"] == 2
    assert CountingEntryRepo.calls == 1  # collect_notes второй раз НЕ выполнялся


async def test_cancel_does_not_mark_profile_failed(graph, monkeypatch):
    llm = crashing_llm(crash_first=True)
    monkeypatch.setattr(nodes, "LLMClient", llm)

    await run_and_kill(make_service(graph), 1, llm)

    assert FakeProfileRepo.failed is None  # остаётся processing -> подхватит recovery


async def test_resume_without_checkpoint_starts_from_scratch(graph, monkeypatch):
    monkeypatch.setattr(nodes, "LLMClient", crashing_llm(crash_first=False))

    await make_service(graph).resume_analysis(1)

    assert FakeProfileRepo.saved is not None
    assert CountingEntryRepo.calls == 1


async def test_resume_after_finished_run_restarts(graph, monkeypatch):
    monkeypatch.setattr(nodes, "LLMClient", crashing_llm(crash_first=False))
    service = make_service(graph)
    await service.run_analysis(1)
    FakeProfileRepo.saved = None

    await service.resume_analysis(1)  # в БД остался pending, но граф уже завершён

    assert FakeProfileRepo.saved is not None
    assert CountingEntryRepo.calls == 2


async def test_graph_failure_marks_profile_failed_via_own_session(monkeypatch):
    class Boom:
        async def aget_state(self, config):
            raise AssertionError

        async def ainvoke(self, *a, **k):
            raise RuntimeError("db is down")

    monkeypatch.setattr(svc_module, "AsyncSessionLocal", nodes.AsyncSessionLocal)
    monkeypatch.setattr(svc_module, "SqlAlchemyTasteProfileRepository", FakeProfileRepo)

    await make_service(Boom()).run_analysis(1)

    assert FakeProfileRepo.failed == ("failed", "db is down")


async def test_heartbeat_called_and_failure_is_harmless(graph, monkeypatch):
    monkeypatch.setattr(nodes, "LLMClient", crashing_llm(crash_first=False))
    await make_service(graph).run_analysis(1)
    assert FakeProfileRepo.heartbeats == 2  # collect_notes + analyze_taste

    async def broken(self, user_id):
        raise RuntimeError("heartbeat db error")

    monkeypatch.setattr(FakeProfileRepo, "heartbeat", broken)
    FakeProfileRepo.saved = None
    await make_service(graph).run_analysis(2)
    assert FakeProfileRepo.saved is not None  # анализ не пострадал


async def test_recover_stale_analyses_resumes_claimed_users(monkeypatch):
    resumed = []

    class ClaimRepo(FakeProfileRepo):
        async def claim_stale(self, seconds):
            assert seconds == settings.TASTE_STALE_AFTER_SECONDS
            return [7, 8]

    async def fake_resume(self, user_id):
        resumed.append(user_id)

    monkeypatch.setattr(svc_module, "AsyncSessionLocal", nodes.AsyncSessionLocal)
    monkeypatch.setattr(svc_module, "SqlAlchemyTasteProfileRepository", ClaimRepo)
    monkeypatch.setattr(TasteProfileService, "resume_analysis", fake_resume)

    tasks: set = set()
    count = await recover_stale_analyses(graph=object(), tasks=tasks)
    await asyncio.gather(*tasks)

    assert count == 2
    assert sorted(resumed) == [7, 8]


def test_to_psycopg_url():
    assert to_psycopg_url("postgresql+asyncpg://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"
    assert to_psycopg_url("postgresql://u:p@h/db") == "postgresql://u:p@h/db"


async def test_start_analysis_commits_before_background_task():
    """Регрессия: без коммита строка залочена сессией запроса и фоновая задача виснет."""
    calls = []

    class Repo:
        async def upsert(self, profile):
            calls.append("upsert")
            return profile

        async def commit(self):
            calls.append("commit")

    profile = await TasteProfileService(Repo(), None, None).start_analysis(1)

    assert calls == ["upsert", "commit"]
    assert profile.status == "pending"
