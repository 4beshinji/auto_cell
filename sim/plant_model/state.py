"""Plant state, actuators and sensor dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class PlantState:
    """ODE 状態ベクタ (連続)."""

    vcd: float              # viable cells / mL
    viability: float        # 0-100 %
    glucose: float          # mM
    lactate: float          # mM
    glutamine: float        # mM
    osmolality: float       # mOsm/kg
    aggregate_diameter: float  # µm

    def to_array(self) -> NDArray[np.float64]:
        return np.array(
            [
                self.vcd,
                self.viability,
                self.glucose,
                self.lactate,
                self.glutamine,
                self.osmolality,
                self.aggregate_diameter,
            ],
            dtype=np.float64,
        )

    @classmethod
    def from_array(cls, arr: NDArray[np.float64]) -> Self:
        if arr.shape != (7,):
            raise ValueError(f"PlantState array must have shape (7,), got {arr.shape}")
        # Clip negative values to zero for physical consistency.
        vcd, viability, glucose, lactate, glutamine, osmolality, agg = np.maximum(
            arr, 0.0
        )
        viability = min(float(viability), 100.0)
        return cls(
            vcd=float(vcd),
            viability=float(viability),
            glucose=float(glucose),
            lactate=float(lactate),
            glutamine=float(glutamine),
            osmolality=float(osmolality),
            aggregate_diameter=float(agg),
        )


@dataclass(frozen=True)
class Actuators:
    """1 ステップ中に plant_model に適用されるアクチュエータ値."""

    perfusion_rate_vvd: float = 0.0   # vessel volumes / day (0-7)
    agitation_rpm: float = 80.0       # rpm
    do_setpoint: float = 40.0         # %
    ph_setpoint: float = 7.1          # -
    feed_glucose: float = 0.0         # mmol (bolus; 0 if continuous perfusion only)
    feed_glutamine: float = 0.0       # mmol (bolus)


@dataclass(frozen=True)
class Sensors:
    """`step()` が返すセンサ出力."""

    vcd: float
    viability: float
    glucose: float
    lactate: float
    glutamine: float
    osmolality: float
    aggregate_diameter_um: float
    do_percent: float
    ph: float
    temp_c: float
