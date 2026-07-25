"""LangGraph workflow (SRS §6): PM → Architect → Backend → Frontend → QA → DevOps → Docs.

Checkpointed (resume from last success), per-agent timeouts, and a Code Reviewer gate after
each code-gen agent that returns work once. The graph is DB-free: persistence and SSE happen
through the injected async `on_event` callback, so the orchestrator owns all side effects.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .agents import AGENTS, REVIEWED, AgentRunner, AgentSpec
from .review import AlwaysPassReviewer, Reviewer

DEFAULT_TIMEOUT = 30.0
MAX_ATTEMPTS = 2  # one regeneration after a failed review

Event = dict[str, Any]
OnEvent = Callable[[Event], Awaitable[None]]


def _merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    return {**a, **b}


class WorkflowState(TypedDict):
    run_id: str
    project_id: str
    idea: str
    outputs: Annotated[dict[str, str], _merge]
    attempts: Annotated[dict[str, int], _merge]
    reviews: Annotated[dict[str, bool], _merge]


def initial_state(run_id: str, project_id: str, idea: str) -> WorkflowState:
    return {
        "run_id": run_id,
        "project_id": project_id,
        "idea": idea,
        "outputs": {},
        "attempts": {},
        "reviews": {},
    }


def _build_prompt(spec: AgentSpec, state: WorkflowState) -> str:
    prior = "\n\n".join(f"## {name}\n{text}" for name, text in state["outputs"].items())
    return f"{spec.role}\n\n# Idea\n{state['idea']}\n\n# Prior work\n{prior or '(none)'}\n"


async def _noop(_event: Event) -> None:
    return None


def _make_node(
    spec: AgentSpec,
    runner: AgentRunner,
    reviewer: Reviewer,
    on_event: OnEvent,
    timeouts: dict[str, float],
) -> Callable[[WorkflowState], Awaitable[dict[str, Any]]]:
    async def node(state: WorkflowState) -> dict[str, Any]:
        agent = spec.name
        await on_event({"type": "start", "run_id": state["run_id"], "agent": agent})
        prompt = _build_prompt(spec, state)
        try:
            output = await asyncio.wait_for(
                runner.run(agent, prompt), timeouts.get(agent, DEFAULT_TIMEOUT)
            )
        except TimeoutError:
            await on_event({"type": "timeout", "run_id": state["run_id"], "agent": agent})
            raise

        attempts = state["attempts"].get(agent, 0) + 1
        passed = await reviewer.review(agent, output) if agent in REVIEWED else True
        await on_event(
            {
                "type": "complete",
                "run_id": state["run_id"],
                "agent": agent,
                "produces": spec.produces,
                "output": output,
                "attempt": attempts,
                "review_passed": passed,
            }
        )
        return {
            "outputs": {agent: output},
            "attempts": {agent: attempts},
            "reviews": {agent: passed},
        }

    return node


def _route(agent: str) -> Callable[[WorkflowState], str]:
    def route(state: WorkflowState) -> str:
        failed = not state["reviews"].get(agent, True)
        if failed and state["attempts"].get(agent, 0) < MAX_ATTEMPTS:
            return "retry"
        return "next"

    return route


def build_workflow(
    runner: AgentRunner,
    reviewer: Reviewer | None = None,
    on_event: OnEvent | None = None,
    timeouts: dict[str, float] | None = None,
    checkpointer: Any = None,
) -> Any:
    reviewer = reviewer or AlwaysPassReviewer()
    on_event = on_event or _noop
    timeouts = timeouts or {}

    # ponytail: langgraph's add_node overloads are strict about node signatures; typing the
    # builder as Any keeps this adapter boundary readable rather than fighting the stubs.
    graph: Any = StateGraph(WorkflowState)
    for spec in AGENTS:
        graph.add_node(spec.name, _make_node(spec, runner, reviewer, on_event, timeouts))

    graph.set_entry_point("product_manager")
    graph.add_edge("product_manager", "architect")
    graph.add_edge("architect", "backend")
    graph.add_conditional_edges(
        "backend", _route("backend"), {"retry": "backend", "next": "frontend"}
    )
    graph.add_conditional_edges("frontend", _route("frontend"), {"retry": "frontend", "next": "qa"})
    graph.add_edge("qa", "devops")
    graph.add_edge("devops", "documentation")
    graph.add_edge("documentation", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
