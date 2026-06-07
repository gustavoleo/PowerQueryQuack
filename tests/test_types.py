"""Type mapping is fully specified by the goal, so it is tested concretely."""

import pytest

from pqquack.convert import types


@pytest.mark.parametrize(
    ("m_type", "expected"),
    [
        ("text", "VARCHAR"),
        ("number", "DOUBLE"),
        ("Int64.Type", "BIGINT"),
        ("Int32.Type", "INTEGER"),
        ("date", "DATE"),
        ("datetime", "TIMESTAMP"),
        ("datetimezone", "TIMESTAMPTZ"),
        ("logical", "BOOLEAN"),
        ("duration", "INTERVAL"),
        ("any", "VARCHAR"),
    ],
)
def test_known_type_mapping(m_type: str, expected: str) -> None:
    assert types.map_type(m_type) == expected


def test_unknown_type_falls_back_to_varchar() -> None:
    assert types.map_type("Some.Unknown.Type") == types.DEFAULT_DUCKDB_TYPE == "VARCHAR"


def test_normalize_is_case_and_whitespace_insensitive() -> None:
    assert types.map_type("  INT64.TYPE  ") == "BIGINT"
    assert types.map_type("type text") == "VARCHAR"


def test_uncertain_types_flagged() -> None:
    assert types.is_uncertain("datetimezone")
    assert types.is_uncertain("any")
    assert types.is_uncertain("Some.Unknown.Type")
    assert not types.is_uncertain("text")


def test_cast_expr_defaults_to_safe_try_cast() -> None:
    assert types.cast_expr("col", "Int64.Type") == "TRY_CAST(col AS BIGINT)"
    assert types.cast_expr("col", "Int64.Type", safe=False) == "CAST(col AS BIGINT)"
