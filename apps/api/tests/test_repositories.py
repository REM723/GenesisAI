"""Repository-layer tests. Integration — requires Postgres."""

from app.db import make_sessionmaker
from app.repositories import ApiKeyRepository, UserRepository


async def test_user_and_apikey_repositories(engine) -> None:
    maker = make_sessionmaker(engine)
    async with maker() as session:
        users = UserRepository(session)
        user = await users.create(email="r@b.com", password_hash="hashed")
        await session.commit()

        assert (await users.get_by_email("r@b.com")).id == user.id
        assert (await users.get(user.id)).email == "r@b.com"
        assert await users.get_by_email("missing@b.com") is None

        keys = ApiKeyRepository(session)
        await keys.create(user_id=user.id, provider="openai", encrypted_key="ciphertext")
        await session.commit()

        stored = await keys.list_for_user(user.id)
        assert len(stored) == 1
        assert stored[0].provider == "openai"
        assert stored[0].encrypted_key == "ciphertext"
