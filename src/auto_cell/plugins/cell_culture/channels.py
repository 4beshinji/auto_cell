"""Channel configuration and routing for cell_culture telemetry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChannelConfig(BaseModel):
    channel_id: str
    env_field: str
    lads_function: str | None = None
    unit: str
    kind: str = Field(..., pattern="^(analog|discrete|image|computed)$")
    cadence_s: float | None = None
    deadband: float | None = None


CHANNELS: list[ChannelConfig] = [
    ChannelConfig(channel_id="vcd", env_field="vcd", lads_function="BioProcessSensor_VCD", unit="cells/mL", kind="analog", cadence_s=30.0),
    ChannelConfig(channel_id="viability", env_field="viability_pct", lads_function="BioProcessSensor_Viability", unit="%", kind="analog", cadence_s=30.0),
    ChannelConfig(channel_id="glucose", env_field="glucose_mM", lads_function="BioProcessSensor_Glucose", unit="mM", kind="analog", cadence_s=30.0),
    ChannelConfig(channel_id="lactate", env_field="lactate_mM", lads_function="BioProcessSensor_Lactate", unit="mM", kind="analog", cadence_s=30.0),
    ChannelConfig(channel_id="glutamine", env_field="glutamine_mM", lads_function="BioProcessSensor_Glutamine", unit="mM", kind="analog", cadence_s=30.0),
    ChannelConfig(channel_id="ammonia", env_field="ammonia_mM", lads_function="BioProcessSensor_Ammonia", unit="mM", kind="analog", cadence_s=60.0),
    ChannelConfig(channel_id="ph", env_field="ph", lads_function="BioProcessSensor_pH", unit="pH", kind="analog", cadence_s=5.0),
    ChannelConfig(channel_id="do", env_field="do_pct", lads_function="BioProcessSensor_DO", unit="%", kind="analog", cadence_s=5.0),
    ChannelConfig(channel_id="co2", env_field="co2_pct", lads_function="BioProcessSensor_CO2", unit="%", kind="analog", cadence_s=10.0),
    ChannelConfig(channel_id="temp", env_field="temp_c", lads_function="BioProcessSensor_Temperature", unit="°C", kind="analog", cadence_s=5.0),
    ChannelConfig(channel_id="osmolality", env_field="osmolality_mOsm_kg", lads_function="BioProcessSensor_Osmolality", unit="mOsm/kg", kind="analog", cadence_s=60.0),
    ChannelConfig(channel_id="agitation", env_field="agitation_rpm", lads_function="AgitationController_ActualSpeed", unit="rpm", kind="analog", cadence_s=5.0),
    ChannelConfig(channel_id="perfusion_rate", env_field="perfusion_rate_vvd", lads_function="PerfusionController_ActualRate", unit="vvd", kind="analog", cadence_s=5.0),
    ChannelConfig(channel_id="aggregate_diameter", env_field="aggregate_diameter_um", lads_function="AggregateAnalyzer_MeanDiameter", unit="µm", kind="analog", cadence_s=300.0),
    ChannelConfig(channel_id="large_aggregate_ratio", env_field="large_aggregate_ratio", lads_function="AggregateAnalyzer_LargeFraction", unit="-", kind="analog", cadence_s=300.0),
    ChannelConfig(channel_id="sterility", env_field="contamination_suspected", lads_function="SterilityMonitor_Contamination", unit="bool", kind="discrete", cadence_s=0.0),
]


def channel_config() -> list[ChannelConfig]:
    return CHANNELS


def route_channel(channel_id: str, payload: Any) -> dict[str, Any] | None:
    """MQTT/LADS channel ID → CellCultureEnv 更新辞書.

    payload は数値または {'value': ..., 'timestamp': ...} の形式を受け入れる.
    """
    for ch in CHANNELS:
        if ch.channel_id == channel_id:
            value = payload["value"] if isinstance(payload, dict) and "value" in payload else payload
            return {ch.env_field: value}
    return None
