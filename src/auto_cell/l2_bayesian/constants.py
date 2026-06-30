"""BO experiment constants and Safe BO outcome constraints.

Constraints are derived from `kg_to_auto_cell.md` §4 CPP envelope and
`CppEnvelope` in `plugins/cell_culture/environment.py`.
"""

from __future__ import annotations

OBJECTIVE_METRIC = "run_objective"

# Safe BO outcome constraints as string expressions for AxClient compatibility.
# These are soft constraints on observed outcomes; the L1 sanitizer remains the
# hard safety envelope for in-run actuation.
SAFE_BO_OUTCOME_CONSTRAINTS = [
    "max_lactate_mm <= 50.0",
    "max_osmolality_mosm <= 500.0",
    "large_aggregate_ratio <= 0.20",
    "viability_final >= 0.85",
]
