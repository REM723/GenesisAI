"""Prompt optimization persistence: version history complete + ordered (Phase 4).
Integration test — requires Postgres."""

from app.db import make_sessionmaker
from app.models import Project, User
from app.prompt_service import optimize_and_persist
from app.repositories import PromptVersionRepository


async def test_optimize_and_persist_writes_ordered_history(engine) -> None:
    maker = make_sessionmaker(engine)
    async with maker() as session:
        user = User(email="p@b.com", password_hash="x")
        session.add(user)
        await session.flush()
        project = Project(user_id=user.id, name="P", idea="A habit tracker with streaks.")
        session.add(project)
        await session.flush()

        prompt = await optimize_and_persist(
            session, project_id=project.id, type="build", idea=project.idea
        )
        await session.commit()

        versions = await PromptVersionRepository(session).list_for_prompt(prompt.id)
        assert len(versions) >= 1
        assert [v.version for v in versions] == list(range(1, len(versions) + 1))
        scores = [v.score for v in versions]
        assert scores == sorted(scores)  # ordered, non-decreasing
        assert prompt.score == versions[-1].score
        assert prompt.score is not None and prompt.score >= 0.8
