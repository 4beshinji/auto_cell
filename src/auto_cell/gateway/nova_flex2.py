"""Nova FLEX2 at-line analyzer adapter.

Nova FLEX2 measures glucose, lactate, glutamine, osmolality, viability, etc.
from a drawn sample. This module provides a skeleton that can either poll a
REST/HTTP endpoint or publish results over MQTT so that
``TelemetryIngestionService`` stores them in the event store.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from auto_cell.gateway.correlation import now_iso
from auto_cell.gateway.mqtt_client import MqttClient

logger = logging.getLogger(__name__)


class MeasurementValue(BaseModel):
    value: float | int | str | None
    unit: str | None = None
    quality: str = "good"


class NovaFlex2Result(BaseModel):
    """One at-line Nova FLEX2 sample report."""

    sample_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    device_id: str = "nova_flex2_01"
    timestamp: str = Field(default_factory=now_iso)
    measurements: dict[str, MeasurementValue] = Field(default_factory=dict)

    def to_mqtt_payloads(self) -> list[dict[str, Any]]:
        """Return single-value telemetry payloads for MQTT publishing."""
        payloads: list[dict[str, Any]] = []
        for analyte, mv in self.measurements.items():
            payloads.append(
                {
                    "timestamp": self.timestamp,
                    "value": mv.value,
                    "unit": mv.unit,
                    "quality": mv.quality,
                    "source": self.device_id,
                    "sample_id": self.sample_id,
                }
            )
        return payloads


class NovaFLEX2Client:
    """At-line Nova FLEX2 client with HTTP polling and MQTT publishing modes."""

    # Default analytes for iPSC perfusion media characterization.
    DEFAULT_ANALYTES = (
        "glucose",
        "lactate",
        "glutamine",
        "osmolality",
        "viability",
    )

    def __init__(
        self,
        culture_unit_id: str,
        device_id: str = "nova_flex2_01",
        *,
        base_url: str | None = None,
        mqtt_client: MqttClient | None = None,
        poll_interval_s: float = 300.0,
        analytes: tuple[str, ...] | None = None,
    ) -> None:
        self.culture_unit_id = culture_unit_id
        self.device_id = device_id
        self.base_url = base_url
        self.mqtt = mqtt_client
        self.poll_interval_s = poll_interval_s
        self.analytes = analytes or self.DEFAULT_ANALYTES
        self._running = False

    async def connect(self) -> None:
        """Validate configuration. Real HTTP session creation is deferred."""
        if self.base_url is None and self.mqtt is None:
            raise RuntimeError(
                "NovaFLEX2Client requires either base_url or mqtt_client"
            )
        logger.info("[%s] Nova FLEX2 adapter ready", self.device_id)

    async def disconnect(self) -> None:
        self._running = False

    async def read_sample(self, sample_id: str | None = None) -> NovaFlex2Result:
        """Fetch or synthesize one sample result.

        When ``base_url`` is set, this performs an HTTP GET to
        ``{base_url}/samples/latest``. Otherwise it returns a synthetic result
        populated with placeholder values for testing.
        """
        if self.base_url is not None:
            return await self._http_read_sample(sample_id)
        return self._synthetic_result(sample_id)

    async def _http_read_sample(self, sample_id: str | None = None) -> NovaFlex2Result:
        # Delayed import so the adapter is importable without httpx installed.
        import httpx

        if self.base_url is None:
            raise RuntimeError("base_url is not configured")
        url = f"{self.base_url.rstrip('/')}/samples/latest"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        measurements: dict[str, MeasurementValue] = {}
        for analyte in self.analytes:
            raw = data.get(analyte)
            if raw is None:
                continue
            if isinstance(raw, dict):
                measurements[analyte] = MeasurementValue(**raw)
            else:
                measurements[analyte] = MeasurementValue(value=raw)

        return NovaFlex2Result(
            sample_id=sample_id or data.get("sample_id", str(uuid.uuid4())[:8]),
            device_id=self.device_id,
            timestamp=data.get("timestamp", now_iso()),
            measurements=measurements,
        )

    def _synthetic_result(self, sample_id: str | None = None) -> NovaFlex2Result:
        """Generate a deterministic placeholder result for offline tests."""
        return NovaFlex2Result(
            sample_id=sample_id or str(uuid.uuid4())[:8],
            device_id=self.device_id,
            timestamp=now_iso(),
            measurements={
                "glucose": MeasurementValue(value=5.0, unit="mM"),
                "lactate": MeasurementValue(value=8.0, unit="mM"),
                "glutamine": MeasurementValue(value=1.5, unit="mM"),
                "osmolality": MeasurementValue(value=320.0, unit="mOsm/kg"),
                "viability": MeasurementValue(value=97.0, unit="percent"),
            },
        )

    def publish_to_mqtt(self, result: NovaFlex2Result) -> None:
        """Publish a sample's measurements as single-value telemetry topics."""
        if self.mqtt is None:
            raise RuntimeError("mqtt_client is not configured")
        payloads = result.to_mqtt_payloads()
        for analyte, payload in zip(result.measurements.keys(), payloads):
            topic = (
                f"cell/{self.culture_unit_id}/telemetry/{self.device_id}/{analyte}"
            )
            self.mqtt.publish(topic, payload, qos=1, retain=True)

    async def poll_loop(
        self,
        callback: Callable[[NovaFlex2Result], None] | None = None,
    ) -> None:
        """Periodically read samples and optionally publish to MQTT."""
        self._running = True
        while self._running:
            result = await self.read_sample()
            if callback is not None:
                callback(result)
            elif self.mqtt is not None:
                self.publish_to_mqtt(result)
            await asyncio.sleep(self.poll_interval_s)
