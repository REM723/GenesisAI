"""Phase 4 exit criteria: AC-01 (20 ideas above threshold), ordered version history,
and the NFR-02 latency budget (< 5s p95). All offline — no model calls."""

import time

from genesis_agents import LoopEngine, PromptOptimizer, score_prompt

THRESHOLD = 0.8

IDEAS = [
    "A mobile-first habit tracker with streaks and weekly email summaries.",
    "A URL shortener with click analytics and custom aliases.",
    "A recipe manager that generates shopping lists from selected meals.",
    "A personal finance dashboard aggregating bank transactions by category.",
    "A team standup bot that collects async updates and posts a digest.",
    "A markdown note app with backlinks and full-text search.",
    "A job board that matches candidates to postings by skills.",
    "A subscription tracker that warns before free trials convert.",
    "A flashcard app with spaced repetition scheduling.",
    "A booking system for a small barbershop with reminders.",
    "A blog platform with scheduled publishing and RSS.",
    "An expense-splitting app for shared households.",
    "A workout planner that adapts to logged performance.",
    "A customer feedback widget with sentiment tagging.",
    "A podcast host with transcript generation and chapters.",
    "A plant-care reminder app tuned to species and season.",
    "An inventory tracker for a small online shop.",
    "A time-tracking tool that bills clients from tagged sessions.",
    "A quiz builder with shareable links and score reports.",
    "A changelog generator from merged pull requests.",
]


def test_all_sample_ideas_reach_threshold() -> None:  # AC-01
    engine = LoopEngine(threshold=THRESHOLD)
    for idea in IDEAS:
        iterations = engine.run(idea)
        assert iterations, idea
        assert iterations[-1].score >= THRESHOLD, f"{idea!r} peaked at {iterations[-1].score}"


def test_version_history_is_complete_and_ordered() -> None:
    iterations = LoopEngine(threshold=THRESHOLD).run(IDEAS[0])
    versions = [it.version for it in iterations]
    assert versions == list(range(1, len(iterations) + 1))  # contiguous from 1
    scores = [it.score for it in iterations]
    assert scores == sorted(scores)  # monotonic non-decreasing refinement


def test_iteration_cap_is_respected() -> None:
    # A pathological optimizer that never improves must still terminate at the cap.
    class NoOp(PromptOptimizer):
        def improve(self, prompt: str, score: object) -> str:  # type: ignore[override]
            return prompt

    iterations = LoopEngine(optimizer=NoOp(), threshold=0.99, max_iterations=4).run("x")
    assert len(iterations) == 4


def test_score_reflects_prompt_quality() -> None:
    assert score_prompt("do stuff").total < THRESHOLD
    good = LoopEngine().run(IDEAS[0])[-1].prompt
    assert score_prompt(good).total >= THRESHOLD


def test_latency_budget_p95_under_5s() -> None:  # NFR-02
    engine = LoopEngine(threshold=THRESHOLD)
    timings = []
    for idea in IDEAS:
        start = time.perf_counter()
        engine.run(idea)
        timings.append(time.perf_counter() - start)
    timings.sort()
    p95 = timings[int(len(timings) * 0.95) - 1]
    assert p95 < 5.0, f"p95 optimize latency {p95:.4f}s exceeds 5s"
