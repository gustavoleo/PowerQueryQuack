"""10-section conversion report assembly (goal section 18)."""

from pqquack.enums import Language, TargetRuntime
from pqquack.report import convert_and_report


def test_report_has_ten_sections_in_order() -> None:
    rep = convert_and_report('let S = Table.SelectColumns(T, {"A", "B"}) in S')
    assert len(rep.sections) == 10
    text = rep.render()
    assert "## 1. Executive Summary" in text
    assert "## 6. Generated SQL" in text
    assert "## 10. Feedback Request" in text


def test_report_includes_sql_validation_confidence_and_feedback() -> None:
    rep = convert_and_report('let S = Table.SelectColumns(T, {"A"}) in S')
    text = rep.render()
    assert "```sql" in text
    assert "Validation Report" in text
    assert "Translation Confidence:" in text
    assert "👍" in text and "👎" in text and "🛠" in text


def test_report_localizes_to_portuguese() -> None:
    rep = convert_and_report(
        'let S = Table.SelectColumns(T, {"A"}) in S', language=Language.PT_BR
    )
    text = rep.render()
    assert "Resumo Executivo" in text
    assert "SQL Gerado" in text
    assert "A conversão foi bem-sucedida?" in text


def test_report_detects_runtime_label() -> None:
    rep = convert_and_report(
        'let S = Table.Distinct(T) in S', target_runtime=TargetRuntime.MOTHERDUCK
    )
    assert "MotherDuck" in rep.render()


def test_report_not_specified_runtime_message() -> None:
    rep = convert_and_report('let S = Table.Distinct(T) in S', target_specified=False)
    assert "Not specified" in rep.render()


def test_circular_report_blocks_and_is_not_production_ready() -> None:
    rep = convert_and_report("section S; shared A = let x = B in x; shared B = let x = A in x;")
    text = rep.render()
    assert "A -> B -> A" in text or "B -> A -> B" in text
    assert not rep.production_ready


def test_multi_query_report_shows_dependency_graph() -> None:
    from pathlib import Path

    samples = Path(__file__).resolve().parents[1] / "samples" / "multi-query-graph"
    rep = convert_and_report(samples.joinpath("input.pq").read_text())
    text = rep.render()
    assert "Sales" in text
    assert "Customer_Staging" in text
