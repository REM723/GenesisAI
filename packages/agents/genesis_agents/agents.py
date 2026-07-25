"""Agent specs + the real runner (SRS §6).

An AgentRunner turns a prompt into an artifact. The real one calls the Phase-2 router;
tests inject a fake so no live model calls happen. Nodes stay DB-free — persistence and
streaming are handled by the orchestrator via injected callbacks.
"""

from dataclasses import dataclass
from typing import Protocol


class AgentRunner(Protocol):
    async def run(self, agent: str, prompt: str) -> str: ...


@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    produces: str  # context-memory kind: requirement | decision | artifact


# SRS §6 responsibility table. `reviewed` agents pass through the Code Reviewer gate.
AGENTS: list[AgentSpec] = [
    AgentSpec(
        "product_manager",
        "Turn the idea into structured requirements, user stories, and scope.",
        "requirement",
    ),
    AgentSpec(
        "architect",
        "Design the architecture, stack, module boundaries, and a task list.",
        "decision",
    ),
    AgentSpec(
        "backend", "Generate API code, models, and migrations from the task list.", "artifact"
    ),
    AgentSpec(
        "frontend", "Generate pages, components, state, and styling from the task list.", "artifact"
    ),
    AgentSpec(
        "qa", "Produce unit and integration tests and a defect report for the code.", "artifact"
    ),
    AgentSpec("devops", "Produce a Dockerfile, CI workflow, and deployment guide.", "artifact"),
    AgentSpec(
        "documentation", "Produce README, API docs, architecture doc, and setup guide.", "artifact"
    ),
]

AGENT_SEQUENCE = [spec.name for spec in AGENTS]
SPECS = {spec.name: spec for spec in AGENTS}
REVIEWED = {"backend", "frontend"}  # code-gen agents gated by the reviewer


class RouterAgentRunner:
    """Real runner: routes each agent's prompt through the LLM router (Phase 2)."""

    def __init__(self, router: object, capabilities_for: object) -> None:
        # Kept light to avoid a hard import cycle; wired concretely by the orchestrator.
        self._router = router
        self._capabilities_for = capabilities_for

    async def run(self, agent: str, prompt: str) -> str:
        from genesis_router import (
            CompletionRequest,
            Message,
        )  # local import: optional dep at runtime

        caps = self._capabilities_for(agent)  # type: ignore[operator]
        request = CompletionRequest(messages=[Message(role="user", content=prompt)])
        completion = await self._router.complete(request, caps)  # type: ignore[attr-defined]
        return str(completion.text)
