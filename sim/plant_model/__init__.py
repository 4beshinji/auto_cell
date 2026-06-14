"""Tier2 plant model — literature iPSC suspension-culture kinetics (Phase 0b).

Re-implements the Monod-type in-silico process model of Manstein, Ullmann,
Triebert & Zweigerdt 2021:
  - Stem Cells Transl Med 10(7):1063-1080, "High density bioprocessing of human
    pluripotent stem cells by metabolic control and in silico modeling"
    (DOI 10.1002/sctm.20-0453, PMID 33660952) -- primary research.
  - STAR Protocols 2(4):100988 (DOI 10.1016/j.xpro.2021.100988, PMC8666714) --
    the in-silico model Table 1 (constants below).
Perfused hPSC stirred-tank culture controlling pH/DO/glucose/lactate/glutamine and
osmolality-peak suppression. Six-term Monod model.

Constants (Manstein 2021, Table 1) -- the hardcoded values ARE faithful:
  mu     = 1.35 /d          K_Glc = 1.5 mM        K_Lac = 50 mM
  K_Gln  = 0.01 mM          K_Osm = 500 mOsm/kg   K_Agg = 350/2 = 175 um (DIAMETER)
  q_Glc = 1.474e-8, q_Lac = 2.37e-8, q_Gln = 1.856e-9 mmol/cell/d
All six match this module's earlier values exactly -> no constant change needed.

Exposes ``step(actuators) -> sensors`` so the ReAct controller closes the loop
against a literature-grounded plant. NOTE: this is a PERFUSION process -- the plant
must accept a perfusion-rate input (Table 3: 0->7 vvd over days 1-7); standard batch
does not reach the target. The same interface later accepts a COBRApy+GEM or
commercial co-sim backend.

Validation target: reproduce the Manstein trajectory -- 70-fold / 7-day to
~35e6 cells/mL (150 mL = 5.25e9 cells), DO 40%->10% on days 6-7, pH 7.1.
(Standard batch reaches only ~2.3-2.4e6: Nogueira 2019 VW, Olmer 2012 stirred.)

History: an earlier P1 lit review tentatively attributed this model to Galvanauskas
et al. 2019 (Regen Therapy) and flagged the constants as "wrong"; that was a
mis-identification -- Galvanauskas is a related 3-term iPSC Monod model (glucose +
lactate + aggregate only, no glutamine/osmolality). The true source is Manstein 2021.
See docs/design/kg_to_auto_cell.md §4.1.
"""
