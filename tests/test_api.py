"""Web API: /convert, /feedback, /meta, and static UI serving (goal section 22)."""

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")

from pqquack.api import create_app  # noqa: E402

client = fastapi_testclient.TestClient(create_app())


def test_convert_returns_full_report() -> None:
    r = client.post(
        "/convert",
        json={"text": 'let S = Table.SelectColumns(T, {"A", "B"}) in S', "target_runtime": "duckdb"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["sections"]) == 10
    assert "SELECT A, B" in data["sql"]
    assert data["confidence_percent"] is not None
    assert "markdown" in data


def test_convert_rejects_empty_input() -> None:
    r = client.post("/convert", json={"text": "   "})
    assert r.json().get("error")


def test_convert_localizes_to_portuguese() -> None:
    r = client.post(
        "/convert",
        json={"text": 'let S = Table.Distinct(T) in S', "language": "pt-BR"},
    )
    titles = [s["title"] for s in r.json()["sections"]]
    assert "Resumo Executivo" in titles


def test_convert_blocks_circular() -> None:
    r = client.post(
        "/convert",
        json={"text": "section S; shared A = let x = B in x; shared B = let x = A in x;"},
    )
    data = r.json()
    assert data["production_ready"] is False


def test_feedback_returns_conversion_id() -> None:
    r = client.post("/feedback", json={"verdict": "correct"})
    assert r.status_code == 200
    assert r.json()["received"] is True
    assert r.json()["conversion_id"]


def test_index_and_static_served() -> None:
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
