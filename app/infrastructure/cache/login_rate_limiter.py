import hashlib

from common import get_redis
from common.exceptions import RateLimitError


class LoginRateLimiter:
    """
    Ограничение подбора пароля: считаем НЕУДАЧНЫЕ попытки входа в Redis.

    Два счётчика в одном окне:
    - пара (IP, email): не даёт подбирать пароль к конкретному аккаунту;
    - IP целиком: не даёт перебирать много аккаунтов с одного адреса.
    Счётчик привязан к IP, поэтому посторонний не может заблокировать чужой аккаунт
    со своего адреса. Успешный вход сбрасывает счётчик пары.
    """

    def __init__(self, max_attempts: int, max_attempts_per_ip: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.max_attempts_per_ip = max_attempts_per_ip
        self.window = window_seconds

    @staticmethod
    def _pair_key(ip: str, email: str) -> str:
        # email хешируем: не храним адреса открытым текстом в ключах Redis
        return f"login_fail:pair:{ip}:{hashlib.sha256(email.encode()).hexdigest()[:32]}"

    @staticmethod
    def _ip_key(ip: str) -> str:
        return f"login_fail:ip:{ip}"

    async def _blocked_for(self, client, key: str, limit: int) -> int:
        """Секунд до конца блокировки по ключу (0 — не заблокирован)."""
        count = await client.get(key)
        if count is not None and int(count) >= limit:
            return max(1, await client.ttl(key))
        return 0

    async def check(self, ip: str, email: str) -> None:
        """RateLimitError, если попыток уже слишком много (пароль при этом не проверяется)."""
        client = await get_redis()
        retry_after = max(
            await self._blocked_for(client, self._pair_key(ip, email), self.max_attempts),
            await self._blocked_for(client, self._ip_key(ip), self.max_attempts_per_ip),
        )
        if retry_after:
            raise RateLimitError("Too many failed login attempts", retry_after=retry_after)

    async def record_failure(self, ip: str, email: str) -> None:
        client = await get_redis()
        for key in (self._pair_key(ip, email), self._ip_key(ip)):
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, self.window)

    async def reset(self, ip: str, email: str) -> None:
        client = await get_redis()
        await client.delete(self._pair_key(ip, email))
