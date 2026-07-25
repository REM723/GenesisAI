"""The router: cheapest-satisfying provider selection + ordered fallback + usage ledger."""

import logging
from collections.abc import Callable

from .errors import AllProvidersFailedError, ProviderError
from .providers import (
    REGISTRY,
    OpenAICompatibleProvider,
    Provider,
    ProviderConfig,
    env_key_resolver,
)
from .types import Capabilities, Completion, CompletionRequest, Usage

logger = logging.getLogger("genesis.router")

ProviderFactory = Callable[[ProviderConfig, str], Provider]
KeyResolver = Callable[[ProviderConfig], str | None]


class Router:
    def __init__(
        self,
        registry: dict[str, ProviderConfig] | None = None,
        key_resolver: KeyResolver = env_key_resolver,
        provider_factory: ProviderFactory = OpenAICompatibleProvider,
    ) -> None:
        self._registry = registry if registry is not None else REGISTRY
        self._resolve_key = key_resolver
        self._factory = provider_factory
        self._ledger: list[Usage] = []

    def candidates(self, caps: Capabilities) -> list[tuple[ProviderConfig, str]]:
        """Providers meeting the capabilities and having a usable key, cheapest first."""
        chain: list[tuple[ProviderConfig, str]] = []
        for cfg in self._registry.values():
            if cfg.context_length < caps.min_context:
                continue
            if cfg.code_strength < caps.min_code_strength:
                continue
            if caps.needs_tools and not cfg.supports_tools:
                continue
            ceiling = caps.max_blended_cost_per_1k
            if ceiling is not None and cfg.blended_price_per_1k > ceiling:
                continue
            key = self._resolve_key(cfg)
            if key is None:
                continue
            chain.append((cfg, key))
        chain.sort(key=lambda item: item[0].blended_price_per_1k)
        return chain

    async def complete(self, request: CompletionRequest, caps: Capabilities) -> Completion:
        chain = self.candidates(caps)
        if not chain:
            raise AllProvidersFailedError({}, "no provider satisfies the required capabilities")
        errors: dict[str, str] = {}
        for cfg, key in chain:
            provider = self._factory(cfg, key)
            try:
                result = await provider.complete(request)
            except ProviderError as exc:
                errors[cfg.name] = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "provider %s failed (%s); falling back", cfg.name, type(exc).__name__
                )
                continue
            self._ledger.append(result.usage)
            return result
        raise AllProvidersFailedError(errors)

    @property
    def ledger(self) -> list[Usage]:
        return list(self._ledger)

    def total_cost(self) -> float:
        return sum(u.cost_usd for u in self._ledger)

    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self._ledger)
