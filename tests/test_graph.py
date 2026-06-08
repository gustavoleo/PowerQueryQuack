"""Dependency graph, classification, and circular-reference detection (goal sections 6-7)."""

from pathlib import Path

from pqquack.graph import analyze

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_multi_query_dependency_graph() -> None:
    result = analyze((SAMPLES / "multi-query-graph" / "input.pq").read_text())
    g = result.graph

    assert set(g.names) == {
        "Customer_Staging", "Customer", "Product_Staging", "Product",
        "Calendar", "Sales", "Unused_Scratch",
    }
    # Edges resolve to real queries only.
    assert g.edges["Sales"] == {"Customer", "Product", "Calendar"}
    assert g.edges["Customer"] == {"Customer_Staging"}
    assert g.edges["Calendar"] == set()
    # No false missing references (record fields / columns excluded).
    assert g.missing_references == {}
    # Sales is the only output (nothing references it).
    assert g.outputs() == ["Sales"]
    assert not result.has_cycle
    assert result.is_convertible


def test_roles_and_connector_isolation() -> None:
    g = analyze((SAMPLES / "multi-query-graph" / "input.pq").read_text()).graph
    assert g.roles["Sales"] == "output"
    assert g.roles["Customer_Staging"] == "source"
    assert g.roles["Unused_Scratch"] == "dead"
    # Staging queries that hit Sql.Database are flagged as source-acquisition.
    assert g.queries["Customer_Staging"].uses_custom_connector is True
    assert g.queries["Customer"].uses_custom_connector is False


def test_dependency_graph_renders_hierarchy() -> None:
    g = analyze((SAMPLES / "multi-query-graph" / "input.pq").read_text()).graph
    ascii_graph = g.render_ascii()
    assert "Sales" in ascii_graph
    assert "Customer_Staging" in ascii_graph
    # Children are nested under their dependents.
    assert "└── Customer_Staging" in ascii_graph or "├── Customer_Staging" in ascii_graph


def test_circular_reference_detection() -> None:
    result = analyze((SAMPLES / "circular-reference" / "input.pq").read_text())
    assert result.has_cycle
    assert not result.is_convertible
    assert len(result.cycles) == 1
    cycle = result.cycles[0]
    # The chain is closed (first == last) and covers A, B, C.
    assert cycle.cycle[0] == cycle.cycle[-1]
    assert set(cycle.cycle) == {"A", "B", "C"}
    assert "->" in cycle.chain
    assert cycle.root_cause
    assert "Break the cycle" in cycle.resolution


def test_self_reference_is_a_cycle() -> None:
    result = analyze("shared A = let Source = A in Source;")
    assert result.has_cycle


def test_genuine_missing_reference_is_flagged() -> None:
    # `Sales` references `Customer`, which is not defined anywhere.
    result = analyze("shared Sales = let Source = Customer in Source;")
    assert result.graph.missing_references.get("Sales") == {"Customer"}
