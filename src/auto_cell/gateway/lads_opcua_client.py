"""LADS Functional Unit / Function abstraction + OPC-UA skeleton."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable
from typing import Any


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
    """asyncua-based LADS/OPC-UA skeleton. Phase 1: interface only."""

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
        raise NotImplementedError("OPC-UA subscribe is Phase 2")

    async def call_method(
        self,
        function_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError("OPC-UA call_method is Phase 2")

    async def read(self, function_id: str) -> Any:
        raise NotImplementedError("OPC-UA read is Phase 2")
