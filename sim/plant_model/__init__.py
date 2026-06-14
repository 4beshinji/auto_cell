"""Tier2 plant model — literature iPSC suspension-culture kinetics (Phase 0b).

Re-implements a published Monod-type ODE (constants: KGlc=1.5 mM, KLac=50 mM,
KGln=0.01 mM, KOsm=500 mOsm, KAgg=175 um, mu=1.35 /d) with scipy. Exposes a
plant interface ``step(actuators) -> sensors`` so the ReAct controller closes the
loop against a literature-grounded plant (not a hand-rolled one). The same
interface later accepts a COBRApy+GEM or commercial co-sim backend.

Validation target: reproduce published trajectories (7-day ~35e6 cells/mL,
lactate accumulation, DO 40%->10%).
"""
