"""M -> DuckDB type mapping (goal section 15).

Fully specified by the goal, so implemented now rather than stubbed. Type
conversion is intentionally conservative: when source data quality is uncertain
callers should prefer ``TRY_CAST`` over ``CAST`` (see :func:`cast_expr`).
"""

from __future__ import annotations

# Canonical mapping from Power Query / M type names to DuckDB-compatible types.
# Keys are lowercased M type tokens; ``Int64.Type`` style tokens are handled by
# :func:`normalize_m_type` before lookup.
M_TO_DUCKDB: dict[str, str] = {
    "text": "VARCHAR",
    "number": "DOUBLE",
    "int64.type": "BIGINT",
    "int32.type": "INTEGER",
    "int16.type": "SMALLINT",
    "int8.type": "TINYINT",
    "date": "DATE",
    "datetime": "TIMESTAMP",
    "datetimezone": "TIMESTAMPTZ",
    "time": "TIME",
    "logical": "BOOLEAN",
    "duration": "INTERVAL",
    "binary": "BLOB",
    "currency.type": "DECIMAL(19, 4)",
    "percentage.type": "DOUBLE",
    "any": "VARCHAR",
}

# Types whose mapping carries a documented limitation/uncertainty the report
# layer should surface to the user (goal sections 15 & 16).
UNCERTAIN_TYPES: frozenset[str] = frozenset({"datetimezone", "any", "duration"})

# Fallback when an unknown/unmappable M type is encountered. ``any`` semantics:
# infer safely, otherwise preserve as VARCHAR and document the uncertainty.
DEFAULT_DUCKDB_TYPE = "VARCHAR"


def normalize_m_type(m_type: str) -> str:
    """Normalize an M type token for lookup (trim, lowercase, strip ``type`` kw)."""
    token = m_type.strip().lower()
    if token.startswith("type "):
        token = token[len("type ") :].strip()
    return token


def map_type(m_type: str) -> str:
    """Return the DuckDB type for an M type token, falling back to VARCHAR."""
    return M_TO_DUCKDB.get(normalize_m_type(m_type), DEFAULT_DUCKDB_TYPE)


def is_uncertain(m_type: str) -> bool:
    """True when the mapping should be flagged for validation (goal section 16)."""
    token = normalize_m_type(m_type)
    return token in UNCERTAIN_TYPES or token not in M_TO_DUCKDB


def cast_expr(column: str, m_type: str, *, safe: bool = True) -> str:
    """Build a CAST/TRY_CAST expression for ``column`` to the mapped DuckDB type.

    ``safe=True`` (default) emits ``TRY_CAST`` per the conservative-cast guidance;
    ``safe=False`` emits a strict ``CAST``.
    """
    duck_type = map_type(m_type)
    fn = "TRY_CAST" if safe else "CAST"
    return f"{fn}({column} AS {duck_type})"
