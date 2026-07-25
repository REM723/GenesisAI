"""Provider errors. Subclasses of ProviderError trigger fallback to the next provider;
anything else propagates (a bug, not a provider hiccup)."""


class ProviderError(Exception):
    """Recoverable provider failure — the router falls back to the next candidate."""


class RateLimitError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class AllProvidersFailedError(Exception):
    """No candidate produced a completion."""

    def __init__(self, errors: dict[str, str], message: str = "all providers failed") -> None:
        super().__init__(f"{message}: {errors}")
        self.errors = errors
