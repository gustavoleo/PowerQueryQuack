"""Per-runtime SQL dialect handling (goal sections 3, 10-12).

``duckdb`` (default), ``gizmosql``, and ``motherduck`` differ in file access,
extensions, remote execution, and native readers. Each target module emits
compatibility markers (e.g. "Local DuckDB only" / "MotherDuck only") so the
report layer can warn about runtime-specific limitations.

Phase 3 populates this package.
"""
