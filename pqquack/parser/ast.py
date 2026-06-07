"""AST node definitions for the parsed M subset.

Kept minimal in Phase 0: a typed ``Query`` container the ingest layer can already
populate (name + raw text + discovered references) before the full expression
parser lands in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Query:
    """A single named Power Query definition."""

    name: str
    source_text: str
    # Names of other queries this query references; filled by the graph builder.
    references: list[str] = field(default_factory=list)
    # True when the query's source-acquisition step uses a custom connector and
    # must be isolated from transformation logic (goal section 8).
    uses_custom_connector: bool = False
