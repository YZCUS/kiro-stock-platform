"""
Generic Redis Streams task queue adapter.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import socket
from typing import Any, Optional

import redis

from domain.workers import IStreamTaskQueue, StreamTaskCommand


class RedisStreamTaskQueue(IStreamTaskQueue):
    """Durable Redis Streams adapter for generic background tasks."""

    def __init__(
        self,
        redis_client: redis.Redis,
        stream_name: str,
        consumer_group: str,
        consumer_name: Optional[str] = None,
        dead_letter_stream: Optional[str] = None,
        max_attempts: int = 3,
        pending_idle_ms: int = 60000,
        stream_maxlen: int = 100000,
        dead_letter_maxlen: int = 10000,
    ) -> None:
        if redis_client is None:
            raise ValueError("Redis client is required for Redis Streams task queue")

        self.redis_client = redis_client
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name or socket.gethostname()
        self.dead_letter_stream = dead_letter_stream or f"{stream_name}_dead"
        self.max_attempts = max_attempts
        self.pending_idle_ms = pending_idle_ms
        self.stream_maxlen = stream_maxlen
        self.dead_letter_maxlen = dead_letter_maxlen
        self._group_ready = False

    async def enqueue(self, command: StreamTaskCommand) -> None:
        await self._ensure_consumer_group()
        await asyncio.to_thread(
            self.redis_client.xadd,
            self.stream_name,
            command.to_stream_fields(),
            maxlen=self.stream_maxlen,
            approximate=True,
        )

    async def dequeue(
        self, timeout: Optional[float] = None
    ) -> Optional[StreamTaskCommand]:
        await self._ensure_consumer_group()

        claimed = await self._claim_stale_pending()
        if claimed is not None:
            return claimed

        response = await asyncio.to_thread(
            self.redis_client.xreadgroup,
            self.consumer_group,
            self.consumer_name,
            {self.stream_name: ">"},
            count=1,
            block=self._timeout_to_block_ms(timeout),
        )
        if not response:
            return None

        _, messages = response[0]
        if not messages:
            return None

        return self._command_from_message(messages[0])

    async def ack(self, command: StreamTaskCommand) -> None:
        message_id = command.metadata.get("_redis_message_id")
        if not message_id:
            return None

        await asyncio.to_thread(
            self.redis_client.xack,
            self.stream_name,
            self.consumer_group,
            message_id,
        )

    async def fail(self, command: StreamTaskCommand, error: Exception) -> None:
        failed_at = datetime.now(timezone.utc).isoformat()
        retry_metadata = {
            key: value
            for key, value in command.metadata.items()
            if not str(key).startswith("_redis_") and key != "_queue_backend"
        }
        retry_metadata.update(
            {
                "last_error": str(error),
                "last_failed_at": failed_at,
            }
        )

        if command.attempt >= self.max_attempts:
            failed_command = StreamTaskCommand(
                task_type=command.task_type,
                payload=command.payload,
                idempotency_key=command.idempotency_key,
                attempt=command.attempt,
                requested_at=command.requested_at,
                metadata=retry_metadata,
            )
            dead_fields = failed_command.to_stream_fields()
            dead_fields["failed_attempts"] = str(command.attempt)
            dead_fields["dead_lettered_at"] = failed_at
            await asyncio.to_thread(
                self.redis_client.xadd,
                self.dead_letter_stream,
                dead_fields,
                maxlen=self.dead_letter_maxlen,
                approximate=True,
            )
            await self.ack(command)
            return None

        retry_command = StreamTaskCommand(
            task_type=command.task_type,
            payload=command.payload,
            idempotency_key=command.idempotency_key,
            attempt=command.attempt + 1,
            requested_at=command.requested_at,
            metadata=retry_metadata,
        )
        await self.enqueue(retry_command)
        await self.ack(command)

    async def _claim_stale_pending(self) -> Optional[StreamTaskCommand]:
        if self.pending_idle_ms <= 0 or not hasattr(self.redis_client, "xautoclaim"):
            return None

        response = await asyncio.to_thread(
            self.redis_client.xautoclaim,
            self.stream_name,
            self.consumer_group,
            self.consumer_name,
            min_idle_time=self.pending_idle_ms,
            start_id="0-0",
            count=1,
        )
        messages = self._extract_claimed_messages(response)
        if not messages:
            return None

        return self._command_from_message(messages[0])

    def _command_from_message(self, message) -> StreamTaskCommand:
        message_id, fields = message
        command = StreamTaskCommand.from_stream_fields(fields)
        command.metadata.update(
            {
                "_queue_backend": "redis_streams",
                "_redis_stream": self.stream_name,
                "_redis_group": self.consumer_group,
                "_redis_message_id": _decode_value(message_id),
            }
        )
        return command

    def _extract_claimed_messages(self, response) -> list:
        if not response:
            return []
        if isinstance(response, (list, tuple)) and len(response) >= 2:
            return response[1] or []
        return []

    async def _ensure_consumer_group(self) -> None:
        if self._group_ready:
            return None

        try:
            await asyncio.to_thread(
                self.redis_client.xgroup_create,
                self.stream_name,
                self.consumer_group,
                id="0",
                mkstream=True,
            )
        except redis.exceptions.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

        self._group_ready = True

    def _timeout_to_block_ms(self, timeout: Optional[float]) -> Optional[int]:
        if timeout is None:
            return 0
        if timeout <= 0:
            return None
        return int(timeout * 1000)


def _decode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
