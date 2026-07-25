"""Opaque cursor pagination (SRS §9: list endpoints are cursor-paginated).

Cursor encodes the last row's (created_at, id) so the next page is a keyset query — stable
under inserts, unlike offset pagination.
"""

import base64
import json
import uuid
from datetime import datetime


def encode_cursor(created_at: datetime, item_id: uuid.UUID) -> str:
    raw = json.dumps({"ts": created_at.isoformat(), "id": str(item_id)}).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode())
    data = json.loads(raw)
    return datetime.fromisoformat(data["ts"]), uuid.UUID(data["id"])
