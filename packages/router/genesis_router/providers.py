"""Provider configs + the single OpenAI-compatible adapter that serves all 7 providers.

Every supported provider exposes an OpenAI-compatible chat endpoint (Gemini via its
`/openai/` compat path, Ollama via `/v1`), so one adapter parameterized by base_url covers
them all. Adding a provider = one REGISTRY row, no new code (Phase 2 exit criterion).
"""

import os
from typing import Protocol

from pydantic import BaseModel

from .errors import (
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from .types import Completion, CompletionRequest, Usage


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    model: str
    api_key_env: str
    context_length: int
    code_strength: int  # 0..10
    supports_tools: bool
    price_in_per_1k: float
    price_out_per_1k: float
    requires_key: bool = True  # Ollama runs locally, no key needed

    @property
    def blended_price_per_1k(self) -> float:
        return self.price_in_per_1k + self.price_out_per_1k


# Calibration table: pricing and capability ratings drift as providers ship models.
# ponytail: these are tunable defaults, not gospel — update the numbers, not the code.
REGISTRY: dict[str, ProviderConfig] = {
    "ollama": ProviderConfig(
        name="ollama",
        base_url="http://localhost:11434/v1",
        model="llama3.1",
        api_key_env="OLLAMA_API_KEY",
        context_length=128000,
        code_strength=6,
        supports_tools=False,
        price_in_per_1k=0.0,
        price_out_per_1k=0.0,
        requires_key=False,
    ),
    "gemini": ProviderConfig(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model="gemini-1.5-flash",
        api_key_env="GEMINI_API_KEY",
        context_length=1000000,
        code_strength=7,
        supports_tools=True,
        price_in_per_1k=0.000075,
        price_out_per_1k=0.0003,
    ),
    "deepseek": ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
        context_length=64000,
        code_strength=8,
        supports_tools=True,
        price_in_per_1k=0.00014,
        price_out_per_1k=0.00028,
    ),
    "openai": ProviderConfig(
        name="openai",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
        context_length=128000,
        code_strength=9,
        supports_tools=True,
        price_in_per_1k=0.00015,
        price_out_per_1k=0.0006,
    ),
    "openrouter": ProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
        api_key_env="OPENROUTER_API_KEY",
        context_length=128000,
        code_strength=8,
        supports_tools=True,
        price_in_per_1k=0.00015,
        price_out_per_1k=0.0006,
    ),
    "mistral": ProviderConfig(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        model="mistral-small-latest",
        api_key_env="MISTRAL_API_KEY",
        context_length=32000,
        code_strength=6,
        supports_tools=True,
        price_in_per_1k=0.0002,
        price_out_per_1k=0.0006,
    ),
    "grok": ProviderConfig(
        name="grok",
        base_url="https://api.x.ai/v1",
        model="grok-2-latest",
        api_key_env="XAI_API_KEY",
        context_length=131072,
        code_strength=8,
        supports_tools=True,
        price_in_per_1k=0.002,
        price_out_per_1k=0.01,
    ),
    # Groq — fast OpenAI-compatible inference (distinct from xAI "grok" above).
    "groq": ProviderConfig(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
        context_length=131072,
        code_strength=8,
        supports_tools=True,
        price_in_per_1k=0.00059,
        price_out_per_1k=0.00079,
    ),
}


def env_key_resolver(config: ProviderConfig) -> str | None:
    """Resolve a provider API key from the environment. None means 'skip this provider'."""
    key = os.environ.get(config.api_key_env)
    if key is None and not config.requires_key:
        return "local"  # keyless local provider (Ollama)
    return key


class Provider(Protocol):
    async def complete(self, request: CompletionRequest) -> Completion: ...


class OpenAICompatibleProvider:
    """Single adapter over any OpenAI-compatible chat endpoint, via LangChain ChatOpenAI."""

    def __init__(self, config: ProviderConfig, api_key: str) -> None:
        self._config = config
        self._api_key = api_key

    async def complete(self, request: CompletionRequest) -> Completion:
        # Imported lazily so the router (and its tests) don't pay LangChain import cost.
        import openai
        from langchain_core.messages import (
            AIMessage,
            BaseMessage,
            HumanMessage,
            SystemMessage,
        )
        from langchain_openai import ChatOpenAI

        cfg = self._config
        llm = ChatOpenAI(
            base_url=cfg.base_url,
            api_key=self._api_key,
            model=cfg.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_retries=0,  # the router owns fallback, not the client
        )
        messages: list[BaseMessage] = []
        for m in request.messages:
            if m.role == "system":
                messages.append(SystemMessage(m.content))
            elif m.role == "assistant":
                messages.append(AIMessage(m.content))
            else:
                messages.append(HumanMessage(m.content))

        try:
            resp = await llm.ainvoke(messages)
        except openai.RateLimitError as exc:
            raise RateLimitError(str(exc)) from exc
        except openai.APITimeoutError as exc:
            raise ProviderTimeoutError(str(exc)) from exc
        except openai.APIConnectionError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise ProviderUnavailableError(str(exc)) from exc
            raise ProviderError(str(exc)) from exc

        meta = resp.usage_metadata if isinstance(resp, AIMessage) else None
        pt = int(meta["input_tokens"]) if meta else 0
        ct = int(meta["output_tokens"]) if meta else 0
        cost = pt / 1000 * cfg.price_in_per_1k + ct / 1000 * cfg.price_out_per_1k
        return Completion(
            provider=cfg.name,
            model=cfg.model,
            text=str(resp.content),
            usage=Usage(
                provider=cfg.name,
                model=cfg.model,
                prompt_tokens=pt,
                completion_tokens=ct,
                cost_usd=cost,
            ),
        )
