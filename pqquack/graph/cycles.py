"""Circular-reference detection (goal section 7).

No final SQL may be generated from unresolved circular dependencies. For every
cycle found, we report the chain, a root cause, and a safe resolution proposal
naming the specific reference to change.
"""

from __future__ import annotations

from dataclasses import dataclass

from pqquack.graph.build import DependencyGraph


@dataclass
class CircularReference:
    """A detected dependency cycle and how to resolve it."""

    # Cycle as a closed path, e.g. ["A", "B", "C", "A"].
    cycle: list[str]

    @property
    def chain(self) -> str:
        """Human-readable chain, e.g. ``A -> B -> C -> A``."""
        return " -> ".join(self.cycle)

    @property
    def root_cause(self) -> str:
        closing_from = self.cycle[-2]
        closing_to = self.cycle[-1]
        return (
            f"Query '{closing_from}' references '{closing_to}', which (directly or "
            f"transitively) depends back on '{closing_from}'."
        )

    @property
    def resolution(self) -> str:
        closing_from = self.cycle[-2]
        closing_to = self.cycle[-1]
        return (
            f"Break the cycle by removing or redirecting the reference from "
            f"'{closing_from}' to '{closing_to}' — for example, extract the shared "
            f"logic into a separate staging query that both can reference without "
            f"forming a loop."
        )


def find_cycles(graph: DependencyGraph) -> list[CircularReference]:
    """Return all distinct dependency cycles in ``graph``.

    Uses depth-first search with a recursion stack; each back edge yields the
    cycle path. Cycles are de-duplicated by their normalized node set.
    """
    cycles: list[CircularReference] = []
    seen_signatures: set[frozenset[str]] = set()

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in graph.queries}

    def visit(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        stack.append(node)
        for nxt in sorted(graph.edges.get(node, set())):
            if color.get(nxt, WHITE) == GRAY:
                # Back edge -> cycle from nxt's position in the stack to node.
                start = stack.index(nxt)
                path = stack[start:] + [nxt]
                signature = frozenset(path)
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    cycles.append(CircularReference(cycle=path))
            elif color.get(nxt, WHITE) == WHITE:
                visit(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for n in sorted(graph.queries):
        if color[n] == WHITE:
            visit(n, [])

    return cycles
