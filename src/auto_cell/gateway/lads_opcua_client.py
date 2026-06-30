"""LADS Functional Unit / Function abstraction + OPC-UA client/adapter."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from auto_cell.gateway.correlation import now_iso
from auto_cell.gateway.mqtt_client import MqttClient

logger = logging.getLogger(__name__)


class FunctionType(str, Enum):
    SENSOR = "sensor"
    CONTROLLER = "controller"
    ACTUATOR = "actuator"
    PROGRAM = "program"


@dataclass(frozen=True)
class LadsFunction:
    function_id: str
    display_name: str
    function_type: FunctionType
    node_id: str
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None


@dataclass(frozen=True)
class LadsReadResult:
    function_id: str
    value: Any
    unit: str | None
    timestamp: str


class LadsFunctionalUnit(ABC):
    """LADS Functional Unit (one vessel) abstraction."""

    def __init__(self, unit_id: str, functions: list[LadsFunction]) -> None:
        self.unit_id = unit_id
        self.functions: dict[str, LadsFunction] = {f.function_id: f for f in functions}

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def subscribe(
        self,
        function_id: str,
        callback: Callable[[str, Any], None],
    ) -> None:
        ...

    @abstractmethod
    async def call_method(
        self,
        function_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def read(self, function_id: str) -> Any:
        ...


class OpcUaLadsClient(LadsFunctionalUnit):
    """asyncua-based LADS/OPC-UA client with read support and polling adapter."""

    def __init__(
        self,
        unit_id: str,
        functions: list[LadsFunction],
        opcua_url: str,
        namespace_index: int = 2,
    ) -> None:
        super().__init__(unit_id, functions)
        self.opcua_url = opcua_url
        self.namespace_index = namespace_index
        self._client: Any = None

    async def connect(self) -> None:
        try:
            from asyncua import Client  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("asyncua is required for OPC-UA connectivity") from exc
        self._client = Client(self.opcua_url)
        await self._client.connect()

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()

    async def subscribe(
        self,
        function_id: str,
        callback: Callable[[str, Any], None],
    ) -> None:
        """OPC-UA subscriptions are not implemented; use polling instead."""
        raise NotImplementedError(
            "OPC-UA datachange subscriptions are Phase 2; "
            "use OpcUaLadsAdapter.start_polling()"
        )

    async def call_method(
        self,
        function_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError("OPC-UA call_method is Phase 2")

    async def read(self, function_id: str) -> LadsReadResult:
        """Read the current value of a LADS Function from the OPC-UA server."""
        if self._client is None:
            raise RuntimeError("OPC-UA client is not connected")
        function = self.functions.get(function_id)
        if function is None:
            raise KeyError(f"unknown function: {function_id}")

        node = self._client.get_node(function.node_id)
        value = await node.read_value()
        return LadsReadResult(
            function_id=function_id,
            value=value,
            unit=function.unit,
            timestamp=now_iso(),
        )


class OpcUaLadsAdapter:
    """Bridge between ``OpcUaLadsClient`` and the MQTT/event_store ingestion path."""

    def __init__(
        self,
        client: LadsFunctionalUnit,
        culture_unit_id: str,
        mqtt_client: MqttClient | None = None,
    ) -> None:
        self.client = client
        self.culture_unit_id = culture_unit_id
        self.mqtt = mqtt_client
        self._running = False

    async def start_polling(
        self,
        function_ids: list[str],
        interval_s: float = 30.0,
    ) -> None:
        """Poll sensor functions and publish each reading as MQTT telemetry."""
        self._running = True
        while self._running:
            for function_id in function_ids:
                try:
                    result = await self.client.read(function_id)
                    self._publish(result)
                except Exception:
                    logger.exception("failed to read %s", function_id)
            await asyncio.sleep(interval_s)

    def stop(self) -> None:
        self._running = False

    def _publish(self, result: LadsReadResult) -> None:
        if self.mqtt is None:
            return
        topic = (
            f"cell/{self.culture_unit_id}/telemetry/"
            f"{self.client.unit_id}/{result.function_id}"
        )
        payload = {
            "timestamp": result.timestamp,
            "value": result.value,
            "unit": result.unit,
            "quality": "good",
            "source": self.client.unit_id,
        }
        self.mqtt.publish(topic, payload, qos=1, retain=True)
