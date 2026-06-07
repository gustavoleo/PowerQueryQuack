"""Phase 0 smoke tests: the package imports, enums/defaults hold, the knowledge
store degrades gracefully, review records match the goal schema, and the API
serves health/meta."""

import importlib

import pytest

import pqquack
from pqquack.enums import Language, OutputMode, ReviewStatus, TargetRuntime
from pqquack.feedback import ReviewRecord
from pqquack.knowledge import KnowledgeStore
from pqquack.report import SECTION_KEYS


def test_version_exposed() -> None:
    assert isinstance(pqquack.__version__, str)
    assert pqquack.__version__


def test_defaults_match_goal() -> None:
    assert Language.default() is Language.EN_US
    assert TargetRuntime.default() is TargetRuntime.DUCKDB
    assert OutputMode.default() is OutputMode.SELECT


def test_all_pipeline_modules_import() -> None:
    for name in [
        "pqquack.ingest",
        "pqquack.knowledge",
        "pqquack.parser",
        "pqquack.parser.ast",
        "pqquack.graph",
        "pqquack.convert",
        "pqquack.convert.types",
        "pqquack.convert.rules",
        "pqquack.convert.targets",
        "pqquack.llm",
        "pqquack.validate",
        "pqquack.confidence",
        "pqquack.report",
        "pqquack.i18n",
        "pqquack.feedback",
    ]:
        assert importlib.import_module(name) is not None


def test_knowledge_store_safe_fallback(tmp_path) -> None:
    store = KnowledgeStore(data_dir=tmp_path)  # empty dir -> no files
    assert store.m_spec() == {}
    assert store.duckdb_skills() == {}


def test_review_record_schema_matches_goal() -> None:
    record = ReviewRecord()
    expected_fields = {
        "conversion_id",
        "language",
        "target_runtime",
        "status",
        "original_power_query_summary",
        "generated_sql_summary",
        "error_message",
        "expected_result",
        "actual_result",
        "human_supervisor_notes",
        "approved_by_human",
    }
    assert set(record.model_dump()) == expected_fields
    assert record.approved_by_human is False
    assert record.status is ReviewStatus.HUMAN_REVIEW


def test_report_has_ten_sections() -> None:
    assert len(SECTION_KEYS) == 10


def test_api_health_and_meta() -> None:
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from pqquack.api import create_app

    client = fastapi_testclient.TestClient(create_app())

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    meta = client.get("/meta").json()
    assert meta["defaults"]["target_runtime"] == "duckdb"
    assert set(meta["target_runtimes"]) == {"duckdb", "gizmosql", "motherduck"}
    assert set(meta["languages"]) == {"en-US", "pt-BR"}
