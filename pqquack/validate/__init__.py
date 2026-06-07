"""Validation engine (goal section 16).

Static checks plus optional live execution against an in-process DuckDB:
dependency resolution, circular references, unsupported functions, column
count/names/types, join/filter/aggregation/distinct/sort logic, business-rule
preservation, and target-runtime compatibility. Failing validation must prevent
the SQL from being presented as production-ready.

Phase 4 implements ``engine`` / ``checks``.
"""
