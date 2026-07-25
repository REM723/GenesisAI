# packages/router — genesis_router

LLM routing and provider adapters (SRS §4). Each agent declares `Capabilities`
(context length, code strength, tool use, cost ceiling); the `Router` picks the cheapest
provider that satisfies them and falls back through the rest, cheapest-first, on any
recoverable provider error (rate limit, timeout, unavailable).

All 7 providers (OpenAI, Grok, Gemini, DeepSeek, Mistral, OpenRouter, Ollama) share one
`OpenAICompatibleProvider` over their OpenAI-compatible endpoints — **adding a provider is
one `REGISTRY` row, no new code.**

## Public interface

```python
from genesis_router import Router, Capabilities, CompletionRequest, Message

router = Router()  # uses REGISTRY + env-based keys
completion = await router.complete(
    CompletionRequest(messages=[Message(role="user", content="…")]),
    Capabilities(min_code_strength=8, needs_tools=True, max_blended_cost_per_1k=0.01),
)
router.total_cost()
router.total_tokens()
router.ledger  # per-run accounting
```

The router returns a `Completion` with a `Usage` record; **it does not write the DB** —
persistence against project/run wires in at Phase 5 (needs the run record). Provider
pricing/capabilities in `providers.REGISTRY` are a tunable calibration table.

## Test

```bash
pip install -e packages/router -r requirements-dev.txt
pytest packages/router/tests        # providers are mocked; no live model calls
```
