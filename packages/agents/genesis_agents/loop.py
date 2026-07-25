"""Prompt loop engine (Phase 4, FR-07).

Iterate optimize -> score until the quality threshold is met or the iteration cap is hit.
Every iteration (prompt + score) is returned in order so the caller can persist the full,
ordered history to `prompt_versions`.
"""

from dataclasses import dataclass

from .optimizer import PromptOptimizer
from .scoring import Score, score_prompt


@dataclass(frozen=True)
class Iteration:
    version: int
    prompt: str
    score: float


class LoopEngine:
    def __init__(
        self,
        optimizer: PromptOptimizer | None = None,
        threshold: float = 0.8,
        max_iterations: int = 6,
    ) -> None:
        self._optimizer = optimizer or PromptOptimizer()
        self._threshold = threshold
        self._max_iterations = max_iterations

    def run(self, idea: str) -> list[Iteration]:
        prompt = self._optimizer.initial(idea)
        iterations: list[Iteration] = []
        for version in range(1, self._max_iterations + 1):
            score: Score = score_prompt(prompt)
            iterations.append(Iteration(version=version, prompt=prompt, score=score.total))
            if score.total >= self._threshold:
                break
            prompt = self._optimizer.improve(prompt, score)
        return iterations
