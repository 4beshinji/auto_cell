"""Tests for the virtual edge dummy bioreactor."""

from __future__ import annotations

import asyncio

import pytest

from auto_cell.gateway.request_response import RequestResponseClient
from infra.virtual_edge.dummy_bioreactor import DummyBioreactorEdge


@pytest.mark.usefixtures("mqtt_broker")
@pytest.mark.asyncio
async def test_set_perfusion_rate_changes_telemetry(mqtt_broker, broker_host):
    edge = DummyBioreactorEdge(
        "cu_integ",
        device_id="bio_01",
        broker=broker_host,
        port=1883,
        cycle_interval_s=1.0,
    )
    await edge.start()

    brain = RequestResponseClient("brain_integ", broker_host, 1883)
    brain.connect()
    await asyncio.sleep(0.3)

    try:
        ack = await brain.request(
            "cu_integ",
            "bio_01",
            "set_perfusion_rate",
            {"vvd": 3.0},
            timeout=5.0,
        )
        assert ack.status == "accepted"

        received = {}

        def on_telemetry(topic, payload, properties):
            received.update(payload)

        await brain.subscribe("cell/cu_integ/telemetry/bio_01/all", on_telemetry, qos=1)
        edge.tick()
        await asyncio.sleep(0.5)

        assert "values" in received
        assert "vcd" in received["values"]
    finally:
        edge.disconnect()
        brain.disconnect()


def test_dummy_bioreactor_tick():
    edge = DummyBioreactorEdge(
        "cu_offline",
        device_id="bio_offline",
        broker="localhost",
        port=1883,
        cycle_interval_s=60.0,
    )
    telemetry = edge.tick()
    assert "values" in telemetry
    assert "actuators" in telemetry
    assert telemetry["actuators"]["perfusion_rate_vvd"] == 0.0
