"""SqlContextStore round-trip against real Postgres (the relational half of AC-02).

The vector half + full recall is proven in packages/memory/tests. Integration test —
requires Postgres.
"""

import uuid

from genesis_memory import ContextRecord

from app.db import make_sessionmaker
from app.memory_store import SqlContextStore
from app.models import Project, User


async def test_sql_context_store_roundtrip(engine) -> None:
    maker = make_sessionmaker(engine)
    async with maker() as session:
        user = User(email="ctx@b.com", password_hash="x")
        session.add(user)
        await session.flush()
        project = Project(user_id=user.id, name="P", idea="an idea")
        session.add(project)
        await session.flush()

        store = SqlContextStore(session)
        record = ContextRecord(
            id=str(uuid.uuid4()),
            project_id=str(project.id),
            kind="decision",
            content="Use Redis for the job queue.",
            meta={"agent": "architect"},
        )
        await store.add(record)
        await session.commit()

        got = await store.get_many([record.id])
        assert len(got) == 1
        assert got[0].content == "Use Redis for the job queue."
        assert got[0].kind == "decision"
        assert got[0].meta == {"agent": "architect"}
