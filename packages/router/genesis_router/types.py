"""Router data types. Agents speak in Capabilities + CompletionRequest; get a Completion."""

from typing import Literal

from pydantic import BaseModel

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    role: Role
    content: str


class Capabilities(BaseModel):
    """What an agent requires of a provider. The router picks the cheapest match."""

    min_context: int = 0
    min_code_strength: int = 0  # 0..10
    needs_tools: bool = False
    max_blended_cost_per_1k: float | None = None  # USD ceiling on (input+output)/1k


class CompletionRequest(BaseModel):
    messages: list[Message]
    max_tokens: int | None = None
    temperature: float = 0.2


class Usage(BaseModel):
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class Completion(BaseModel):
    provider: str
    model: str
    text: str
    usage: Usage
