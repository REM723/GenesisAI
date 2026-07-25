from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from genesis_agents import RouterAgentRunner
from genesis_router import Capabilities, Router
from redis.asyncio import Redis

from app import agents_api, api_keys, artifacts_api, auth, projects_api, prompts_api
from app.config import Settings, get_settings
from app.db import make_engine, make_sessionmaker


def _capabilities_for(_agent: str) -> Capabilities:
    # All agents need solid code strength; tune per-agent later. ponytail: one profile for now.
    return Capabilities(min_code_strength=6)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.agent_runner = RouterAgentRunner(Router(), _capabilities_for)
    app.state.background_tasks = set()
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
    app.include_router(projects_api.router)
    app.include_router(prompts_api.router)
    app.include_router(agents_api.router)
    app.include_router(artifacts_api.router)
    return app


app = create_app()
