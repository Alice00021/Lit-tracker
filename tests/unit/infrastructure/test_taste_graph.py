"""Тесты графа taste profile: retry, backoff, feedback в промпте."""
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.infrastructure.llm.langgraph import nodes
from app.infrastructure.llm.langgraph.graph import should_retry, taste_profile_graph
from app.infrastructure.llm.prompts import build_taste_prompt

VALID = {"themes": ["fantasy"], "style": "dark", "summary": "ok", "loves": [], "dislikes": []}


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def commit(self):
        pass


class FakeEntryRepo:
    notes = ["good book"]

    def __init__(self, session):
        pass

    async def get_by_user_id(self, user_id, limit):
        return [SimpleNamespace(note=n) for n in self.notes]


class FakeProfileRepo:
    saved = None
    failed = None
    heartbeats = 0

    def __init__(self, session):
        pass

    async def upsert(self, profile):
        FakeProfileRepo.saved = profile

    async def update_status(self, user_id, status, error):
        FakeProfileRepo.failed = (status, error)

    async def heartbeat(self, user_id):
        FakeProfileRepo.heartbeats += 1


def make_llm(responses, prompts_seen):
    """Фейковый LLM: на каждый вызов отдаёт следующий ответ (или бросает исключение)."""
    calls = iter(responses)

    class FakeLLM:
        async def analyze_taste(self, notes, feedback=None):
            prompts_seen.append(feedback)
            result = next(calls)
            if isinstance(result, Exception):
                raise result
            return result

    return FakeLLM


@pytest.fixture(autouse=True)
def patched(monkeypatch):
    FakeProfileRepo.saved = None
    FakeProfileRepo.failed = None
    FakeProfileRepo.heartbeats = 0
    FakeEntryRepo.notes = ["good book"]
    monkeypatch.setattr(nodes, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(nodes, "SqlAlchemyReadingEntryRepository", FakeEntryRepo)
    monkeypatch.setattr(nodes, "SqlAlchemyTasteProfileRepository", FakeProfileRepo)
    monkeypatch.setattr(settings, "TASTE_RETRY_BACKOFF_SECONDS", 0)


def initial_state(max_retries=3):
    return {
        "user_id": 1, "notes": [], "analysis": None, "error": None,
        "retryable": True, "feedback": None, "retry_count": 0,
        "max_retries": max_retries, "status": "pending", "entries_count": 0,
    }


# ---- should_retry ----

def test_should_retry_save_when_no_error():
    assert should_retry({**initial_state(), "error": None}) == "save"


def test_should_retry_retry_when_attempts_left():
    assert should_retry({**initial_state(), "error": "boom", "retry_count": 1}) == "retry"


def test_should_retry_fail_when_attempts_exhausted():
    assert should_retry({**initial_state(3), "error": "boom", "retry_count": 3}) == "fail"


def test_should_retry_fail_immediately_when_not_retryable():
    assert should_retry({**initial_state(), "error": "x", "retryable": False}) == "fail"


# ---- prompt ----

def test_prompt_contains_feedback_only_on_retry():
    assert "предыдущий ответ не подошёл" not in build_taste_prompt(["a"])
    assert "Missing fields" in build_taste_prompt(["a"], feedback="Missing fields: ['style']")


# ---- graph end-to-end ----

async def test_graph_success_first_try(monkeypatch):
    seen = []
    monkeypatch.setattr(nodes, "LLMClient", make_llm([VALID], seen))

    final = await taste_profile_graph.ainvoke(initial_state())

    assert final["status"] == "done"
    assert final["retry_count"] == 0
    assert FakeProfileRepo.saved is not None


async def test_graph_recovers_after_llm_error_and_passes_feedback(monkeypatch):
    seen = []
    monkeypatch.setattr(nodes, "LLMClient", make_llm([RuntimeError("timeout"), VALID], seen))

    final = await taste_profile_graph.ainvoke(initial_state())

    assert final["status"] == "done"
    assert final["retry_count"] == 1
    assert seen == [None, "timeout"]  # на 2-й попытке LLM узнала причину провала


async def test_graph_retries_on_incomplete_analysis(monkeypatch):
    seen = []
    incomplete = {"themes": [], "style": "", "summary": ""}
    monkeypatch.setattr(nodes, "LLMClient", make_llm([incomplete, VALID], seen))

    final = await taste_profile_graph.ainvoke(initial_state())

    assert final["status"] == "done"
    assert "Missing fields" in seen[1]


async def test_graph_fails_after_max_retries(monkeypatch):
    seen = []
    monkeypatch.setattr(nodes, "LLMClient", make_llm([RuntimeError("down")] * 10, seen))

    final = await taste_profile_graph.ainvoke(initial_state(max_retries=2))

    assert final["status"] == "failed"
    assert final["retry_count"] == 2
    assert len(seen) == 3  # 1 первая попытка + 2 повтора
    assert FakeProfileRepo.failed == ("failed", "down")


async def test_graph_does_not_retry_without_notes(monkeypatch):
    seen = []
    FakeEntryRepo.notes = []
    monkeypatch.setattr(nodes, "LLMClient", make_llm([], seen))

    final = await taste_profile_graph.ainvoke(initial_state())

    assert final["status"] == "failed"
    assert final["retry_count"] == 0
    assert seen == []  # LLM даже не вызывали
