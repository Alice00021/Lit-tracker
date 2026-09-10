from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from common import Base
from app.core.config import settings

# Создаём движок БД
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """Получить сессию БД для Dependency Injection"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Создать таблицы (для разработки)"""
    async with engine.begin() as conn:
        from app.models import User, Book, ReadingEntry
        await conn.run_sync(Base.metadata.create_all)