"""Power Query Quack — from M to DuckDB, one quack at a time.

Transforms Power Query (M) solutions into native DuckDB / GizmoSQL / MotherDuck
SQL. Power Query is treated as the source *specification*; the target SQL runtime
is the *execution* layer.

This package is organized as a gated pipeline (see ``docs/architecture.md``):

    ingest -> parse -> graph (circular check = hard gate)
           -> convert (rules + connector isolation + LLM fallback)
           -> validate -> confidence -> report

Phase 0 ships the scaffolding plus the fully-specified deterministic pieces
(type mapping, i18n, feedback record schema, shared enums). Later phases fill in
the parser, dependency graph, conversion rules, validation, and web UI.
"""

from pqquack.enums import Language, OutputMode, ReviewStatus, TargetRuntime

__version__ = "0.0.1"

__all__ = [
    "__version__",
    "Language",
    "OutputMode",
    "ReviewStatus",
    "TargetRuntime",
]
