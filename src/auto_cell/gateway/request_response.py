"""MQTT 5.0 Response Topic + Correlation Data request-response."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from pydantic import BaseModel, Field

from auto_cell.gateway.correlation import generate_correlation_id, generate_request_id, now_iso
from auto_cell.gateway.idempotency import IdempotencyStore
from auto_cell.gateway.mqtt_client import MqttClient
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes


class MqttCommandPayload(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str
    request_id: str
    timestamp: str
    source: str = "brain"
    response_topic: str | None = None
    message_expiry_interval: int | None = None


class MqttAckPayload(BaseModel):
    status: str
    correlation_id: str
    request_id: str
    timestamp: str
    source: str = "gateway"
    result: dict[str, Any] | None = None


class RequestResponseClient(MqttClient):
    """Publish cmd and await matching ack via Correlation Data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._pending: dict[str, asyncio.Future[MqttAckPayload]] = {}
        self._pending_lock = threading.Lock()
        self._idempotency = IdempotencyStore(ttl_seconds=86400)
        self._subscribed_response_topics: set[str] = set()

    def _dispatch_ack(
        self,
        topic: str,
        ack: dict[str, Any],
        properties: Properties | None,
    ) -> None:
        corr = ""
        if properties is not None and hasattr(properties, "CorrelationData") and properties.CorrelationData:
            corr = properties.CorrelationData.decode("utf-8")
        with self._pending_lock:
            future = self._pending.pop(corr, None)
        if future is None or future.done():
            return
        try:
            ack_payload = MqttAckPayload(**ack)
        except Exception as exc:
            ack_payload = MqttAckPayload(
                status="failed",
                correlation_id=corr,
                request_id="unknown",
                timestamp=now_iso(),
                source="gateway",
                result={"error": str(exc)},
            )
        loop = future.get_loop()
        loop.call_soon_threadsafe(future.set_result, ack_payload)

    async def request(
        self,
        cu: str,
        device_id: str,
        function_id: str,
        args: dict[str, Any],
        *,
        timeout: float = 10.0,
        request_id: str | None = None,
        expiry_interval: int | None = 60,
    ) -> MqttAckPayload:
        request_id = request_id or generate_request_id()
        correlation_id = generate_correlation_id()
        response_topic = f"cell/{cu}/ack/{device_id}/{function_id}"
        cmd_topic = f"cell/{cu}/cmd/{device_id}/{function_id}"

        payload = MqttCommandPayload(
            args=args,
            correlation_id=correlation_id,
            request_id=request_id,
            timestamp=now_iso(),
            response_topic=response_topic,
            message_expiry_interval=expiry_interval,
        )

        props = Properties(PacketTypes.PUBLISH)
        props.ResponseTopic = response_topic
        props.CorrelationData = correlation_id.encode("utf-8")
        if expiry_interval:
            props.MessageExpiryInterval = expiry_interval

        loop = asyncio.get_event_loop()
        future: asyncio.Future[MqttAckPayload] = loop.create_future()
        with self._pending_lock:
            self._pending[correlation_id] = future

        # Subscribe once per response topic; reuse the shared dispatcher for
        # parallel in-flight requests.
        if response_topic not in self._subscribed_response_topics:
            self._subscribed_response_topics.add(response_topic)
            await self.subscribe(response_topic, self._dispatch_ack, qos=1)

        self.publish(cmd_topic, payload.model_dump(), qos=1, properties=props)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return MqttAckPayload(
                status="timeout",
                correlation_id=correlation_id,
                request_id=request_id,
                timestamp=now_iso(),
                source="gateway",
                result={"error": f"timeout after {timeout}s"},
            )
        finally:
            with self._pending_lock:
                self._pending.pop(correlation_id, None)

    def request_sync(
        self,
        cu: str,
        device_id: str,
        function_id: str,
        args: dict[str, Any],
        *,
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> MqttAckPayload:
        """Synchronous wrapper for Phase 1.

        Must be called from a thread without a running event loop. Calling it
        from inside an async loop will raise RuntimeError to avoid nested loops.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.request(cu, device_id, function_id, args, timeout=timeout, **kwargs)
            )
        raise RuntimeError(
            "request_sync cannot be called from a running event loop; use request() instead"
        )
