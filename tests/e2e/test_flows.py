"""
E2E-сценарии по сквозным потокам: книга -> запись -> анализ вкуса -> рекомендации,
плюс восстановление зависшего анализа после «рестарта».
"""
import asyncio
import uuid

from sqlalchemy import text

from app.application.services.taste_profile_service import recover_stale_analyses
from app.core.database import AsyncSessionLocal
from tests.e2e.conftest import VALID_ANALYSIS, FakeLLM


async def create_book(client, title=None):
    title = title or f"Book {uuid.uuid4().hex[:8]}"
    r = await client.post("/books", json={"title": title, "author": "Author"})
    assert r.status_code == 201, r.text
    return r.json()


async def add_entry(client, book_id, note="Отличная книга"):
    r = await client.post(
        f"/books/{book_id}/entries",
        json={"note": note, "read_date": "2026-09-01", "rating": 5},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def wait_profile(client, statuses=("done", "failed"), timeout=10.0):
    """Ждать, пока анализ дойдёт до финального статуса."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        r = await client.get("/taste-profile")
        if r.status_code == 200 and r.json()["status"] in statuses:
            return r.json()
        assert asyncio.get_event_loop().time() < deadline, f"не дождались {statuses}: {r.text}"
        await asyncio.sleep(0.2)


class TestReadingEntries:
    async def test_create_and_read_entry(self, client):
        book = await create_book(client)
        entry = await add_entry(client, book["id"], note="Запоминающийся финал")

        assert entry["book"]["id"] == book["id"]
        got = await client.get(f"/books/entries/{entry['id']}")
        assert got.status_code == 200
        assert got.json()["note"] == "Запоминающийся финал"

    async def test_entry_for_missing_book_is_404(self, client):
        r = await client.post(
            "/books/999999/entries",
            json={"note": "Заметка для несуществующей книги", "read_date": "2026-09-01", "rating": 3},
        )
        assert r.status_code == 404


class TestTasteProfile:
    async def test_analysis_succeeds_and_is_saved(self, client):
        book = await create_book(client)
        await add_entry(client, book["id"])

        r = await client.post("/taste-profile/analyze")
        assert r.status_code == 202

        profile = await wait_profile(client)
        assert profile["status"] == "done"
        assert profile["analysis"]["themes"] == VALID_ANALYSIS["themes"]

    async def test_llm_failure_is_reported_as_failed(self, client):
        book = await create_book(client)
        await add_entry(client, book["id"])
        FakeLLM.fail = True

        await client.post("/taste-profile/analyze")

        profile = await wait_profile(client)
        assert profile["status"] == "failed"
        assert "Ollama is down" in profile["error"]

    async def test_stale_analysis_is_recovered(self, client, running_app):
        """Зависший после рестарта анализ подхватывается и доводится до done."""
        book = await create_book(client)
        await add_entry(client, book["id"])
        await client.post("/taste-profile/analyze")
        await wait_profile(client)
        user_id = (await client.get("/auth/me")).json()["id"]

        # имитация: процесс умер, запись осталась processing и давно не обновлялась
        async with AsyncSessionLocal() as session:
            await session.execute(text(
                "UPDATE taste_profiles SET status='processing', "
                "updated_at = now() - interval '1 hour' WHERE user_id = :uid"
            ), {"uid": user_id})
            await session.commit()

        tasks: set = set()
        recovered = await recover_stale_analyses(running_app.state.taste_graph, tasks)
        await asyncio.gather(*tasks)

        assert recovered >= 1
        profile = await wait_profile(client)
        assert profile["status"] == "done"


class TestRecommendations:
    async def test_recommendations_exclude_read_books(self, client):
        read = await create_book(client)
        other = await create_book(client)
        await add_entry(client, read["id"])
        await client.post("/taste-profile/analyze")
        await wait_profile(client)

        r = await client.get("/recommendations")

        assert r.status_code == 200
        ids = [item["book"]["id"] for item in r.json()["recommendations"]]
        assert other["id"] in ids
        assert read["id"] not in ids
