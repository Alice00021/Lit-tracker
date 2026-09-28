"""
E2E-тесты через HTTP-клиент.
"""
import pytest
from httpx import AsyncClient


class TestHealth:
    """Тесты healthcheck."""

    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        """GET / — root."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        """GET /health."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestBooksAPI:
    """Тесты Books API."""

    @pytest.mark.asyncio
    async def test_create_book(self, client: AsyncClient):
        """POST /books — успех."""
        response = await client.post("/books", json={
            "title": "E2E Test Book",
            "author": "E2E Author",
            "description": "Created via E2E test",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "E2E Test Book"
        assert data["author"] == "E2E Author"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_book_validation_error(self, client: AsyncClient):
        """POST /books — пустой title → 422."""
        response = await client.post("/books", json={
            "title": "",
            "author": "Author",
        })

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_books(self, client: AsyncClient):
        """GET /books — список."""
        response = await client.get("/books")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_missing_book(self, client: AsyncClient):
        """GET /books/999999 — 404."""
        response = await client.get("/books/999999")

        assert response.status_code == 404


class TestSmartSearchAPI:
    """Тесты smart search."""

    @pytest.mark.asyncio
    async def test_smart_search_validation(self, client: AsyncClient):
        """POST /books/search/smart — пустой query → 422."""
        response = await client.post("/books/search/smart", json={
            "query": "",
        })

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_smart_search_too_short(self, client: AsyncClient):
        """POST /books/search/smart — короткий query → 422."""
        response = await client.post("/books/search/smart", json={
            "query": "ab",   # < 3 символов
        })

        assert response.status_code == 422