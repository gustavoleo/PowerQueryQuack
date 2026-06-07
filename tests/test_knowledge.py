"""Phase 1: the extracted knowledge cache is present, sane, and queryable, and the
extractors degrade gracefully when an asset is missing/unreadable."""

from pathlib import Path

from pqquack.knowledge import KnowledgeStore, extract_skills, extract_spec

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- Committed cache content -------------------------------------------------


def test_m_spec_cache_has_core_libraries_and_functions() -> None:
    store = KnowledgeStore()
    spec = store.m_spec()
    assert spec.get("available") is True
    # Core transformation libraries must be catalogued.
    for lib in ("Table", "List", "Text", "Number", "Date"):
        assert lib in spec["libraries"]
    # Concept-mapping anchor functions (goal section 14) must be present.
    table_fns = set(spec["functions"]["Table"])
    for fn in ("Table.SelectRows", "Table.Group", "Table.NestedJoin", "Table.Combine"):
        assert fn in table_fns


def test_join_kind_enumeration_is_clean() -> None:
    enums = KnowledgeStore().enumerations()
    join_kinds = set(enums["JoinKind"])
    assert "JoinKind.Inner" in join_kinds
    assert "JoinKind.LeftOuter" in join_kinds
    # Artifacts must be filtered out.
    assert "JoinKind.Type" not in join_kinds
    assert all(not k.split(".")[1][-1].isdigit() for k in join_kinds)


def test_access_libraries_support_connector_isolation() -> None:
    store = KnowledgeStore()
    assert {"Sql", "Web", "Excel"} <= store.access_libraries()
    # Source-acquisition functions are flagged; transformations are not.
    assert store.is_access_function("Sql.Database")
    assert store.is_access_function("Web.Contents")
    assert not store.is_access_function("Table.SelectRows")


def test_duckdb_skills_cache_has_catalog_and_constructs() -> None:
    store = KnowledgeStore()
    skills = store.duckdb_skills()
    assert skills.get("available") is True
    names = {s["name"] for s in store.skills()}
    assert {"motherduck-duckdb-sql", "motherduck-load-data"} <= names
    assert "GROUP BY ALL" in store.native_constructs()
    assert store.native_readers()[0] == "read_parquet"


# --- Extractor robustness (goal section 4: safe fallback) --------------------


def test_extract_spec_missing_asset_returns_fallback(tmp_path) -> None:
    result = extract_spec.extract(tmp_path / "nope.pdf")
    assert result["available"] is False
    assert result["functions"] == {}


def test_extract_skills_missing_asset_returns_fallback(tmp_path) -> None:
    result = extract_skills.extract(tmp_path / "nope.zip")
    assert result["available"] is False
    assert result["skills"] == []
    # Even on failure, the documented reader preference order is provided.
    assert result["native_readers"][0] == "read_parquet"


def test_extract_skills_bad_zip_returns_fallback(tmp_path) -> None:
    bad = tmp_path / "bad.zip"
    bad.write_text("not a zip")
    result = extract_skills.extract(bad)
    assert result["available"] is False
