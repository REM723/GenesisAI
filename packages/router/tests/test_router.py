"""Router tests. No live model calls — providers are faked via an injected factory."""

import pytest
from genesis_router import (
    REGISTRY,
    AllProvidersFailedError,
    Capabilities,
    Completion,
    CompletionRequest,
    Message,
    ProviderConfig,
    ProviderTimeoutError,
    RateLimitError,
    Router,
    Usage,
)
from genesis_router.errors import ProviderError, ProviderUnavailableError

REQ = CompletionRequest(messages=[Message(role="user", content="hi")])
ANY_KEY: str = "test-key"


def _cfg(
    name: str, price: float, *, ctx: int = 128000, code: int = 8, tools: bool = True
) -> ProviderConfig:
    return ProviderConfig(
        name=name,
        base_url=f"https://{name}/v1",
        model=f"{name}-model",
        api_key_env=f"{name.upper()}_KEY",
        context_length=ctx,
        code_strength=code,
        supports_tools=tools,
        price_in_per_1k=price,
        price_out_per_1k=price,
    )


class _Fake:
    """A provider that either returns a canned completion or raises a configured error."""

    def __init__(
        self,
        config: ProviderConfig,
        key: str,
        *,
        error: Exception | None = None,
        tokens: tuple[int, int] = (10, 20),
    ) -> None:
        self._config = config
        self._error = error
        self._tokens = tokens

    async def complete(self, request: CompletionRequest) -> Completion:
        if self._error is not None:
            raise self._error
        cfg, (pt, ct) = self._config, self._tokens
        cost = pt / 1000 * cfg.price_in_per_1k + ct / 1000 * cfg.price_out_per_1k
        return Completion(
            provider=cfg.name,
            model=cfg.model,
            text="ok",
            usage=Usage(
                provider=cfg.name,
                model=cfg.model,
                prompt_tokens=pt,
                completion_tokens=ct,
                cost_usd=cost,
            ),
        )


def _factory(behaviors: dict[str, Exception | None]):
    def make(config: ProviderConfig, key: str) -> _Fake:
        return _Fake(config, key, error=behaviors.get(config.name))

    return make


def _always_keyed(_config: ProviderConfig) -> str:
    return ANY_KEY


async def test_picks_cheapest_satisfying_provider() -> None:
    reg = {"cheap": _cfg("cheap", 0.001), "pricey": _cfg("pricey", 0.01)}
    router = Router(
        reg, key_resolver=_always_keyed, provider_factory=_factory({"cheap": None, "pricey": None})
    )
    result = await router.complete(REQ, Capabilities())
    assert result.provider == "cheap"


async def test_capability_filters_exclude_providers() -> None:
    reg = {"weak": _cfg("weak", 0.001, code=3), "strong": _cfg("strong", 0.01, code=9)}
    router = Router(reg, key_resolver=_always_keyed, provider_factory=_factory({}))
    result = await router.complete(REQ, Capabilities(min_code_strength=8))
    assert result.provider == "strong"  # cheap-but-weak filtered out


@pytest.mark.parametrize(
    "err", [RateLimitError("x"), ProviderTimeoutError("x"), ProviderUnavailableError("x")]
)
async def test_fallback_on_recoverable_error(err: ProviderError, caplog) -> None:
    reg = {"a": _cfg("a", 0.001), "b": _cfg("b", 0.002), "c": _cfg("c", 0.003)}
    router = Router(
        reg, key_resolver=_always_keyed, provider_factory=_factory({"a": err, "b": err, "c": None})
    )
    result = await router.complete(REQ, Capabilities())
    assert result.provider == "c"
    assert "falling back" in caplog.text


async def test_all_providers_failing_raises() -> None:
    reg = {"a": _cfg("a", 0.001), "b": _cfg("b", 0.002)}
    router = Router(
        reg,
        key_resolver=_always_keyed,
        provider_factory=_factory({"a": RateLimitError("x"), "b": RateLimitError("x")}),
    )
    with pytest.raises(AllProvidersFailedError) as exc:
        await router.complete(REQ, Capabilities())
    assert set(exc.value.errors) == {"a", "b"}


async def test_non_provider_error_propagates() -> None:
    reg = {"a": _cfg("a", 0.001), "b": _cfg("b", 0.002)}
    # A ValueError is a bug, not a provider hiccup: it must not be swallowed as fallback.
    router = Router(
        reg, key_resolver=_always_keyed, provider_factory=_factory({"a": ValueError("boom")})
    )
    with pytest.raises(ValueError, match="boom"):
        await router.complete(REQ, Capabilities())


async def test_missing_key_skips_provider() -> None:
    reg = {"nokey": _cfg("nokey", 0.001), "keyed": _cfg("keyed", 0.01)}
    resolver = lambda cfg: None if cfg.name == "nokey" else ANY_KEY  # noqa: E731
    router = Router(reg, key_resolver=resolver, provider_factory=_factory({}))
    result = await router.complete(REQ, Capabilities())
    assert result.provider == "keyed"


async def test_token_and_cost_accounting_across_run() -> None:
    reg = {"a": _cfg("a", 0.001), "b": _cfg("b", 0.01)}
    router = Router(reg, key_resolver=_always_keyed, provider_factory=_factory({}))
    # first call hits cheapest 'a'; force 'b' by requiring a higher code strength unavailable on 'a'
    await router.complete(REQ, Capabilities())  # -> a: 10 in, 20 out @0.001 = 0.00003
    await router.complete(REQ, Capabilities())  # -> a again
    assert router.total_tokens() == 2 * 30
    assert router.total_cost() == pytest.approx(2 * (30 / 1000 * 0.001))
    assert len(router.ledger) == 2


async def test_adding_provider_is_one_registry_row() -> None:
    reg = {name: _cfg(name, 0.01) for name in ("a", "b")}
    reg["cheapest"] = _cfg("cheapest", 0.0001)  # one new row, no code change
    router = Router(reg, key_resolver=_always_keyed, provider_factory=_factory({}))
    result = await router.complete(REQ, Capabilities())
    assert result.provider == "cheapest"


def test_real_registry_has_all_seven_providers() -> None:
    assert set(REGISTRY) == {
        "openai",
        "grok",
        "gemini",
        "deepseek",
        "mistral",
        "openrouter",
        "ollama",
    }
    assert all(c.blended_price_per_1k >= 0 for c in REGISTRY.values())
