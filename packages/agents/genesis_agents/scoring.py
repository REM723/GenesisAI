"""Heuristic prompt-quality scorer (Phase 4, FR-07).

Deterministic and offline: scores a prompt on the dimensions of a well-formed, model-aware
prompt — role, requirements, constraints, output format, and specificity. Total is a
weighted sum in [0, 1]. No model calls, so AC-01 is reproducible and NFR-02 is trivial.
"""

import re
from dataclasses import dataclass

_WEIGHTS = {
    "role": 0.20,
    "requirements": 0.25,
    "constraints": 0.15,
    "output_format": 0.20,
    "specificity": 0.20,
}


@dataclass(frozen=True)
class Score:
    total: float
    breakdown: dict[str, float]


def _present(pattern: str, text: str) -> float:
    return 1.0 if re.search(pattern, text, re.IGNORECASE) else 0.0


def _specificity(word_count: int) -> float:
    # Reward prompts in a substantive-but-focused range; never zero (avoids dead scores).
    if 40 <= word_count <= 400:
        return 1.0
    if word_count < 40:
        return word_count / 40
    return max(0.3, 400 / word_count)


def score_prompt(prompt: str) -> Score:
    breakdown = {
        "role": _present(
            r"you are|act as|as an? .*(engineer|architect|developer|assistant)", prompt
        ),
        "requirements": _present(r"#+\s*requirements|requirements:", prompt),
        "constraints": _present(r"#+\s*constraints|constraints:", prompt),
        "output_format": _present(
            r"#+\s*output|output format|return |respond with|format:", prompt
        ),
        "specificity": _specificity(len(re.findall(r"\w+", prompt))),
    }
    total = sum(_WEIGHTS[k] * v for k, v in breakdown.items())
    return Score(total=round(total, 4), breakdown=breakdown)
