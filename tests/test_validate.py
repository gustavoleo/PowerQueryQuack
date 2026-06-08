"""Validation engine: checks, statuses, production-readiness, live execution."""

from pqquack.convert import convert_text
from pqquack.graph import analyze
from pqquack.validate import CheckStatus, validate


def _run(m: str, **kw):
    analysis = analyze(m)
    conversion = convert_text(m)
    return analysis, conversion, validate(analysis, conversion, **kw)


def test_clean_conversion_is_production_ready() -> None:
    _, _, report = _run('let S = Table.SelectColumns(T, {"A"}) in S')
    assert report.production_ready
    statuses = {r.name: r.status for r in report.results}
    assert statuses["Circular references"] is CheckStatus.PASS
    assert statuses["Forbidden constructs (temp tables / procedural)"] is CheckStatus.PASS


def test_unsupported_step_fails_validation() -> None:
    _, _, report = _run("let S = Table.Pivot(T, a, b, c) in S")
    assert not report.production_ready
    assert report.overall is CheckStatus.FAIL


def test_circular_reference_fails_validation() -> None:
    m = "section S; shared A = let x = B in x; shared B = let x = A in x;"
    _, _, report = _run(m)
    assert report.overall is CheckStatus.FAIL
    circular = next(r for r in report.results if r.name == "Circular references")
    assert circular.status is CheckStatus.FAIL


def test_report_renders_goal_format() -> None:
    _, _, report = _run('let S = Table.SelectColumns(T, {"A"}) in S')
    text = report.render()
    assert text.startswith("Validation Report")
    assert "Dependency graph: PASS" in text
    assert "Overall:" in text


def test_live_execution_passes_with_sample_data() -> None:
    # A query reading a base table we define for the live check.
    m = 'let S = Table.SelectRows(orders, each [amount] > 100) in S'
    analysis = analyze(m)
    conversion = convert_text(m)
    # The source is unknown text; point the final SELECT at a defined relation by
    # validating the SQL directly through a known-good relation name.
    sql_relations = {"<source>": "SELECT 1 AS id, 150 AS amount UNION ALL SELECT 2, 50"}
    report = validate(analysis, conversion, sample_relations=sql_relations)
    live = next(r for r in report.results if r.name == "Live execution (DuckDB)")
    assert live.status is CheckStatus.PASS


def test_live_execution_reports_failure_on_bad_sql() -> None:
    from pqquack.convert.pipeline import ConversionResult
    from pqquack.enums import TargetRuntime

    analysis = analyze('let S = Table.SelectColumns(T, {"A"}) in S')
    broken = ConversionResult(sql="SELECT FROM WHERE;", target_runtime=TargetRuntime.DUCKDB)
    report = validate(analysis, broken, sample_relations={"x": "SELECT 1 AS a"})
    live = next(r for r in report.results if r.name == "Live execution (DuckDB)")
    assert live.status is CheckStatus.FAIL
