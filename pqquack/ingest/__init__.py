"""Input ingestion (goal section 5).

Accepts raw M, ``.pq``/``.m``/``.txt`` files, ``.zip`` packages, pasted text, and
(preferred) Power BI "About" section exports containing all queries at once.
Normalizes inputs and splits multi-query exports into individually named queries
so the dependency graph can be built globally.

Phase 2 implements parsing/splitting; this is the placeholder boundary.
"""
