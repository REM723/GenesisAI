"""GenesisAI agents package. Phase 4: prompt optimizer + loop engine.
The LangGraph agent workflow (SRS §6) lands in Phase 5."""

from .loop import Iteration, LoopEngine
from .optimizer import PromptOptimizer
from .scoring import Score, score_prompt

__all__ = ["Iteration", "LoopEngine", "PromptOptimizer", "Score", "score_prompt"]
