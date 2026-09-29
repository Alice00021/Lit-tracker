from common import RedisCache
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.cache = RedisCache(prefix="rate")

    @staticmethod
    def _client_ip(request: Request) -> str:
        # За nginx request.client.host — это IP самого nginx, а не юзера.
        # Nginx кладёт реальный IP в X-Forwarded-For (см. nginx/nginx.conf).
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        # Пропускаем служебные
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/metrics"]:
            return await call_next(request)

        client_ip = self._client_ip(request)
        key = f"{client_ip}:{request.url.path}"

        count = await self.cache.incr(key, ttl=self.window)

        if count > self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - count))
        return response