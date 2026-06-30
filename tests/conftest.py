"""Shared fixtures including optional MQTT broker detection."""

from __future__ import annotations

import socket

import pytest


LOCAL_BROKER_HOST = "127.0.0.1"
LOCAL_BROKER_PORT = 1883


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def broker_available():
    return _port_open(LOCAL_BROKER_HOST, LOCAL_BROKER_PORT)


@pytest.fixture(scope="session")
def mqtt_broker(broker_available):
    """Requires a running MQTT broker on 127.0.0.1:1883.

    The embedded ``amqtt`` broker does not support MQTT 5.0, so tests using
    this fixture are skipped unless an external broker (e.g. Mosquitto) is
    already listening.
    """
    if not broker_available:
        pytest.skip("No MQTT broker on 127.0.0.1:1883 (MQTT 5.0 required)")
    return None


@pytest.fixture
def broker_host():
    return LOCAL_BROKER_HOST
