"""Tests for MQTT request-id idempotency."""

from __future__ import annotations

import asyncio

import pytest

from auto_cell.gateway.idempotency import IdempotencyStore


def test_duplicate_request_returns_replayed():
    store = IdempotencyStore(ttl_seconds=60)
    store.save("req_001", "accepted", {"vvd": 2.0})
    assert store.is_known("req_001")
    cached = store.get("req_001")
    assert cached is not None
    assert cached.status == "accepted"
    assert cached.result == {"vvd": 2.0}


def test_expired_request_is_unknown():
    store = IdempotencyStore(ttl_seconds=-1)
    store.save("req_002", "accepted", {})
    assert not store.is_known("req_002")


def test_cleanup_removes_expired():
    store = IdempotencyStore(ttl_seconds=60)
    store.save("req_003", "accepted", {})
    store._records["req_003"].expires_at = 0.0
    store.cleanup()
    assert "req_003" not in store._records


@pytest.mark.usefixtures("mqtt_broker")
@pytest.mark.asyncio
async def test_duplicate_command_to_virtual_edge(mqtt_broker, broker_host):
    from auto_cell.gateway.request_response import RequestResponseClient
    from infra.virtual_edge.dummy_bioreactor import DummyBioreactorEdge

    edge = DummyBioreactorEdge(
        "cu_test",
        device_id="bio_test",
        broker=broker_host,
        port=1883,
        cycle_interval_s=3600,
    )
    await edge.start()

    brain = RequestResponseClient("brain_test", broker_host, 1883)
    brain.connect()
    await asyncio.sleep(0.3)

    try:
        req_id = "req_duplicate_001"
        ack1 = await brain.request(
            "cu_test",
            "bio_test",
            "set_perfusion_rate",
            {"vvd": 2.0},
            request_id=req_id,
            timeout=5.0,
        )
        assert ack1.status == "accepted"

        ack2 = await brain.request(
            "cu_test",
            "bio_test",
            "set_perfusion_rate",
            {"vvd": 999.0},
            request_id=req_id,
            timeout=5.0,
        )
        assert ack2.status == "replayed"
        assert ack2.result["actuators"]["perfusion_rate_vvd"] == 2.0
    finally:
        edge.disconnect()
        brain.disconnect()
