"""GenesisAI agents package. Phase 4: prompt optimizer + loop engine.
The LangGraph agent workflow (SRS §6) lands in Phase 5."""

from .agents import AGENT_SEQUENCE, AGENTS, AgentRunner, AgentSpec, RouterAgentRunner
from .loop import Iteration, LoopEngine
from .optimizer import PromptOptimizer
from .review import AlwaysPassReviewer, Reviewer
from .scoring import Score, score_prompt
from .workflow import WorkflowState, build_workflow, initial_state

__all__ = [
    "AGENTS",
    "AGENT_SEQUENCE",
    "AgentRunner",
    "AgentSpec",
    "AlwaysPassReviewer",
    "Iteration",
    "LoopEngine",
    "PromptOptimizer",
    "Reviewer",
    "RouterAgentRunner",
    "Score",
    "WorkflowState",
    "build_workflow",
    "initial_state",
    "score_prompt",
]
