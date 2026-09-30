from common import RedisCache
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.interfaces.api.client_ip import get_client_ip


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

        client_ip = get_client_ip(request)
        key = f"{client_ip}:{request.url.path}"

        count = await self.cache.incr(key, ttl=self.window)

        if count > self.limit:
            # HTTPException из middleware FastAPI не превращает в ответ (вышло бы 500),
            # поэтому возвращаем 429 напрямую.
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(self.window)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - count))
        return response