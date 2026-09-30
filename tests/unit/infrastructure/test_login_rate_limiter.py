"""Тесты LoginRateLimiter и TokenBlacklist на фейковом Redis."""
import pytest
from common import TokenBlacklist
from common.exceptions import RateLimitError

from app.infrastructure.cache import login_rate_limiter as limiter_module
from app.infrastructure.cache.login_rate_limiter import LoginRateLimiter
from tests.unit.fakes import FakeRedis


@pytest.fixture
def redis(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(limiter_module, "get_redis", get_fake)
    monkeypatch.setattr("common.security.blacklist.get_redis", get_fake)
    return fake


@pytest.fixture
def limiter(redis):
    return LoginRateLimiter(max_attempts=3, max_attempts_per_ip=5, window_seconds=60)


async def fail(limiter, ip, email, times):
    for _ in range(times):
        await limiter.check(ip, email)
        await limiter.record_failure(ip, email)


# ---- LoginRateLimiter ----

async def test_blocks_after_max_failures_for_pair(limiter):
    await fail(limiter, "1.1.1.1", "a@b.co", 3)

    with pytest.raises(RateLimitError) as exc:
        await limiter.check("1.1.1.1", "a@b.co")

    assert exc.value.status_code == 429
    assert 0 < exc.value.details["retry_after"] <= 60


async def test_other_email_or_ip_not_affected(limiter):
    await fail(limiter, "1.1.1.1", "a@b.co", 3)

    await limiter.check("1.1.1.1", "other@b.co")   # другой аккаунт с того же IP
    await limiter.check("2.2.2.2", "a@b.co")       # тот же аккаунт с другого IP: чужой IP не блокирует


async def test_ip_limit_covers_many_accounts(limiter):
    for i in range(5):
        await limiter.record_failure("1.1.1.1", f"user{i}@b.co")

    with pytest.raises(RateLimitError):
        await limiter.check("1.1.1.1", "brand-new@b.co")


async def test_success_resets_pair_counter(limiter):
    await fail(limiter, "1.1.1.1", "a@b.co", 2)

    await limiter.reset("1.1.1.1", "a@b.co")

    await fail(limiter, "1.1.1.1", "a@b.co", 2)  # снова есть запас, блокировки нет


async def test_email_is_not_stored_in_plain_text(limiter, redis):
    await limiter.record_failure("1.1.1.1", "secret@b.co")

    assert not any("secret@b.co" in key for key in redis.data)


async def test_counter_gets_window_ttl(limiter, redis):
    await limiter.record_failure("1.1.1.1", "a@b.co")

    assert set(redis.ttls.values()) == {60}


# ---- TokenBlacklist ----

async def test_revoke_then_is_revoked(redis):
    bl = TokenBlacklist()

    assert not await bl.is_revoked("jti1")
    assert await bl.revoke("jti1", 100) is True
    assert await bl.is_revoked("jti1")


async def test_second_revoke_returns_false(redis):
    bl = TokenBlacklist()
    await bl.revoke("jti1", 100)

    assert await bl.revoke("jti1", 100) is False   # на этом держится одноразовость refresh


async def test_revoke_sets_ttl_and_never_zero(redis):
    bl = TokenBlacklist()

    await bl.revoke("a", 120)
    await bl.revoke("b", 0)

    assert redis.ttls["revoked:a"] == 120
    assert redis.ttls["revoked:b"] == 1
