"""Tests for tool invocation."""

from auto_cell.plugins.cell_culture.tools import invoke_tool, tool_schemas


def test_invoke_set_perfusion_rate():
    result = invoke_tool("set_perfusion_rate", {"vvd": 3.5})
    assert result.status == "accepted"
    assert result.requested_actuators["perfusion_rate_vvd"] == 3.5


def test_invoke_unknown_tool():
    result = invoke_tool("unknown_tool", {})
    assert result.status == "rejected"


def test_tool_schemas_cover_expected_tools():
    schemas = tool_schemas()
    assert "set_perfusion_rate" in schemas
    assert "trigger_passage" in schemas
