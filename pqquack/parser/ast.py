"""AST nodes for the parsed M subset.

The parser is pragmatic: it structures a query into its ``let`` steps and, for
each step, records the information dependency analysis and (later) conversion
need — identifier references, called library functions, and bracketed column
names — without attempting a full expression tree. This is enough for the
Phase 2 dependency graph and gives Phase 3 the step boundaries to convert.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Step:
    """A single ``name = expression`` binding inside a ``let`` block."""

    name: str
    text: str
    # Non-dotted/quoted identifiers used in the expression that could be
    # references to other queries (field names and dotted library calls excluded).
    identifiers: set[str] = field(default_factory=set)
    # Dotted library functions that are *invoked* here, e.g. ``Table.SelectRows``,
    # ``Sql.Database``. Drives connector isolation and conversion rule dispatch.
    head_functions: list[str] = field(default_factory=list)
    # Bracketed column references, e.g. ``[Amount]``.
    field_names: set[str] = field(default_factory=set)


@dataclass
class Query:
    """A single named Power Query definition."""

    name: str
    source_text: str
    steps: list[Step] = field(default_factory=list)
    # The local step name returned by ``in`` (the query's final step), if simple.
    output: str | None = None
    is_let: bool = True

    # Identifiers used anywhere in the query that are not local step names or
    # parameters — i.e. candidate cross-query references (resolved by the graph).
    free_identifiers: set[str] = field(default_factory=set)
    # All library functions invoked across steps.
    head_functions: list[str] = field(default_factory=list)

    # Resolved references to other queries (filled in by the dependency graph).
    references: list[str] = field(default_factory=list)
    # True when a source-acquisition / connector function is used (goal section 8).
    uses_custom_connector: bool = False
