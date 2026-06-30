"""SiLA2 Feature abstraction + mock/test client and adapter."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from auto_cell.gateway.correlation import now_iso
from auto_cell.gateway.mqtt_client import MqttClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SiLAMethod:
    name: str
    parameter_schema: dict[str, Any]
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class SiLAFeature:
    feature_id: str
    display_name: str
    commands: dict[str, SiLAMethod] = field(default_factory=dict)
    properties: dict[str, SiLAMethod] = field(default_factory=dict)
    observations: dict[str, SiLAMethod] = field(default_factory=dict)


class SiLA2Client(ABC):
    """SiLA2 peripheral client abstraction."""

    def __init__(self, server_uri: str, features: list[SiLAFeature]) -> None:
        self.server_uri = server_uri
        self.features: dict[str, SiLAFeature] = {f.feature_id: f for f in features}

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def call_command(
        self,
        feature_id: str,
        command_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def subscribe_property(
        self,
        feature_id: str,
        property_id: str,
        callback: Callable[[Any], None],
    ) -> None:
        ...

    @abstractmethod
    async def observe_event(
        self,
        feature_id: str,
        event_id: str,
        callback: Callable[[Any], None],
    ) -> None:
        ...


class MockSiLA2Client(SiLA2Client):
    """In-memory SiLA2 mock for offline tests and CI."""

    def __init__(self, server_uri: str, features: list[SiLAFeature]) -> None:
        super().__init__(server_uri, features)
        self._command_stubs: dict[tuple[str, str], dict[str, Any]] = {}
        self._property_streams: dict[tuple[str, str], list[Any]] = {}
        self._event_streams: dict[tuple[str, str], list[Any]] = {}
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def set_stub_response(
        self, feature_id: str, command_id: str, response: dict[str, Any]
    ) -> None:
        self._command_stubs[(feature_id, command_id)] = response

    def set_stub_stream(
        self,
        feature_id: str,
        property_id: str,
        values: list[Any],
        *,
        is_event: bool = False,
    ) -> None:
        if is_event:
            self._event_streams[(feature_id, property_id)] = list(values)
        else:
            self._property_streams[(feature_id, property_id)] = list(values)

    async def call_command(
        self,
        feature_id: str,
        command_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        key = (feature_id, command_id)
        if key not in self._command_stubs:
            raise RuntimeError(f"no stub for {feature_id}/{command_id}")
        return {"status": "completed", "result": self._command_stubs[key]}

    async def subscribe_property(
        self,
        feature_id: str,
        property_id: str,
        callback: Callable[[Any], None],
    ) -> None:
        values = self._property_streams.get((feature_id, property_id), [])
        for value in values:
            callback(value)
            await asyncio.sleep(0)

    async def observe_event(
        self,
        feature_id: str,
        event_id: str,
        callback: Callable[[Any], None],
    ) -> None:
        values = self._event_streams.get((feature_id, event_id), [])
        for value in values:
            callback(value)
            await asyncio.sleep(0)


class SiLA2Adapter:
    """Bridge a SiLA2 client to MQTT telemetry / event_store ingestion."""

    def __init__(
        self,
        client: SiLA2Client,
        culture_unit_id: str,
        device_id: str,
        mqtt_client: MqttClient | None = None,
    ) -> None:
        self.client = client
        self.culture_unit_id = culture_unit_id
        self.device_id = device_id
        self.mqtt = mqtt_client
        self._running = False

    async def start_observations(
        self,
        property_observables: list[tuple[str, str]] | None = None,
        event_observables: list[tuple[str, str]] | None = None,
        interval_s: float = 30.0,
    ) -> None:
        """Start polling properties and observing events, publishing each as telemetry."""
        self._running = True
        property_observables = property_observables or []
        event_observables = event_observables or []

        while self._running:
            for feature_id, property_id in property_observables:
                try:
                    await self.client.subscribe_property(
                        feature_id, property_id, self._make_callback(property_id)
                    )
                except Exception:
                    logger.exception("SiLA2 property subscription failed")
            for feature_id, event_id in event_observables:
                try:
                    await self.client.observe_event(
                        feature_id, event_id, self._make_callback(event_id)
                    )
                except Exception:
                    logger.exception("SiLA2 event observation failed")
            await asyncio.sleep(interval_s)

    def stop(self) -> None:
        self._running = False

    def _make_callback(self, observable_id: str) -> Callable[[Any], None]:
        def callback(value: Any) -> None:
            self._publish(observable_id, value)

        return callback

    def _publish(self, observable_id: str, value: Any) -> None:
        if self.mqtt is None:
            return
        topic = (
            f"cell/{self.culture_unit_id}/telemetry/"
            f"{self.device_id}/{observable_id}"
        )
        payload = {
            "timestamp": now_iso(),
            "value": value,
            "quality": "good",
            "source": self.device_id,
        }
        self.mqtt.publish(topic, payload, qos=1, retain=True)
