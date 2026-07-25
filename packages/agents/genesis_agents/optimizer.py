"""Prompt optimizer (Phase 4, FR-06).

Rewrites a raw idea into a model-aware prompt, then improves it one section at a time so the
loop engine produces a real, ordered refinement history. Rule-based today; `improve()` is the
seam where an LLM rewriter can drop in later without touching the loop engine.
"""

from .scoring import Score

# (marker-regex-free) section text keyed by scoring dimension; "prepend" for the role line.
_SECTIONS: dict[str, tuple[str, str]] = {
    "role": ("You are an expert software architect and engineer.\n\n", "prepend"),
    "requirements": (
        "\n# Requirements\n"
        "- Break the objective into concrete, testable requirements.\n"
        "- Specify the data model, API surface, and UI where relevant.\n",
        "append",
    ),
    "output_format": (
        "\n# Output format\n"
        "Return a structured plan, then the implementation with explicit file paths.\n",
        "append",
    ),
    "constraints": (
        "\n# Constraints\n"
        "- Production-ready: include tests, error handling, and documentation.\n"
        "- Adhere to the project's fixed technology stack.\n",
        "append",
    ),
}

# Order in which missing sections are added (highest scoring weight first).
_ORDER = ["requirements", "role", "output_format", "constraints"]

_DETAIL = "\n# Notes\nBe explicit and specific; prefer concrete names over placeholders.\n"


class PromptOptimizer:
    def initial(self, idea: str) -> str:
        return f"# Objective\n{idea.strip()}\n"

    def improve(self, prompt: str, score: Score) -> str:
        for dim in _ORDER:
            if score.breakdown.get(dim, 0.0) < 1.0:
                text, how = _SECTIONS[dim]
                return text + prompt if how == "prepend" else prompt + text
        # All sections present but still below threshold -> add detail to lift specificity.
        return prompt + _DETAIL
