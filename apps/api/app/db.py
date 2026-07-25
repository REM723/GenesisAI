from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _async_url(database_url: str) -> str:
    # asyncpg driver requires the +asyncpg scheme; .env uses the plain psql URL.
    if database_url.startswith("postgresql+"):
        return database_url
    return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


def make_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(_async_url(database_url), pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
