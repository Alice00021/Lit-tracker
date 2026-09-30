"""Тесты зависимости «текущий пользователь» (common.create_auth_dependency)."""
from datetime import timedelta

import pytest
from common import AuthenticatedUser, JWTService, create_auth_dependency
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

SECRET = "unit-test-secret-key-at-least-32-chars!!"
jwt = JWTService(SECRET)

app = FastAPI()
get_current_user = create_auth_dependency(jwt)


@app.get("/whoami")
async def whoami(user: AuthenticatedUser = Depends(get_current_user)):
    return {"id": user.id, "role": user.role}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


async def test_valid_access_token(client):
    token = jwt.create_access_token(42, "user", timedelta(minutes=5))

    r = await client.get("/whoami", headers=bearer(token))

    assert r.status_code == 200
    assert r.json() == {"id": 42, "role": "user"}


async def test_missing_token_is_401_with_www_authenticate(client):
    r = await client.get("/whoami")

    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("make_token", [
    lambda: "not-a-jwt",
    lambda: jwt.create_access_token(1, "user", timedelta(seconds=-5)),          # просрочен
    lambda: jwt.create_refresh_token(1, "user", timedelta(minutes=5)),          # не тот тип
    lambda: JWTService("another-secret-key-at-least-32-chars!!!").create_access_token(
        1, "user", timedelta(minutes=5)),                                       # чужая подпись
    lambda: jwt.create_token({"role": "user"}, timedelta(minutes=5), "access"),  # нет sub
    lambda: jwt.create_token({"sub": "abc", "role": "user"}, timedelta(minutes=5), "access"),  # sub не число
])
async def test_invalid_tokens_are_rejected(client, make_token):
    r = await client.get("/whoami", headers=bearer(make_token()))

    assert r.status_code == 401
