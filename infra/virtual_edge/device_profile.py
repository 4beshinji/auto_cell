"""Channel/tool to LADS/SiLA2 device profile stub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeviceMapping:
    device_id: str
    function_id: str
    transport: str  # mqtt, opcua, sila2


_CHANNEL_TO_DEVICE: dict[str, DeviceMapping] = {
    "vcd": DeviceMapping("bioreactor_01", "BioProcessSensor_VCD", "mqtt"),
    "viability": DeviceMapping("bioreactor_01", "BioProcessSensor_Viability", "mqtt"),
    "glucose": DeviceMapping("bioreactor_01", "BioProcessSensor_Glucose", "mqtt"),
    "lactate": DeviceMapping("bioreactor_01", "BioProcessSensor_Lactate", "mqtt"),
    "glutamine": DeviceMapping("bioreactor_01", "BioProcessSensor_Glutamine", "mqtt"),
    "ph": DeviceMapping("bioreactor_01", "BioProcessSensor_pH", "mqtt"),
    "do": DeviceMapping("bioreactor_01", "BioProcessSensor_DO", "mqtt"),
    "temp": DeviceMapping("bioreactor_01", "BioProcessSensor_Temperature", "mqtt"),
    "osmolality": DeviceMapping("bioreactor_01", "BioProcessSensor_Osmolality", "mqtt"),
    "agitation": DeviceMapping("bioreactor_01", "AgitationController_ActualSpeed", "mqtt"),
    "perfusion_rate": DeviceMapping("bioreactor_01", "PerfusionController_ActualRate", "mqtt"),
    "aggregate_diameter": DeviceMapping("aggregate_analyzer_01", "AggregateAnalyzer_MeanDiameter", "sila2"),
    "large_aggregate_ratio": DeviceMapping("aggregate_analyzer_01", "AggregateAnalyzer_LargeFraction", "sila2"),
    "sterility": DeviceMapping("bioreactor_01", "SterilityMonitor_Contamination", "mqtt"),
}


_TOOL_TO_DEVICE: dict[str, DeviceMapping] = {
    "set_perfusion_rate": DeviceMapping("bioreactor_01", "PerfusionController_SetRate", "mqtt"),
    "set_agitation_rpm": DeviceMapping("bioreactor_01", "AgitationController_SetSpeed", "mqtt"),
    "set_gas_setpoint": DeviceMapping("bioreactor_01", "GasController_SetSetpoint", "mqtt"),
    "feed": DeviceMapping("dispense_01", "FeedPump_Dispense", "mqtt"),
    "exchange_media": DeviceMapping("dispense_01", "MediaExchange_Exchange", "mqtt"),
    "trigger_passage": DeviceMapping("bioreactor_01", "PassageMethod_Execute", "mqtt"),
    "take_sample": DeviceMapping("sampler_01", "TakeSample_Execute", "sila2"),
}


def map_channel(channel_id: str) -> DeviceMapping | None:
    return _CHANNEL_TO_DEVICE.get(channel_id)


def map_tool(tool_name: str) -> DeviceMapping | None:
    return _TOOL_TO_DEVICE.get(tool_name)


def device_profile() -> dict[str, Any]:
    return {
        "channels": {k: v.__dict__ for k, v in _CHANNEL_TO_DEVICE.items()},
        "tools": {k: v.__dict__ for k, v in _TOOL_TO_DEVICE.items()},
    }
