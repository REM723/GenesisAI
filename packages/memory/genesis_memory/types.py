"""Context-memory record types. Agents only ever see ContextRecord."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ContextKind = Literal["requirement", "decision", "artifact"]


class ContextRecord(BaseModel):
    id: str
    project_id: str
    kind: ContextKind
    content: str
    meta: dict[str, str] | None = None
    created_at: datetime | None = None
