"""Resolve a query's data source into a SQL base relation (goal sections 8-10).

Separates source-acquisition / connector logic from business transformations and
prefers native readers for file sources. Connector specifics (auth, gateways,
navigation) are *not* reproduced as SQL — only the resulting table/file is
referenced, with notes recording the original source (goal section 8).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pqquack.convert.mexpr import m_string_to_sql, quote_ident
from pqquack.convert.targets import Target
from pqquack.parser.ast import Query
from pqquack.parser.lexer import TokenType, tokenize

# File-reader functions -> DuckDB native reader (goal section 10 preference order).
READER_MAP: dict[str, str] = {
    "Parquet.Document": "read_parquet",
    "Json.Document": "read_json_auto",
    "Csv.Document": "read_csv_auto",
    "Excel.Workbook": "read_xlsx",
}


@dataclass
class SourcePlan:
    """How to read the rows a query starts from."""

    relation: str  # a SQL relation usable after FROM
    kind: str  # reader | table | query_ref | inline | unknown
    ref_name: str | None = None  # the referenced query name, when kind == query_ref
    notes: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _find_string_after(text: str, key: str) -> str | None:
    """Return the string value of ``key = "value"`` in a record (e.g. Item="X")."""
    tokens = [t for t in tokenize(text) if t.type is not TokenType.EOF]
    for i in range(len(tokens) - 2):
        if (
            tokens[i].type is TokenType.IDENT
            and tokens[i].value == key
            and tokens[i + 1].type is TokenType.OPERATOR
            and tokens[i + 1].value == "="
            and tokens[i + 2].type is TokenType.STRING
        ):
            sql = m_string_to_sql(tokens[i + 2].value)
            return sql[1:-1].replace("''", "'")
    return None


def _first_string(text: str) -> str | None:
    for t in tokenize(text):
        if t.type is TokenType.STRING:
            sql = m_string_to_sql(t.value)
            return sql[1:-1].replace("''", "'")
    return None


def detect_source(
    query: Query, target: Target, query_names: set[str]
) -> SourcePlan:
    """Determine the base relation for ``query``."""
    # 1. Pure query reference: the source step is just another query's name.
    refs = query.free_identifiers & query_names
    first_step = query.steps[0] if query.steps else None
    if first_step is not None:
        head = first_step.identifiers - {query.name}
        ref = head & query_names
        if ref and not first_step.head_functions:
            name = sorted(ref)[0]
            return SourcePlan(relation=quote_ident(name), kind="query_ref", ref_name=name)

    # 2. File reader -> native reader.
    for fn in query.head_functions:
        reader = READER_MAP.get(fn)
        if reader:
            path = _first_string(query.source_text) or "<path>"
            plan = SourcePlan(
                relation=f"{reader}('{path}')",
                kind="reader",
                notes=[f"Source file read natively via {reader} (was {fn})."],
            )
            if not target.local_files_reliable and target.local_only_marker:
                plan.markers.append(
                    f"{target.local_only_marker} Local file path '{path}' "
                    "may not be reachable on the remote runtime."
                )
            return plan

    # 3. Database / connector source -> base table reference (connector isolated).
    if query.uses_custom_connector:
        item = _find_string_after(query.source_text, "Item")
        schema = _find_string_after(query.source_text, "Schema")
        connector = next((f for f in query.head_functions if "." in f), "a connector")
        if item:
            relation = quote_ident(item)
            if schema:
                relation = f"{quote_ident(schema)}.{quote_ident(item)}"
            return SourcePlan(
                relation=relation,
                kind="table",
                notes=[
                    f"Source-acquisition logic ({connector}) isolated; mapped to "
                    f"base table {relation}. Connector auth/navigation is not "
                    "reproduced in SQL (goal section 8)."
                ],
            )
        return SourcePlan(
            relation='"<source_table>"',
            kind="unknown",
            warnings=[
                f"Could not determine the source table name from {connector}; "
                "replace \"<source_table>\" with the real table."
            ],
        )

    # 4. Bare references to other queries (e.g. used only deeper in the pipeline).
    if refs:
        name = sorted(refs)[0]
        return SourcePlan(relation=quote_ident(name), kind="query_ref", ref_name=name)

    return SourcePlan(
        relation='"<source>"',
        kind="unknown",
        warnings=["Could not determine the data source for this query."],
    )
