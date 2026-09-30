"""Тесты AuthService: регистрация, вход, лимит попыток, токены, refresh, logout."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from common import AuthenticatedUser, JWTService, PasswordService, TokenBlacklist
from common.exceptions import RateLimitError
from jose import jwt as jose_jwt

from app.application.services.auth_service import AuthService
from app.domain.entities.user import UserEntity
from app.domain.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.domain.interfaces.user_repository import IUserRepository
from app.infrastructure.cache import login_rate_limiter as limiter_module
from app.infrastructure.cache.login_rate_limiter import LoginRateLimiter
from tests.unit.fakes import FakeRedis

GOOD_PASSWORD = "Str0ng!Pass"
SECRET = "unit-test-secret-key-at-least-32-chars!!"
IP = "1.2.3.4"


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


@pytest.fixture(autouse=True)
def redis(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(limiter_module, "get_redis", get_fake)
    monkeypatch.setattr("common.security.blacklist.get_redis", get_fake)
    return fake


@pytest.fixture
def jwt():
    return JWTService(SECRET)


@pytest.fixture
def repo():
    return FakeUserRepo()


@pytest.fixture
def service(repo, jwt):
    limiter = LoginRateLimiter(max_attempts=3, max_attempts_per_ip=10, window_seconds=60)
    return AuthService(repo, jwt, TokenBlacklist(), limiter)


def as_current_user(jwt, tokens) -> AuthenticatedUser:
    """Как это делает зависимость get_current_user по access-токену."""
    claims = jwt.decode_token(tokens["access_token"])
    return AuthenticatedUser(
        id=int(claims["sub"]), role=claims["role"], token_id=claims["jti"], token_expires_at=claims["exp"],
    )


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


# ---- login + лимит попыток ----

async def test_login_success_returns_tokens(service):
    await service.register("a@b.co", GOOD_PASSWORD)

    tokens = await service.login("A@b.co", GOOD_PASSWORD, IP)

    assert tokens["access_token"] and tokens["refresh_token"]


async def test_login_locks_out_after_failures_even_with_correct_password(service):
    await service.register("a@b.co", GOOD_PASSWORD)
    for _ in range(3):
        with pytest.raises(UnauthorizedError):
            await service.login("a@b.co", "Wrong1234!", IP)

    with pytest.raises(RateLimitError) as exc:
        await service.login("a@b.co", GOOD_PASSWORD, IP)  # верный пароль, но аккаунт «остывает»

    assert exc.value.details["retry_after"] > 0


async def test_lockout_is_per_ip_and_per_email(service):
    await service.register("a@b.co", GOOD_PASSWORD)
    await service.register("c@d.co", GOOD_PASSWORD)
    for _ in range(3):
        with pytest.raises(UnauthorizedError):
            await service.login("a@b.co", "Wrong1234!", IP)

    assert await service.login("a@b.co", GOOD_PASSWORD, "9.9.9.9")   # другой IP входит
    assert await service.login("c@d.co", GOOD_PASSWORD, IP)          # другой аккаунт входит


async def test_successful_login_resets_failures(service):
    await service.register("a@b.co", GOOD_PASSWORD)
    for _ in range(2):
        with pytest.raises(UnauthorizedError):
            await service.login("a@b.co", "Wrong1234!", IP)
    await service.login("a@b.co", GOOD_PASSWORD, IP)

    for _ in range(2):  # снова есть запас попыток
        with pytest.raises(UnauthorizedError):
            await service.login("a@b.co", "Wrong1234!", IP)


# ---- refresh (ротация, одноразовость) ----

async def test_refresh_returns_new_working_pair(service, jwt):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)

    new = await service.refresh(tokens["refresh_token"])

    assert new["refresh_token"] != tokens["refresh_token"]
    assert jwt.verify_token(new["access_token"], "access")["sub"] == str(user.id)
    assert jwt.verify_token(new["refresh_token"], "refresh")["sub"] == str(user.id)


async def test_refresh_token_is_single_use(service):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)
    await service.refresh(tokens["refresh_token"])

    with pytest.raises(UnauthorizedError):
        await service.refresh(tokens["refresh_token"])   # повторное предъявление


async def test_concurrent_refresh_only_one_wins(service):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)

    results = await asyncio.gather(
        service.refresh(tokens["refresh_token"]),
        service.refresh(tokens["refresh_token"]),
        return_exceptions=True,
    )

    assert sum(isinstance(r, dict) for r in results) == 1
    assert sum(isinstance(r, UnauthorizedError) for r in results) == 1


async def test_refresh_rejects_access_token(service):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)

    with pytest.raises(UnauthorizedError):
        await service.refresh(tokens["access_token"])


async def test_refresh_rejects_expired_garbage_and_jti_less_tokens(service, jwt):
    expired = jwt.create_refresh_token(1, "user", timedelta(seconds=-5))
    legacy = jose_jwt.encode(   # refresh, выданный до появления jti: отозвать нельзя -> не принимаем
        {"sub": "1", "role": "user", "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
        SECRET, algorithm="HS256",
    )

    for bad in (expired, "garbage", "", legacy):
        with pytest.raises(UnauthorizedError):
            await service.refresh(bad)


async def test_refresh_rejects_token_of_deleted_user(service, repo):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)
    del repo.users[user.id]

    with pytest.raises(UnauthorizedError):
        await service.refresh(tokens["refresh_token"])


# ---- logout ----

async def test_logout_revokes_access_and_refresh(service, jwt):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)

    await service.logout(as_current_user(jwt, tokens), tokens["refresh_token"])

    blacklist = service.blacklist
    assert await blacklist.is_revoked(jwt.decode_token(tokens["access_token"])["jti"])
    assert await blacklist.is_revoked(jwt.decode_token(tokens["refresh_token"])["jti"])
    with pytest.raises(UnauthorizedError):
        await service.refresh(tokens["refresh_token"])


async def test_logout_without_refresh_revokes_only_access(service, jwt):
    user = await service.register("a@b.co", GOOD_PASSWORD)
    tokens = service.issue_tokens(user)

    await service.logout(as_current_user(jwt, tokens))

    assert await service.blacklist.is_revoked(jwt.decode_token(tokens["access_token"])["jti"])
    assert await service.refresh(tokens["refresh_token"])   # refresh остался рабочим


async def test_logout_ignores_foreign_and_garbage_refresh(service, jwt):
    alice = await service.register("a@b.co", GOOD_PASSWORD)
    bob = await service.register("b@b.co", GOOD_PASSWORD)
    a_tokens, b_tokens = service.issue_tokens(alice), service.issue_tokens(bob)

    await service.logout(as_current_user(jwt, a_tokens), b_tokens["refresh_token"])  # чужой refresh
    await service.logout(as_current_user(jwt, a_tokens), "garbage")

    assert not await service.blacklist.is_revoked(jwt.decode_token(b_tokens["refresh_token"])["jti"])
    assert await service.refresh(b_tokens["refresh_token"])   # у Bob всё работает
