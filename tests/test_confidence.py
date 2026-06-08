"""Confidence scoring (goal section 17)."""

from pqquack.confidence import score
from pqquack.convert import convert_text
from pqquack.graph import analyze


def _score(m: str):
    return score(analyze(m), convert_text(m))


def test_clean_conversion_is_high_confidence() -> None:
    # A determined source (native reader) with only mapped steps -> full confidence.
    s = _score(
        'let Source = Csv.Document(File.Contents("x.csv")), '
        'S = Table.SelectColumns(Source, {"A"}) in S'
    )
    assert s.percent == 100.0
    assert not s.needs_more_info
    assert any("deterministic" in r for r in s.reasons)


def test_unsupported_lowers_confidence_and_requests_info() -> None:
    s = _score("let S = Table.Pivot(T, a, b, c) in S")
    assert s.percent < 100.0
    assert any("unsupported" in r.lower() for r in s.reasons)


def test_circular_reference_is_lowest_confidence() -> None:
    s = _score("section S; shared A = let x = B in x; shared B = let x = A in x;")
    assert s.percent <= 10.0
    assert s.needs_more_info


def test_render_includes_percentage_and_reasons() -> None:
    text = _score(
        'let Source = Csv.Document(File.Contents("x.csv")), S = Table.Distinct(Source) in S'
    ).render()
    assert "Translation Confidence:" in text
    assert "Reasons:" in text


def test_low_confidence_threshold_triggers_more_info() -> None:
    # Several unsupported steps drive confidence below the threshold.
    s = _score("let A = Table.Pivot(T, a, b, c), B = Table.Unpivot(A, x, y, z) in B")
    assert s.needs_more_info
    assert "low" in s.render().lower()
