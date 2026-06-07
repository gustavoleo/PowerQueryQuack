"""Global dependency analysis and circular-reference detection (goal sections 6-7).

A hard gate: no SQL generation may begin until the dependency graph is built and
all circular references are resolved. Detects references, reuse, staging/fact/
dimension/lookup queries, dead queries, and missing references.

Phase 2 implements ``build`` (graph) and ``cycles`` (circular detection with
chain, root cause, and resolution proposal).
"""
