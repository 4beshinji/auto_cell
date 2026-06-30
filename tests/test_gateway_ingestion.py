"""Tests for gateway telemetry ingestion and protocol adapters."""

from __future__ import annotations

import tempfile
from typing import Any

import pytest

from auto_cell.audit.event_store import EventWriter
from auto_cell.gateway import (
    FunctionType,
    LadsFunction,
    MeasurementValue,
    MockSiLA2Client,
    NovaFLEX2Client,
    NovaFlex2Result,
    OpcUaLadsClient,
    SiLAFeature,
    TelemetryIngestionService,
)
from auto_cell.gateway.lads_opcua_client import LadsReadResult, OpcUaLadsAdapter
from auto_cell.schemas.audit_events import EventType


class _FakeMqttClient:
    """Minimal MqttClient stand-in for offline ingestion tests."""

    def __init__(self) -> None:
        self._callbacks: dict[str, Any] = {}
        self._connected = True
        self._client = _FakePahoClient()

    def is_connected(self) -> bool:
        return self._connected

    def subscribe(
        self,
        topic: str,
        callback: Any,
        *,
        qos: int = 1,
    ) -> None:
        self._callbacks[topic] = callback


class _FakePahoClient:
    def subscribe(self, topic: str, qos: int = 1) -> None:
        pass


@pytest.fixture
def event_writer() -> EventWriter:
    tmp = tempfile.TemporaryDirectory()
    return EventWriter(tmp.name)


@pytest.fixture
def fake_mqtt() -> _FakeMqttClient:
    return _FakeMqttClient()


def _dispatch(
    mqtt: _FakeMqttClient,
    topic: str,
    payload: dict[str, Any],
) -> None:
    for pattern, handler in mqtt._callbacks.items():
        if _topic_matches(pattern, topic):
            handler(topic, payload, None)
            return


def _topic_matches(pattern: str, topic: str) -> bool:
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


def test_ingestion_service_writes_single_telemetry(
    fake_mqtt: _FakeMqttClient,
    event_writer: EventWriter,
) -> None:
    service = TelemetryIngestionService(
        mqtt_client=fake_mqtt,  # type: ignore[arg-type]
        event_writer=event_writer,
        culture_unit_id="cu_001",
        run_id="run_001",
    )
    service.start()

    _dispatch(
        fake_mqtt,
        "cell/cu_001/telemetry/bio_01/glucose",
        {
            "timestamp": "2026-06-30T07:00:00Z",
            "value": 4.5,
            "unit": "mM",
            "quality": "GOOD",
            "source": "bio_01",
        },
    )

    events = event_writer.load_run("run_001")
    assert len(events) == 1
    assert events[0].header.event_type == EventType.TELEMETRY
    assert events[0].payload["channel"] == "bio_01/glucose"
    assert events[0].payload["value"] == pytest.approx(4.5)


def test_ingestion_service_writes_all_telemetry(
    fake_mqtt: _FakeMqttClient,
    event_writer: EventWriter,
) -> None:
    service = TelemetryIngestionService(
        mqtt_client=fake_mqtt,  # type: ignore[arg-type]
        event_writer=event_writer,
        culture_unit_id="cu_001",
        run_id="run_002",
    )
    service.start()

    _dispatch(
        fake_mqtt,
        "cell/cu_001/telemetry/bio_01/all",
        {
            "timestamp": "2026-06-30T07:00:00Z",
            "device_id": "bio_01",
            "values": {
                "vcd": 1.2e6,
                "viability": 97.0,
                "glucose": 5.0,
            },
        },
    )

    events = event_writer.load_run("run_002")
    assert len(events) == 3
    channels = {e.payload["channel"] for e in events}
    assert channels == {"bio_01/vcd", "bio_01/viability", "bio_01/glucose"}


def test_ingestion_service_writes_bad_quality_event(
    fake_mqtt: _FakeMqttClient,
    event_writer: EventWriter,
) -> None:
    service = TelemetryIngestionService(
        mqtt_client=fake_mqtt,  # type: ignore[arg-type]
        event_writer=event_writer,
        culture_unit_id="cu_001",
        run_id="run_003",
    )
    service.start()

    _dispatch(
        fake_mqtt,
        "cell/cu_001/telemetry/bio_01/do_percent",
        {
            "timestamp": "2026-06-30T07:00:00Z",
            "value": 0.0,
            "unit": "percent",
            "quality": "BAD",
            "source": "bio_01",
        },
    )

    events = event_writer.load_run("run_003")
    types = [e.header.event_type for e in events]
    assert EventType.TELEMETRY in types
    assert EventType.EVENT in types


def test_nova_flex2_result_parsing_and_mqtt_publish(
    fake_mqtt: _FakeMqttClient,
) -> None:
    published: list[tuple[str, dict[str, Any]]] = []

    def capture_publish(topic: str, payload: dict[str, Any], **kwargs: Any) -> None:
        published.append((topic, payload))

    fake_mqtt.publish = capture_publish  # type: ignore[method-assign]

    client = NovaFLEX2Client(
        culture_unit_id="cu_001",
        device_id="nova_01",
        mqtt_client=fake_mqtt,  # type: ignore[arg-type]
    )
    result = NovaFlex2Result(
        sample_id="S01",
        device_id="nova_01",
        measurements={
            "glucose": MeasurementValue(value=5.0, unit="mM"),
            "lactate": MeasurementValue(value=8.0, unit="mM"),
        },
    )
    client.publish_to_mqtt(result)

    assert len(published) == 2
    topics = [t for t, _ in published]
    assert "cell/cu_001/telemetry/nova_01/glucose" in topics
    assert "cell/cu_001/telemetry/nova_01/lactate" in topics


@pytest.mark.asyncio
async def test_opcua_lads_read_value() -> None:
    functions = [
        LadsFunction(
            function_id="Temperature",
            display_name="Temperature",
            function_type=FunctionType.SENSOR,
            node_id="ns=2;i=1234",
            unit="degC",
        )
    ]
    client = OpcUaLadsClient("unit_01", functions, "opc.tcp://localhost:4840")

    # Mock asyncua client internals so no real server is needed.
    class FakeNode:
        async def read_value(self) -> float:
            return 37.0

    class FakeAsyncuaClient:
        def __init__(self, url: str) -> None:
            self.url = url

        async def connect(self) -> None:
            pass

        async def disconnect(self) -> None:
            pass

        def get_node(self, node_id: str) -> FakeNode:
            return FakeNode()

    client._client = FakeAsyncuaClient("opc.tcp://localhost:4840")
    result = await client.read("Temperature")

    assert result.function_id == "Temperature"
    assert result.value == pytest.approx(37.0)
    assert result.unit == "degC"


@pytest.mark.asyncio
async def test_mock_sila2_client_command_and_observation() -> None:
    feature = SiLAFeature(
        feature_id="AggregateImaging",
        display_name="Aggregate Imaging",
    )
    client = MockSiLA2Client("grpc://localhost:50051", [feature])
    await client.connect()

    client.set_stub_response("AggregateImaging", "TakeImage", {"image_id": "img_01"})
    response = await client.call_command("AggregateImaging", "TakeImage", {})
    assert response["result"]["image_id"] == "img_01"

    observed: list[Any] = []
    client.set_stub_stream(
        "AggregateImaging", "MeanDiameter", [150.0, 155.0, 160.0]
    )
    await client.subscribe_property(
        "AggregateImaging", "MeanDiameter", observed.append
    )
    assert observed == [150.0, 155.0, 160.0]


def test_opcua_lads_adapter_publish(fake_mqtt: _FakeMqttClient) -> None:
    published: list[tuple[str, dict[str, Any]]] = []

    def capture_publish(topic: str, payload: dict[str, Any], **kwargs: Any) -> None:
        published.append((topic, payload))

    fake_mqtt.publish = capture_publish  # type: ignore[method-assign]

    functions = [
        LadsFunction(
            function_id="pH",
            display_name="pH",
            function_type=FunctionType.SENSOR,
            node_id="ns=2;i=1",
            unit="pH",
        )
    ]
    lads = OpcUaLadsClient("bio_01", functions, "opc.tcp://localhost:4840")
    adapter = OpcUaLadsAdapter(
        lads, culture_unit_id="cu_001", mqtt_client=fake_mqtt  # type: ignore[arg-type]
    )

    class FakeNode:
        async def read_value(self) -> float:
            return 7.1

    class FakeAsyncuaClient:
        async def connect(self) -> None:
            pass

        async def disconnect(self) -> None:
            pass

        def get_node(self, node_id: str) -> FakeNode:
            return FakeNode()

    lads._client = FakeAsyncuaClient()
    adapter._publish(
        LadsReadResult(
            function_id=lads.functions["pH"].function_id,
            value=7.1,
            unit="pH",
            timestamp="2026-06-30T07:00:00Z",
        )
    )

    assert len(published) == 1
    assert published[0][0] == "cell/cu_001/telemetry/bio_01/pH"
    assert published[0][1]["value"] == pytest.approx(7.1)
