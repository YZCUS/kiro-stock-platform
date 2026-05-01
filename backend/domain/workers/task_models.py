"""
Generic worker task command models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict
from uuid import uuid4


@dataclass(frozen=True)
class StreamTaskCommand:
    """Durable command envelope for non-order background workers."""

    task_type: str
    payload: Dict[str, Any]
    idempotency_key: str = field(default_factory=lambda: str(uuid4()))
    attempt: int = 1
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_stream_fields(self) -> Dict[str, str]:
        return {
            "task_type": self.task_type,
            "payload_json": json.dumps(self.payload, default=str),
            "idempotency_key": self.idempotency_key,
            "attempt": str(self.attempt),
            "requested_at": self.requested_at.isoformat(),
            "metadata_json": json.dumps(self.metadata, default=str),
        }

    @classmethod
    def from_stream_fields(cls, fields: Dict[str, Any]) -> "StreamTaskCommand":
        normalized = {
            _decode_stream_value(key): _decode_stream_value(value)
            for key, value in fields.items()
        }
        requested_at_raw = normalized.get("requested_at")
        requested_at = (
            datetime.fromisoformat(requested_at_raw)
            if requested_at_raw
            else datetime.now(timezone.utc)
        )
        return cls(
            task_type=normalized["task_type"],
            payload=json.loads(normalized.get("payload_json") or "{}"),
            idempotency_key=normalized["idempotency_key"],
            attempt=int(normalized.get("attempt") or 1),
            requested_at=requested_at,
            metadata=json.loads(normalized.get("metadata_json") or "{}"),
        )


def _decode_stream_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
