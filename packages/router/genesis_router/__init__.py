"""GenesisAI LLM router (SRS §4)."""

from .errors import (
    AllProvidersFailedError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from .providers import (
    REGISTRY,
    OpenAICompatibleProvider,
    Provider,
    ProviderConfig,
    env_key_resolver,
)
from .router import KeyResolver, ProviderFactory, Router
from .types import Capabilities, Completion, CompletionRequest, Message, Usage

__all__ = [
    "REGISTRY",
    "AllProvidersFailedError",
    "Capabilities",
    "Completion",
    "CompletionRequest",
    "KeyResolver",
    "Message",
    "OpenAICompatibleProvider",
    "Provider",
    "ProviderConfig",
    "ProviderError",
    "ProviderFactory",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "RateLimitError",
    "Router",
    "Usage",
    "env_key_resolver",
]
