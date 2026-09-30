import asyncio
import os
from contextlib import asynccontextmanager

from common import (
    RequestIDMiddleware,
    close_redis,
    get_logger,
    init_redis,
    setup_cors,
    setup_logging,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.application.services.taste_profile_service import recovery_loop
from app.core.config import settings
from app.core.database import engine
from app.domain.exceptions import AppException, NotFoundError
from app.infrastructure.llm.langgraph.checkpointer import open_checkpointer
from app.infrastructure.llm.langgraph.graph import build_taste_profile_graph
from app.interfaces.api import api_router
from app.interfaces.api.middlewares.rate_limit import RateLimitMiddleware

setup_logging(
    service_name=settings.SERVICE_NAME,
    log_level=settings.LOG_LEVEL,
    json_format=settings.is_production(),
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME}")

    # Redis
    await init_redis(settings.REDIS_URL)
    logger.info(f"✅ Redis connected: {settings.REDIS_URL}")

    # Граф анализа вкуса с чекпоинтами в Postgres + подхват зависших анализов
    async with open_checkpointer(settings.DATABASE_URL) as checkpointer:
        app.state.taste_graph = build_taste_profile_graph(checkpointer)
        recovery_tasks: set = set()
        recovery = asyncio.create_task(recovery_loop(app.state.taste_graph, recovery_tasks))
        logger.info("✅ Taste graph checkpointer ready")

        yield

        recovery.cancel()
        for task in list(recovery_tasks):
            task.cancel()  # чекпоинт остался на последнем узле, после рестарта продолжим
        await asyncio.gather(recovery, *recovery_tasks, return_exceptions=True)

    await close_redis()
    await engine.dispose()
    logger.info("Shutdown")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    description="Literary Tracker API",
    lifespan=lifespan,
)

setup_cors(app, origins=settings.CORS_ORIGINS)

# Все роуты через один router
app.include_router(api_router)

# Метрики
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(
    RateLimitMiddleware,
    limit=settings.RATE_LIMIT_REQUESTS,
    window=settings.RATE_LIMIT_WINDOW,
)
app.add_middleware(RequestIDMiddleware)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": str(exc), "status_code": 404},
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict(), headers=headers)


@app.get("/")
async def root():
    return {"service": settings.SERVICE_NAME, "status": "healthy", "docs": "/docs"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "instance": os.getenv("HOSTNAME", "unknown"),
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )