"""Global dependency analysis and circular-reference detection (goal sections 6-7).

A hard gate: no SQL generation may begin until the dependency graph is built and
all circular references are resolved. :func:`analyze` ties the pieces together —
split a document into queries, parse each, build the graph, and detect cycles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pqquack.graph.build import DependencyGraph, build_dependency_graph
from pqquack.graph.cycles import CircularReference, find_cycles
from pqquack.ingest import split_queries
from pqquack.knowledge import KnowledgeStore
from pqquack.parser import Query, parse_query


@dataclass
class AnalysisResult:
    """The result of global pre-conversion analysis."""

    queries: list[Query]
    graph: DependencyGraph
    cycles: list[CircularReference] = field(default_factory=list)

    @property
    def has_cycle(self) -> bool:
        return bool(self.cycles)

    @property
    def is_convertible(self) -> bool:
        """SQL generation may proceed only when there are no circular references."""
        return not self.has_cycle


def analyze(text: str, store: KnowledgeStore | None = None) -> AnalysisResult:
    """Run the full pre-conversion analysis over a Power Query document."""
    named = split_queries(text)
    queries = [parse_query(name, source) for name, source in named]
    graph = build_dependency_graph(queries, store=store)
    cycles = find_cycles(graph)
    return AnalysisResult(queries=queries, graph=graph, cycles=cycles)


__all__ = [
    "AnalysisResult",
    "CircularReference",
    "DependencyGraph",
    "analyze",
    "build_dependency_graph",
    "find_cycles",
]
