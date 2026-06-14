"""cell_culture domain plugin (iPSC suspension bioreactor) — Phase 0b.

Will export ``plugin_class = CellCulturePlugin`` (a physical_ai_core
``DomainVertical`` subclass) once the core is extracted. Planned modules:
environment / channels / events / tools / sanitizer_rules / prompt.

Reference implementation to mirror: auto_JA hydroponics plugin (liquid pH/DO/
temperature/flow is the closest analog). CPP setpoints and control strategy are
specified in the planning blueprint (pH 7.1, DO 40%, agitation 50-120 rpm,
lactate <50 mM, aggregate 150-350 um, VCD via capacitance).
"""
