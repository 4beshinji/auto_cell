"""Tests for channel routing."""

from auto_cell.plugins.cell_culture.channels import route_channel, channel_config


def test_route_channel():
    update = route_channel("do", {"value": 41.2, "timestamp": "2026-06-30T07:00:00Z"})
    assert update == {"do_pct": 41.2}


def test_route_channel_raw_value():
    update = route_channel("ph", 7.15)
    assert update == {"ph": 7.15}


def test_route_channel_unknown():
    assert route_channel("unknown", 1.0) is None


def test_channel_config_count():
    assert len(channel_config()) >= 10
