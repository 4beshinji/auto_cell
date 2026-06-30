"""paho-mqtt v2 publisher/subscriber."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties

logger = logging.getLogger(__name__)


def _topic_matches(pattern: str, topic: str) -> bool:
    """Match an MQTT topic against a subscription pattern containing + or #."""
    pattern_parts = pattern.split("/")
    topic_parts = topic.split("/")
    pi = ti = 0
    while pi < len(pattern_parts):
        part = pattern_parts[pi]
        if part == "#":
            return pi == len(pattern_parts) - 1
        if ti >= len(topic_parts):
            return False
        if part != "+" and part != topic_parts[ti]:
            return False
        pi += 1
        ti += 1
    return ti == len(topic_parts)


class MqttClient:
    """MQTT 5.0 publisher/subscriber using paho-mqtt v2."""

    def __init__(
        self,
        client_id: str,
        broker: str,
        port: int = 1883,
        *,
        username: str | None = None,
        password: str | None = None,
        protocol: mqtt.MQTTProtocolVersion = mqtt.MQTTProtocolVersion.MQTTv5,
    ) -> None:
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self._callbacks: dict[str, Callable[[str, dict[str, Any], Properties | None], None]] = {}
        self._subscribe_lock = threading.Lock()
        self._subscribe_futures: dict[int, asyncio.Future[None]] = {}
        self._suback_received: set[int] = set()

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=protocol,
        )
        if username:
            self._client.username_pw_set(username, password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._client.on_subscribe = self._on_subscribe

    # ------------------------------------------------------------------
    # callbacks
    # ------------------------------------------------------------------
    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        connect_flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: Properties | None,
    ) -> None:
        logger.info("[%s] connected: %s", self.client_id, reason_code)
        for topic in list(self._callbacks.keys()):
            self._client.subscribe(topic, qos=1)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        rc: mqtt.ReasonCode,
        properties: Properties | None,
    ) -> None:
        logger.warning("[%s] disconnected: rc=%s", self.client_id, rc)

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code_list: list[mqtt.ReasonCode],
        properties: Properties | None,
    ) -> None:
        with self._subscribe_lock:
            future = self._subscribe_futures.pop(mid, None)
            if future is not None and not future.done():
                # asyncio.Future.set_result is not thread-safe; use the loop's
                # thread-safe scheduler because this callback runs on paho's
                # network thread.
                future.get_loop().call_soon_threadsafe(future.set_result, None)
            else:
                self._suback_received.add(mid)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            logger.warning(
                "[%s] failed to decode JSON payload on %s",
                self.client_id,
                msg.topic,
                exc_info=True,
            )
            payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

        # Iterate over a snapshot so subscribe()/unsubscribe() from another
        # thread while we are iterating does not raise RuntimeError.
        for pattern, handler in list(self._callbacks.items()):
            if _topic_matches(pattern, msg.topic):
                handler(msg.topic, payload, msg.properties)
                return
        logger.debug("[%s] no handler for %s", self.client_id, msg.topic)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def connect(self, keepalive: int = 60, *, timeout: float = 5.0) -> None:
        self._client.connect(self.broker, self.port, keepalive)
        self._client.loop_start()
        # Wait until the connection is established so callers can publish
        # immediately after connect() returns.
        deadline = time.monotonic() + timeout
        while not self._client.is_connected() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not self._client.is_connected():
            raise RuntimeError(f"Failed to connect to MQTT broker at {self.broker}:{self.port}")

    def disconnect(self) -> None:
        # Initiate MQTT disconnect first so the broker can flush in-flight
        # messages, then stop the network loop.
        self._client.disconnect()
        deadline = time.monotonic() + 2.0
        while self._client.is_connected() and time.monotonic() < deadline:
            time.sleep(0.05)
        self._client.loop_stop()

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        qos: int = 1,
        retain: bool = False,
        properties: Properties | None = None,
    ) -> mqtt.MQTTMessageInfo:
        data = json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8")
        info = self._client.publish(topic, data, qos=qos, retain=retain, properties=properties)
        # Calling wait_for_publish from the paho network loop thread (e.g. inside
        # an on_message callback) can deadlock, because the same thread must
        # process the incoming PUBACK. Wait only when called from another thread.
        loop_thread = getattr(self._client, "_thread", None)
        if loop_thread is not None and threading.current_thread() is loop_thread:
            return info
        info.wait_for_publish(timeout=5.0)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"publish to {topic} failed: {mqtt.error_string(info.rc)}")
        if qos > 0 and not info.is_published():
            raise RuntimeError(f"publish to {topic} did not receive PUBACK in time")
        return info

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[str, dict[str, Any], Properties | None], None],
        *,
        qos: int = 1,
        timeout: float = 5.0,
    ) -> None:
        """Subscribe to a literal or wildcard topic and await SUBACK."""
        self._callbacks[topic] = callback
        if not self.is_connected():
            # If not connected, _on_connect will resubscribe registered callbacks.
            return

        result, mid = self._client.subscribe(topic, qos=qos)
        if result != mqtt.MQTT_ERR_SUCCESS or mid is None:
            raise RuntimeError(f"Failed to subscribe to {topic}: {mqtt.error_string(result)}")

        loop = asyncio.get_event_loop()
        with self._subscribe_lock:
            if mid in self._suback_received:
                self._suback_received.discard(mid)
                return
            future: asyncio.Future[None] = loop.create_future()
            self._subscribe_futures[mid] = future
        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("[%s] SUBACK timeout for %s", self.client_id, topic)
            with self._subscribe_lock:
                self._subscribe_futures.pop(mid, None)
            raise

    def is_connected(self) -> bool:
        return self._client.is_connected()
