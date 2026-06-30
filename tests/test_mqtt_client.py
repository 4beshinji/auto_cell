"""Tests for the paho-mqtt v2 client."""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("paho.mqtt.client", reason="paho-mqtt not installed")

from auto_cell.gateway.mqtt_client import MqttClient


def test_mocked_message_dispatch():
    """Verify on_message dispatches to the registered callback without a broker."""
    received = {}

    def handler(topic, payload, properties):
        received["topic"] = topic
        received["payload"] = payload

    client = MqttClient("mock_client", "localhost", 1883)
    client._callbacks["test/topic"] = handler

    class FakeMsg:
        topic = "test/topic"
        payload = b'{"hello": "world"}'
        properties = None

    client._on_message(None, None, FakeMsg())
    assert received["topic"] == "test/topic"
    assert received["payload"] == {"hello": "world"}


@pytest.mark.usefixtures("mqtt_broker")
@pytest.mark.asyncio
async def test_client_connect_publish_subscribe(broker_host):
    received = {}

    def handler(topic, payload, properties):
        received["topic"] = topic
        received["payload"] = payload

    client = MqttClient("test_pubsub", broker_host, 1883)
    client.connect()
    await client.subscribe("test/+/foo", handler, qos=1)
    await asyncio.sleep(0.2)
    client.publish("test/bar/foo", {"value": 42}, qos=1)
    await asyncio.sleep(0.3)
    client.disconnect()

    assert received.get("topic") == "test/bar/foo"
    assert received.get("payload") == {"value": 42}
