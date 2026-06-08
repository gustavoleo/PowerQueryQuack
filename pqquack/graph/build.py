"""Global dependency graph construction and query classification (goal section 6).

Builds the cross-query reference graph from parsed queries, resolves references,
flags missing references, marks source-acquisition (connector) queries, and
assigns each query a role (source / staging / fact / lookup / output / dead /
intermediate). This is the analysis that must complete before any SQL generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pqquack.knowledge import KnowledgeStore
from pqquack.parser.ast import Query


@dataclass
class DependencyGraph:
    """Resolved cross-query dependency graph."""

    queries: dict[str, Query]
    # name -> set of query names it references (outgoing edges).
    edges: dict[str, set[str]]
    # name -> set of names that reference it (incoming edges).
    reverse: dict[str, set[str]]
    # name -> identifiers used that resolve to no known query (candidate missing
    # references; may include uncaptured parameters — see goal section 6).
    missing_references: dict[str, set[str]] = field(default_factory=dict)
    # name -> classified role.
    roles: dict[str, str] = field(default_factory=dict)

    @property
    def names(self) -> set[str]:
        return set(self.queries)

    def dependencies(self, name: str) -> set[str]:
        return self.edges.get(name, set())

    def dependents(self, name: str) -> set[str]:
        return self.reverse.get(name, set())

    def outputs(self) -> list[str]:
        """Final queries: sinks that actually participate (excludes dead/isolated)."""
        return sorted(
            n
            for n in self.queries
            if not self.reverse.get(n) and self.roles.get(n) != "dead"
        )

    def dead_queries(self) -> list[str]:
        """Queries defined but referenced by and referencing nothing (goal section 6)."""
        return sorted(n for n, role in self.roles.items() if role == "dead")

    def render_ascii(self) -> str:
        """Render the dependency hierarchy from each root downward (goal section 6)."""
        # Roots are all sinks (incl. isolated/dead) so every query is shown; if the
        # whole graph is a cycle, fall back to listing all nodes as roots.
        roots = sorted(n for n in self.queries if not self.reverse.get(n))
        if not roots:
            roots = sorted(self.queries)
        lines: list[str] = []
        for root in roots:
            lines.append(root)
            self._render_children(root, "", {root}, lines)
        return "\n".join(lines)

    def _render_children(
        self, node: str, prefix: str, seen: set[str], lines: list[str]
    ) -> None:
        deps = sorted(self.edges.get(node, set()))
        for idx, dep in enumerate(deps):
            last = idx == len(deps) - 1
            connector = "└── " if last else "├── "
            lines.append(f"{prefix}{connector}{dep}")
            if dep in seen:  # guard against cycles when rendering
                continue
            seen = seen | {dep}
            extension = "    " if last else "│   "
            self._render_children(dep, prefix + extension, seen, lines)


def build_dependency_graph(
    queries: list[Query], store: KnowledgeStore | None = None
) -> DependencyGraph:
    """Resolve references among ``queries`` into a :class:`DependencyGraph`."""
    store = store if store is not None else KnowledgeStore()
    access_libraries = store.access_libraries()

    by_name = {q.name: q for q in queries}
    names = set(by_name)

    edges: dict[str, set[str]] = {n: set() for n in names}
    reverse: dict[str, set[str]] = {n: set() for n in names}
    missing: dict[str, set[str]] = {}

    for q in queries:
        resolved: set[str] = set()
        unresolved: set[str] = set()
        for ident in q.free_identifiers:
            # A query naming itself is a (degenerate) circular reference, so it is
            # kept as a self-edge rather than silently dropped.
            if ident in names:
                resolved.add(ident)
            else:
                unresolved.add(ident)
        edges[q.name] = resolved
        q.references = sorted(resolved)
        for target in resolved:
            reverse[target].add(q.name)
        if unresolved:
            missing[q.name] = unresolved

        # Connector / source-acquisition detection (goal section 8).
        q.uses_custom_connector = any(
            fn.split(".", 1)[0] in access_libraries for fn in q.head_functions
        )

    roles = _classify(by_name, edges, reverse)

    return DependencyGraph(
        queries=by_name,
        edges=edges,
        reverse=reverse,
        missing_references=missing,
        roles=roles,
    )


def _classify(
    queries: dict[str, Query],
    edges: dict[str, set[str]],
    reverse: dict[str, set[str]],
) -> dict[str, str]:
    """Assign a heuristic role to each query (documented in docs/architecture.md)."""
    roles: dict[str, str] = {}
    for name, q in queries.items():
        out_deg = len(edges.get(name, set()))
        in_deg = len(reverse.get(name, set()))

        if in_deg == 0 and out_deg == 0:
            # Defined but referenced by nothing and referencing nothing.
            role = "source" if q.uses_custom_connector else "dead"
        elif out_deg == 0:
            role = "source"
        elif in_deg == 0:
            role = "output"
        elif "stag" in name.lower():
            role = "staging"
        elif in_deg >= 2:
            role = "lookup"
        elif out_deg >= 2:
            role = "fact"
        else:
            role = "intermediate"
        roles[name] = role
    return roles
