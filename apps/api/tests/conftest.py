"""Test fixtures. Integration fixtures skip cleanly when Postgres/Redis are unreachable
(run `make up` first). Unit tests (e.g. test_crypto) need no infrastructure.
"""

import base64
import os

# Set required secrets before Settings is first constructed.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ACCESS_TTL", "900")
os.environ.setdefault("GENESIS_ENCRYPTION_KEY", base64.b64encode(b"0" * 32).decode())

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from redis.exceptions import RedisError  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import make_engine, make_sessionmaker  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

get_settings.cache_clear()
SETTINGS = get_settings()


@pytest.fixture
async def engine():
    eng = make_engine(SETTINGS.database_url)
    try:
        async with eng.connect() as conn:
            await conn.execute(text("select 1"))
    except (SQLAlchemyError, OSError):
        await eng.dispose()
        pytest.skip("Postgres not reachable — run `make up`")
    # ponytail: create/drop against the disposable compose DB; use a dedicated test DB if reused.
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def redis_client():
    r: Redis = Redis.from_url(SETTINGS.redis_url, decode_responses=True)
    try:
        await r.ping()
    except (RedisError, OSError):
        await r.aclose()
        pytest.skip("Redis not reachable — run `make up`")
    await r.flushdb()
    yield r
    await r.flushdb()
    await r.aclose()


class _FakeRunner:
    """Deterministic agent runner for API tests — no live model calls."""

    async def run(self, agent: str, prompt: str) -> str:
        return f"{agent}-output"


@pytest.fixture
async def client(engine, redis_client):
    app = create_app()
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.redis = redis_client
    app.state.agent_runner = _FakeRunner()
    app.state.background_tasks = set()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
