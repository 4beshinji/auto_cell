"""Ingest MQTT telemetry into the event store.

``TelemetryIngestionService`` subscribes to the ``cell/{cu}/telemetry/...`` topic
tree, parses single-value and all-value payloads, and writes each measurement as
an ALCOA-lite ``EventType.TELEMETRY`` row via ``EventWriter``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal, cast

from auto_cell.audit.event_store import EventWriter
from auto_cell.gateway.mqtt_client import MqttClient
from auto_cell.schemas.audit_events import EventType, TelemetryPayload

logger = logging.getLogger(__name__)


class TelemetryIngestionService:
    """Subscribe to MQTT telemetry and persist every measurement to event_store."""

    def __init__(
        self,
        mqtt_client: MqttClient,
        event_writer: EventWriter,
        culture_unit_id: str,
        run_id: str | Callable[[], str],
        *,
        write_bad_quality_events: bool = True,
    ) -> None:
        self.mqtt = mqtt_client
        self.event_writer = event_writer
        self.culture_unit_id = culture_unit_id
        self.run_id = run_id
        self.write_bad_quality_events = write_bad_quality_events
        self._subscribed_topics: set[str] = set()

    def _resolve_run_id(self) -> str:
        if callable(self.run_id):
            return self.run_id()
        return self.run_id

    def start(self) -> None:
        """Subscribe to telemetry topics if the MQTT client is connected."""
        single = f"cell/{self.culture_unit_id}/telemetry/+/+"
        all_values = f"cell/{self.culture_unit_id}/telemetry/+/all"
        for topic in (single, all_values):
            self._subscribed_topics.add(topic)
            # Register the callback so the client can dispatch incoming messages.
            self.mqtt._callbacks[topic] = self._on_telemetry
            if self.mqtt.is_connected():
                # MqttClient.subscribe is async; for sync bootstrapping we call the
                # synchronous paho subscribe through the underlying client.
                self.mqtt._client.subscribe(topic, qos=1)
        logger.info(
            "[%s] telemetry ingestion started for run %s",
            self.culture_unit_id,
            self._resolve_run_id(),
        )

    def _on_telemetry(
        self,
        topic: str,
        payload: dict[str, Any],
        properties: Any,
    ) -> None:
        """Dispatch incoming MQTT telemetry to the appropriate parser."""
        parts = topic.split("/")
        if len(parts) != 5:
            logger.warning("unexpected telemetry topic: %s", topic)
            return

        device_id = parts[3]
        function_id = parts[4]

        if function_id == "all":
            readings = self._parse_all_telemetry(device_id, payload)
        else:
            single = self._parse_single_telemetry(device_id, function_id, payload)
            readings = [single] if single is not None else []

        for reading in readings:
            self._write_telemetry(reading)

    def _parse_single_telemetry(
        self,
        device_id: str,
        function_id: str,
        payload: dict[str, Any],
    ) -> TelemetryPayload | None:
        """Parse a single-value telemetry payload."""
        value = payload.get("value")
        if value is None:
            logger.debug("single telemetry without 'value': %s", payload)
            return None
        return TelemetryPayload(
            channel=f"{device_id}/{function_id}",
            value=value,
            unit=payload.get("unit"),
            quality=cast(Literal["good", "suspect", "bad"], self._normalize_quality(payload.get("quality"))),
        )

    def _parse_all_telemetry(
        self,
        device_id: str,
        payload: dict[str, Any],
    ) -> list[TelemetryPayload]:
        """Parse a telemetry/all payload into one row per channel."""
        values = payload.get("values", {})
        if not isinstance(values, dict):
            logger.warning("telemetry/all 'values' is not a dict: %s", payload)
            return []

        readings: list[TelemetryPayload] = []
        for function_id, value in values.items():
            # Skip nested structures; we only scalarize primitive values.
            if not isinstance(value, (int, float, str, bool, type(None))):
                continue
            readings.append(
                TelemetryPayload(
                    channel=f"{device_id}/{function_id}",
                    value=value,
                    unit=self._guess_unit(function_id),
                    quality="good",
                )
            )
        return readings

    def _write_telemetry(self, reading: TelemetryPayload) -> None:
        event_payload = {
            "channel": reading.channel,
            "value": reading.value,
            "unit": reading.unit,
            "quality": reading.quality,
        }
        self.event_writer.write(
            run_id=self._resolve_run_id(),
            event_type=EventType.TELEMETRY,
            payload=event_payload,
            source=f"gateway/{reading.channel}",
            actor="gateway.ingestion",
        )

        if self.write_bad_quality_events and reading.quality == "bad":
            self.event_writer.write(
                run_id=self._resolve_run_id(),
                event_type=EventType.EVENT,
                payload={
                    "severity": "P1",
                    "message": f"bad quality telemetry on {reading.channel}",
                    "channel": reading.channel,
                    "value": reading.value,
                },
                source=f"gateway/{reading.channel}",
                actor="gateway.ingestion",
            )

    @staticmethod
    def _normalize_quality(value: Any) -> str:
        if value is None:
            return "good"
        quality = str(value).lower()
        if quality in {"good", "suspect", "bad"}:
            return quality
        if quality in {"uncertain", "questionable"}:
            return "suspect"
        return "good"

    @staticmethod
    def _guess_unit(function_id: str) -> str | None:
        unit_map = {
            "vcd": "cells/mL",
            "viability": "percent",
            "glucose": "mM",
            "lactate": "mM",
            "glutamine": "mM",
            "osmolality": "mOsm/kg",
            "aggregate_diameter_um": "um",
            "do_percent": "percent",
            "ph": "pH",
            "temp_c": "degC",
            "perfusion_rate_vvd": "vvd",
            "agitation_rpm": "rpm",
        }
        return unit_map.get(function_id)
