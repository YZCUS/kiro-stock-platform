"""
Order execution command models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict
from uuid import UUID


@dataclass(frozen=True)
class OrderExecutionCommand:
    """A durable command boundary between order intent approval and broker execution."""

    order_intent_id: int
    user_id: UUID
    idempotency_key: str
    attempt: int = 1
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_intent(cls, intent, attempt: int = 1) -> "OrderExecutionCommand":
        return cls(
            order_intent_id=intent.id,
            user_id=intent.user_id,
            idempotency_key=intent.idempotency_key,
            attempt=attempt,
            metadata={
                "source": intent.source,
                "client_order_id": intent.client_order_id,
            },
        )

    def to_stream_fields(self) -> Dict[str, str]:
        """Serialize this command into Redis Stream string fields."""
        return {
            "order_intent_id": str(self.order_intent_id),
            "user_id": str(self.user_id),
            "idempotency_key": self.idempotency_key,
            "attempt": str(self.attempt),
            "requested_at": self.requested_at.isoformat(),
            "metadata_json": json.dumps(self.metadata, default=str),
        }

    @classmethod
    def from_stream_fields(cls, fields: Dict[str, Any]) -> "OrderExecutionCommand":
        """Deserialize Redis Stream fields into a command."""
        normalized = {
            _decode_stream_value(key): _decode_stream_value(value)
            for key, value in fields.items()
        }
        metadata = json.loads(normalized.get("metadata_json") or "{}")
        requested_at_raw = normalized.get("requested_at")
        requested_at = (
            datetime.fromisoformat(requested_at_raw)
            if requested_at_raw
            else datetime.now(timezone.utc)
        )

        return cls(
            order_intent_id=int(normalized["order_intent_id"]),
            user_id=UUID(normalized["user_id"]),
            idempotency_key=normalized["idempotency_key"],
            attempt=int(normalized.get("attempt") or 1),
            requested_at=requested_at,
            metadata=metadata,
        )


def _decode_stream_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
