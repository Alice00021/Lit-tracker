from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from common import RedisCache


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.cache = RedisCache(prefix="rate")

    async def dispatch(self, request: Request, call_next):
        # Пропускаем служебные
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/metrics"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
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