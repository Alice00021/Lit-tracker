"""E2E: регистрация, вход, токены, защита роутов и изоляция данных между пользователями."""
import uuid

from app.core.config import settings
from tests.e2e.conftest import PASSWORD, _http, auth_headers


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
    async def test_refresh_rotates_tokens(self, anon_client, fresh_user):
        old_refresh = fresh_user["tokens"]["refresh_token"]

        r = await anon_client.post("/auth/refresh", json={"refresh_token": old_refresh})

        assert r.status_code == 200
        new = r.json()
        assert new["refresh_token"] != old_refresh
        me = await anon_client.get("/auth/me", headers=auth_headers(new))
        assert me.status_code == 200

    async def test_refresh_token_is_single_use(self, anon_client, fresh_user):
        old_refresh = fresh_user["tokens"]["refresh_token"]
        first = await anon_client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert first.status_code == 200

        replay = await anon_client.post("/auth/refresh", json={"refresh_token": old_refresh})

        assert replay.status_code == 401

    async def test_access_token_cannot_be_used_as_refresh(self, anon_client, user_a):
        r = await anon_client.post("/auth/refresh", json={"refresh_token": user_a["tokens"]["access_token"]})

        assert r.status_code == 401

    async def test_refresh_token_cannot_be_used_as_access(self, anon_client, user_a):
        r = await anon_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {user_a['tokens']['refresh_token']}"},
        )

        assert r.status_code == 401


class TestLogout:
    async def test_logout_revokes_access_token(self, anon_client, fresh_user):
        headers = fresh_user["headers"]
        assert (await anon_client.get("/auth/me", headers=headers)).status_code == 200

        r = await anon_client.post("/auth/logout", headers=headers)

        assert r.status_code == 204
        assert (await anon_client.get("/auth/me", headers=headers)).status_code == 401
        assert (await anon_client.get("/books", headers=headers)).status_code == 401

    async def test_logout_with_refresh_token_revokes_it_too(self, anon_client, fresh_user):
        refresh = fresh_user["tokens"]["refresh_token"]

        r = await anon_client.post(
            "/auth/logout", headers=fresh_user["headers"], json={"refresh_token": refresh},
        )

        assert r.status_code == 204
        assert (await anon_client.post("/auth/refresh", json={"refresh_token": refresh})).status_code == 401

    async def test_logout_without_refresh_keeps_refresh_usable(self, anon_client, fresh_user):
        await anon_client.post("/auth/logout", headers=fresh_user["headers"])

        r = await anon_client.post(
            "/auth/refresh", json={"refresh_token": fresh_user["tokens"]["refresh_token"]},
        )

        assert r.status_code == 200

    async def test_logout_requires_token(self, anon_client):
        assert (await anon_client.post("/auth/logout")).status_code == 401

    async def test_can_log_in_again_after_logout(self, anon_client, fresh_user):
        await anon_client.post("/auth/logout", headers=fresh_user["headers"])

        r = await anon_client.post(
            "/auth/login", data={"username": fresh_user["email"], "password": PASSWORD},
        )

        assert r.status_code == 200
        me = await anon_client.get("/auth/me", headers=auth_headers(r.json()))
        assert me.status_code == 200

    async def test_other_users_tokens_survive_logout(self, anon_client, fresh_user, user_b):
        await anon_client.post("/auth/logout", headers=fresh_user["headers"])

        assert (await anon_client.get("/auth/me", headers=user_b["headers"])).status_code == 200


class TestLoginRateLimit:
    async def _bad_login(self, ac, email):
        return await ac.post("/auth/login", data={"username": email, "password": "Wrong1234!"})

    async def test_lockout_after_max_failures_blocks_even_correct_password(self, anon_client, fresh_user):
        email = fresh_user["email"]
        for _ in range(settings.LOGIN_MAX_ATTEMPTS):
            assert (await self._bad_login(anon_client, email)).status_code == 401

        blocked = await anon_client.post("/auth/login", data={"username": email, "password": PASSWORD})

        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0

    async def test_lockout_does_not_affect_other_ip_or_account(self, running_app, anon_client, fresh_user, user_b):
        email = fresh_user["email"]
        for _ in range(settings.LOGIN_MAX_ATTEMPTS):
            await self._bad_login(anon_client, email)

        # тот же аккаунт с другого IP и другой аккаунт с того же IP входят нормально
        async with _http(running_app) as elsewhere:
            ok = await elsewhere.post("/auth/login", data={"username": email, "password": PASSWORD})
        other = await anon_client.post("/auth/login", data={"username": user_b["email"], "password": PASSWORD})

        assert ok.status_code == 200
        assert other.status_code == 200

    async def test_success_resets_counter(self, anon_client, fresh_user):
        email = fresh_user["email"]
        for _ in range(settings.LOGIN_MAX_ATTEMPTS - 1):
            await self._bad_login(anon_client, email)
        ok = await anon_client.post("/auth/login", data={"username": email, "password": PASSWORD})
        assert ok.status_code == 200

        for _ in range(settings.LOGIN_MAX_ATTEMPTS - 1):   # снова полный запас попыток
            assert (await self._bad_login(anon_client, email)).status_code == 401


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
