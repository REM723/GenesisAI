# packages/agents — genesis_agents

Phase 4: the prompt optimizer + loop engine. Phase 5 adds the LangGraph agent workflow.

`LoopEngine.run(idea)` rewrites a raw idea into a model-aware prompt and iteratively refines
it (`optimizer.improve`) against a heuristic quality score until the threshold (default 0.8)
or the iteration cap (default 6). It returns the full, ordered iteration history so the
caller can persist every version + score to `prompt_versions`.

Scoring is deterministic and offline (`scoring.score_prompt`) — no model calls — so AC-01 is
reproducible and the NFR-02 5s p95 budget is trivially met. `PromptOptimizer.improve` is the
seam where an LLM-based rewriter can drop in later without changing the loop.

## Public interface

```python
from genesis_agents import LoopEngine

iterations = LoopEngine(threshold=0.8, max_iterations=6).run("A habit tracker with streaks.")
final = iterations[-1]  # .version, .prompt, .score
```

## Test

```bash
pip install -e packages/agents -r requirements-dev.txt
pytest packages/agents/tests
```
