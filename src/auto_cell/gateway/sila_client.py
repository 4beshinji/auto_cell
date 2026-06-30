"""SiLA2 Feature abstraction + client skeleton."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any


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
    """SiLA2 peripheral client abstraction. Phase 1: interface only."""

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
