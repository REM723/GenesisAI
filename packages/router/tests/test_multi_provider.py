"""AC-05: the same project request runs successfully on at least three providers.

Deterministic proof via the real REGISTRY + a fake factory (no live calls). A live run with
real keys is the remaining end-to-end confirmation, noted in the AC verification doc.
"""

import pytest
from genesis_router import (
    REGISTRY,
    Capabilities,
    Completion,
    CompletionRequest,
    Message,
    ProviderConfig,
    Router,
    Usage,
)

REQUEST = CompletionRequest(messages=[Message(role="user", content="build a habit tracker")])


class _Fake:
    def __init__(self, config: ProviderConfig, key: str) -> None:
        self._config = config

    async def complete(self, request: CompletionRequest) -> Completion:
        c = self._config
        return Completion(
            provider=c.name,
            model=c.model,
            text="ok",
            usage=Usage(provider=c.name, model=c.model, prompt_tokens=5, completion_tokens=5),
        )


@pytest.mark.parametrize("provider", ["openai", "deepseek", "gemini"])
async def test_same_request_runs_on_each_provider(provider: str) -> None:
    def resolver(cfg: ProviderConfig) -> str | None:
        return "test-key" if cfg.name == provider else None

    router = Router(REGISTRY, key_resolver=resolver, provider_factory=_Fake)
    result = await router.complete(REQUEST, Capabilities())

    assert result.provider == provider
    assert result.text == "ok"
