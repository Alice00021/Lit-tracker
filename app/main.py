from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from common import setup_logging, get_logger, setup_cors
from app.core.config import settings
from app.core.database import init_db, engine
from app.interfaces.api.book_routes import router as books_router
from app.domain.exceptions import NotFoundError

setup_logging(
    service_name=settings.SERVICE_NAME,
    log_level=settings.LOG_LEVEL,
    json_format=settings.is_production(),
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Starting {settings.SERVICE_NAME}")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    await engine.dispose()
    logger.info("👋 Shutdown")


app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    description="Literary Tracker API",
    lifespan=lifespan,
)

setup_cors(app, origins=settings.CORS_ORIGINS)
app.include_router(books_router)

# Подключаем метрики
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": str(exc), "status_code": 404},
    )


@app.get("/")
async def root():
    return {"service": settings.SERVICE_NAME, "status": "healthy", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )