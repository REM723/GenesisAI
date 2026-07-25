"""Code Reviewer gate (SRS §6). A failing review returns work to the generating agent once."""

from typing import Protocol


class Reviewer(Protocol):
    async def review(self, agent: str, artifact: str) -> bool: ...


class AlwaysPassReviewer:
    async def review(self, agent: str, artifact: str) -> bool:
        return True
