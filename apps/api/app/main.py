from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from redis.asyncio import Redis

from app import agents_api, api_keys, auth
from app.config import Settings, get_settings
from app.db import make_engine, make_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="GenesisAI API", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
        return {"status": "ok", "env": settings.env}

    app.include_router(auth.router)
    app.include_router(api_keys.router)
    app.include_router(agents_api.router)
    return app


app = create_app()
