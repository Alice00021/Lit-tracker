"""Тесты AuthService: регистрация, вход, токены, refresh."""
from datetime import timedelta

import pytest
from common import JWTService, PasswordService

from app.application.services.auth_service import AuthService
from app.domain.entities.user import UserEntity
from app.domain.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.domain.interfaces.user_repository import IUserRepository

GOOD_PASSWORD = "Str0ng!Pass"


class FakeUserRepo(IUserRepository):
    def __init__(self):
        self.users: dict[int, UserEntity] = {}

    async def get_by_id(self, user_id):
        return self.users.get(user_id)

    async def get_by_email(self, email):
        return next((u for u in self.users.values() if u.email == email), None)

    async def create(self, email, hashed_password):
        user = UserEntity(id=len(self.users) + 1, email=email, hashed_password=hashed_password)
        self.users[user.id] = user
        return user


@pytest.fixture
def jwt():
    return JWTService("unit-test-secret-key-at-least-32-chars!!")


@pytest.fixture
def repo():
    return FakeUserRepo()


@pytest.fixture
def service(repo, jwt):
    return AuthService(repo, jwt)


# ---- register ----

async def test_register_hashes_password_and_normalizes_email(service, repo):
    user = await service.register("  Alice@Example.COM ", GOOD_PASSWORD)

    assert user.email == "alice@example.com"
    assert user.hashed_password != GOOD_PASSWORD
    assert PasswordService.verify_password(GOOD_PASSWORD, user.hashed_password)


@pytest.mark.parametrize("password", ["short1!", "alllowercase1!", "ALLUPPERCASE1!", "NoDigits!!", "NoSpecial123"])
async def test_register_rejects_weak_password(service, password):
    with pytest.raises(ValidationError):
        await service.register("a@b.co", password)


async def test_register_rejects_password_over_72_bytes(service):
    with pytest.raises(ValidationError):
        await service.register("a@b.co", "Aa1!" + "x" * 80)


async def test_register_duplicate_email_conflicts_case_insensitively(service):
    await service.register("a@b.co", GOOD_PASSWORD)

    with pytest.raises(ConflictError):
        await service.register("A@B.co", GOOD_PASSWORD)


# ---- authenticate ----

async def test_authenticate_success(service):
    await service.register("a@b.co", GOOD_PASSWORD)

    user = await service.authenticate("A@b.co", GOOD_PASSWORD)

    assert user.email == "a@b.co"


async def test_authenticate_wrong_password_and_unknown_email_look_the_same(service):
    await service.register("a@b.co", GOOD_PASSWORD)

    with pytest.raises(UnauthorizedError) as wrong_pw:
        await service.authenticate("a@b.co", "Wrong1234!")
    with pytest.raises(UnauthorizedError) as unknown:
        await service.authenticate("nobody@b.co", GOOD_PASSWORD)

    assert str(wrong_pw.value) == str(unknown.value)


async def test_authenticate_legacy_placeholder_hash_is_401_not_500(service, repo):
    repo.users[1] = UserEntity(id=1, email="old@b.co", hashed_password="not-a-real-hash-just-for-test")

    with pytest.raises(UnauthorizedError):
        await service.authenticate("old@b.co", GOOD_PASSWORD)


# ---- tokens ----

async def test_issue_tokens_contains_valid_access_and_refresh(service, jwt):
    user = await service.register("a@b.co", GOOD_PASSWORD)

    tokens = service.issue_tokens(user)

    assert tokens["token_type"] == "bearer"
    assert jwt.verify_token(tokens["access_token"], "access")["sub"] == str(user.id)
    assert jwt.verify_token(tokens["refresh_token"], "refresh")["sub"] == str(user.id)
    assert jwt.verify_token(tokens["access_token"], "refresh") is None  # типы не взаимозаменяемы


async def test_refresh_returns_new_access_token(service, jwt):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)

    result = await service.refresh_access_token(tokens["refresh_token"])

    assert jwt.verify_token(result["access_token"], "access")["sub"] == str(user.id)


async def test_refresh_rejects_access_token(service):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)

    with pytest.raises(UnauthorizedError):
        await service.refresh_access_token(tokens["access_token"])


async def test_refresh_rejects_expired_and_garbage_tokens(service, jwt):
    expired = jwt.create_refresh_token(1, "user", timedelta(seconds=-5))

    for bad in (expired, "garbage", ""):
        with pytest.raises(UnauthorizedError):
            await service.refresh_access_token(bad)


async def test_refresh_rejects_token_of_deleted_user(service, repo):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)
    del repo.users[user.id]

    with pytest.raises(UnauthorizedError):
        await service.refresh_access_token(tokens["refresh_token"])
