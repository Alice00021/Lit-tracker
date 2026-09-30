"""E2E: регистрация, вход, токены, защита роутов и изоляция данных между пользователями."""
import uuid

from tests.e2e.conftest import PASSWORD


def new_email():
    return f"auth-{uuid.uuid4().hex[:10]}@example.com"


class TestRegister:
    async def test_register_returns_user_without_password(self, anon_client):
        r = await anon_client.post("/auth/register", json={"email": new_email(), "password": PASSWORD})

        assert r.status_code == 201
        assert set(r.json()) == {"id", "email", "created_at"}

    async def test_duplicate_email_is_409_case_insensitive(self, anon_client):
        email = new_email()
        await anon_client.post("/auth/register", json={"email": email, "password": PASSWORD})

        r = await anon_client.post("/auth/register", json={"email": email.upper(), "password": PASSWORD})

        assert r.status_code == 409

    async def test_weak_password_is_400(self, anon_client):
        r = await anon_client.post("/auth/register", json={"email": new_email(), "password": "weakpassword"})

        assert r.status_code == 400

    async def test_invalid_email_is_422(self, anon_client):
        r = await anon_client.post("/auth/register", json={"email": "not-an-email", "password": PASSWORD})

        assert r.status_code == 422


class TestLogin:
    async def test_wrong_password_and_unknown_user_give_same_401(self, anon_client, user_a):
        wrong = await anon_client.post("/auth/login", data={"username": user_a["email"], "password": "Wrong1234!"})
        unknown = await anon_client.post("/auth/login", data={"username": new_email(), "password": PASSWORD})

        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()

    async def test_me_returns_current_user(self, client, user_a):
        r = await client.get("/auth/me")

        assert r.status_code == 200
        assert r.json()["email"] == user_a["email"]


class TestRefresh:
    async def test_refresh_gives_working_access_token(self, anon_client, user_a):
        r = await anon_client.post("/auth/refresh", json={"refresh_token": user_a["tokens"]["refresh_token"]})

        assert r.status_code == 200
        me = await anon_client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
        assert me.status_code == 200

    async def test_access_token_cannot_be_used_as_refresh(self, anon_client, user_a):
        r = await anon_client.post("/auth/refresh", json={"refresh_token": user_a["tokens"]["access_token"]})

        assert r.status_code == 401

    async def test_refresh_token_cannot_be_used_as_access(self, anon_client, user_a):
        r = await anon_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {user_a['tokens']['refresh_token']}"},
        )

        assert r.status_code == 401


class TestProtection:
    async def test_protected_routes_require_token(self, anon_client):
        checks = [
            ("GET", "/books"), ("POST", "/books"), ("GET", "/books/entries"),
            ("GET", "/taste-profile"), ("POST", "/taste-profile/analyze"),
            ("GET", "/recommendations"), ("POST", "/books/search/smart"),
        ]
        for method, path in checks:
            r = await anon_client.request(method, path)
            assert r.status_code == 401, f"{method} {path} -> {r.status_code}"
            assert r.headers["www-authenticate"] == "Bearer"

    async def test_public_routes_stay_open(self, anon_client):
        for path in ("/", "/health", "/docs", "/openapi.json"):
            assert (await anon_client.get(path)).status_code == 200, path

    async def test_garbage_token_is_401(self, anon_client):
        r = await anon_client.get("/books", headers={"Authorization": "Bearer garbage"})

        assert r.status_code == 401


class TestIsolation:
    """Пользователь не видит и не меняет данные другого."""

    async def _entry_of_a(self, client):
        book = (await client.post("/books", json={"title": "Private", "author": "A"})).json()
        r = await client.post(
            f"/books/{book['id']}/entries",
            json={"note": "Моя личная заметка", "read_date": "2026-09-01", "rating": 4},
        )
        assert r.status_code == 201
        return r.json()

    async def test_other_user_cannot_read_update_or_delete_entry(self, client, other_client):
        entry = await self._entry_of_a(client)
        url = f"/books/entries/{entry['id']}"

        assert (await other_client.get(url)).status_code == 404
        assert (await other_client.patch(url, json={"rating": 1})).status_code == 404
        assert (await other_client.delete(url)).status_code == 404

        # у владельца запись цела и не изменилась
        mine = await client.get(url)
        assert mine.status_code == 200
        assert mine.json()["rating"] == 4

    async def test_other_user_does_not_see_entry_in_list(self, client, other_client):
        entry = await self._entry_of_a(client)

        listed = (await other_client.get("/books/entries")).json()

        assert entry["id"] not in [e["id"] for e in listed["items"]]

    async def test_taste_profiles_are_per_user(self, client, other_client):
        assert (await other_client.get("/taste-profile")).status_code == 404  # у B анализа не было
