"""Deterministic Power Query concept -> SQL rules (goal section 14).

Each handler turns one ``Table.*`` step into a SQL ``SELECT`` over the previous
relation, translating *concepts* (filter, projection, join, group, ...) rather
than syntax. Handlers return :class:`StepResult`; an unsupported shape sets
``unsupported`` so the pipeline flags it (and Phase 5 can route it to the LLM)
instead of emitting wrong SQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pqquack.convert import types
from pqquack.convert.args import (
    Call,
    parse_list_of_lists,
    parse_string_list,
    split_top_commas,
    string_value,
)
from pqquack.convert.mexpr import quote_ident, translate_scalar
from pqquack.parser.lexer import Token, TokenType


@dataclass
class StepContext:
    input_relation: str
    columns: list[str] | None
    query_names: set[str]


@dataclass
class StepResult:
    sql: str | None
    columns: list[str] | None = None
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unsupported: str | None = None

    @classmethod
    def unsupported_step(cls, reason: str) -> StepResult:
        return cls(sql=None, unsupported=reason)


def _proj(columns: list[str] | None) -> str:
    return "*" if columns is None else ", ".join(quote_ident(c) for c in columns)


def _resolve_relation(tokens: list[Token], ctx: StepContext) -> str | None:
    """Resolve a single-identifier argument to a relation name."""
    real = [t for t in tokens if t.type is not TokenType.EOF]
    if len(real) == 1 and real[0].type in (TokenType.IDENT, TokenType.QUOTED_IDENT):
        return quote_ident(real[0].value)
    return None


# --- Single-input transformations -------------------------------------------


def select_rows(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 2:
        return StepResult.unsupported_step("Table.SelectRows: missing predicate")
    predicate = translate_scalar(call.args[1])
    if predicate is None:
        return StepResult.unsupported_step("Table.SelectRows: unmappable predicate")
    sql = f"SELECT {_proj(ctx.columns)} FROM {ctx.input_relation} WHERE {predicate}"
    return StepResult(sql=sql, columns=ctx.columns)


def select_columns(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 2:
        return StepResult.unsupported_step("Table.SelectColumns: missing columns")
    cols = parse_string_list(call.args[1])
    if cols is None:
        return StepResult.unsupported_step("Table.SelectColumns: unmappable column list")
    sql = f"SELECT {', '.join(quote_ident(c) for c in cols)} FROM {ctx.input_relation}"
    return StepResult(sql=sql, columns=cols)


def remove_columns(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 2:
        return StepResult.unsupported_step("Table.RemoveColumns: missing columns")
    cols = parse_string_list(call.args[1])
    if cols is None:
        return StepResult.unsupported_step("Table.RemoveColumns: unmappable column list")
    if ctx.columns is not None:
        kept = [c for c in ctx.columns if c not in cols]
        sql = f"SELECT {', '.join(quote_ident(c) for c in kept)} FROM {ctx.input_relation}"
        return StepResult(sql=sql, columns=kept)
    excl = ", ".join(quote_ident(c) for c in cols)
    sql = f"SELECT * EXCLUDE ({excl}) FROM {ctx.input_relation}"
    return StepResult(sql=sql, columns=None, notes=["Uses DuckDB EXCLUDE (unknown schema)."])


def rename_columns(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 2:
        return StepResult.unsupported_step("Table.RenameColumns: missing rename pairs")
    pairs = parse_list_of_lists(call.args[1])
    if pairs is None:
        return StepResult.unsupported_step("Table.RenameColumns: unmappable rename pairs")
    mapping: dict[str, str] = {}
    for pair in pairs:
        if len(pair) != 2:
            return StepResult.unsupported_step("Table.RenameColumns: bad rename pair")
        old, new = string_value(pair[0]), string_value(pair[1])
        if old is None or new is None:
            return StepResult.unsupported_step("Table.RenameColumns: non-literal name")
        mapping[old] = new
    if ctx.columns is not None:
        proj, new_cols = [], []
        for c in ctx.columns:
            if c in mapping:
                proj.append(f"{quote_ident(c)} AS {quote_ident(mapping[c])}")
                new_cols.append(mapping[c])
            else:
                proj.append(quote_ident(c))
                new_cols.append(c)
        sql = f"SELECT {', '.join(proj)} FROM {ctx.input_relation}"
        return StepResult(sql=sql, columns=new_cols)
    ren = ", ".join(f"{quote_ident(o)} AS {quote_ident(n)}" for o, n in mapping.items())
    sql = f"SELECT * RENAME ({ren}) FROM {ctx.input_relation}"
    return StepResult(sql=sql, columns=None, notes=["Uses DuckDB RENAME (unknown schema)."])


def transform_column_types(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 2:
        return StepResult.unsupported_step("Table.TransformColumnTypes: missing pairs")
    pairs = parse_list_of_lists(call.args[1])
    if pairs is None:
        return StepResult.unsupported_step("Table.TransformColumnTypes: unmappable pairs")
    casts: dict[str, str] = {}
    for pair in pairs:
        if len(pair) < 2:
            return StepResult.unsupported_step("Table.TransformColumnTypes: bad pair")
        col = string_value(pair[0])
        if col is None:
            return StepResult.unsupported_step("Table.TransformColumnTypes: non-literal col")
        type_text = " ".join(t.value for t in pair[1])
        casts[col] = types.map_type(type_text)
    note = "Conservative TRY_CAST used for type conversion (goal section 15)."
    if ctx.columns is not None:
        proj = [
            f"TRY_CAST({quote_ident(c)} AS {casts[c]}) AS {quote_ident(c)}"
            if c in casts
            else quote_ident(c)
            for c in ctx.columns
        ]
        sql = f"SELECT {', '.join(proj)} FROM {ctx.input_relation}"
        return StepResult(sql=sql, columns=ctx.columns, notes=[note])
    repl = ", ".join(
        f"TRY_CAST({quote_ident(c)} AS {t}) AS {quote_ident(c)}" for c, t in casts.items()
    )
    sql = f"SELECT * REPLACE ({repl}) FROM {ctx.input_relation}"
    return StepResult(sql=sql, columns=None, notes=[note, "Uses DuckDB REPLACE (unknown schema)."])


def add_column(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 3:
        return StepResult.unsupported_step("Table.AddColumn: missing name/expression")
    name = string_value(call.args[1])
    if name is None:
        return StepResult.unsupported_step("Table.AddColumn: non-literal column name")
    expr = translate_scalar(call.args[2])
    if expr is None:
        return StepResult.unsupported_step("Table.AddColumn: unmappable expression")
    sql = f"SELECT {_proj(ctx.columns)}, {expr} AS {quote_ident(name)} FROM {ctx.input_relation}"
    cols = ctx.columns + [name] if ctx.columns is not None else None
    return StepResult(sql=sql, columns=cols)


def distinct(call: Call, ctx: StepContext) -> StepResult:
    sql = f"SELECT DISTINCT {_proj(ctx.columns)} FROM {ctx.input_relation}"
    return StepResult(sql=sql, columns=ctx.columns)


def sort(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 2:
        return StepResult.unsupported_step("Table.Sort: missing sort spec")
    terms: list[str] = []
    spec = parse_list_of_lists(call.args[1])
    if spec is not None:
        for pair in spec:
            col = string_value(pair[0])
            if col is None:
                return StepResult.unsupported_step("Table.Sort: non-literal column")
            direction = "ASC"
            if len(pair) >= 2:
                text = " ".join(t.value for t in pair[1])
                if "Descending" in text:
                    direction = "DESC"
            terms.append(f"{quote_ident(col)} {direction}")
    else:
        cols = parse_string_list(call.args[1])
        if not cols:
            return StepResult.unsupported_step("Table.Sort: unmappable sort spec")
        terms = [quote_ident(c) for c in cols]
    sql = f"SELECT {_proj(ctx.columns)} FROM {ctx.input_relation} ORDER BY {', '.join(terms)}"
    return StepResult(
        sql=sql,
        columns=ctx.columns,
        notes=["ORDER BY kept; preserve only if downstream order matters (goal section 14)."],
    )


# --- Aggregation and multi-input --------------------------------------------

_AGG_MAP = {
    "List.Sum": "SUM",
    "List.Average": "AVG",
    "List.Max": "MAX",
    "List.Min": "MIN",
    "List.Count": "COUNT",
}


def _translate_aggregate(tokens: list[Token]) -> str | None:
    real = [t for t in tokens if t.type is not TokenType.EOF]
    if real and real[0].type is TokenType.KEYWORD and real[0].value == "each":
        real = real[1:]
    if len(real) < 3 or real[0].type is not TokenType.IDENT:
        return None
    fn = real[0].value
    if fn == "Table.RowCount":
        return "COUNT(*)"
    agg = _AGG_MAP.get(fn)
    if agg is None or real[1].value != "(":
        return None
    inner = real[2:-1] if real[-1].value == ")" else real[2:]
    col_sql = translate_scalar(inner)
    if col_sql is None:
        return None
    return f"{agg}({col_sql})"


def group(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 2:
        return StepResult.unsupported_step("Table.Group: missing keys")
    keys = parse_string_list(call.args[1])
    if keys is None:
        return StepResult.unsupported_step("Table.Group: unmappable group keys")
    agg_terms: list[str] = []
    new_cols = list(keys)
    if len(call.args) >= 3:
        aggs = parse_list_of_lists(call.args[2])
        if aggs is None:
            return StepResult.unsupported_step("Table.Group: unmappable aggregations")
        for spec in aggs:
            agg_name = string_value(spec[0])
            if agg_name is None or len(spec) < 2:
                return StepResult.unsupported_step("Table.Group: bad aggregation spec")
            agg_sql = _translate_aggregate(spec[1])
            if agg_sql is None:
                return StepResult.unsupported_step("Table.Group: unmappable aggregation")
            agg_terms.append(f"{agg_sql} AS {quote_ident(agg_name)}")
            new_cols.append(agg_name)
    key_sql = ", ".join(quote_ident(k) for k in keys)
    select_list = ", ".join([quote_ident(k) for k in keys] + agg_terms)
    sql = f"SELECT {select_list} FROM {ctx.input_relation} GROUP BY {key_sql}"
    return StepResult(sql=sql, columns=new_cols)


def combine(call: Call, ctx: StepContext) -> StepResult:
    if not call.args:
        return StepResult.unsupported_step("Table.Combine: missing table list")
    inner = call.args[0]
    if not (inner and inner[0].value == "{" and inner[-1].value == "}"):
        return StepResult.unsupported_step("Table.Combine: expected a list of tables")
    relations: list[str] = []
    for element in split_top_commas(inner[1:-1]):
        rel = _resolve_relation(element, ctx)
        if rel is None:
            return StepResult.unsupported_step("Table.Combine: non-identifier table")
        relations.append(rel)
    sql = " UNION ALL ".join(f"SELECT * FROM {rel}" for rel in relations)
    return StepResult(sql=sql, columns=None, notes=["Append mapped to UNION ALL."])


_JOIN_MAP = {
    "JoinKind.Inner": "INNER JOIN",
    "JoinKind.LeftOuter": "LEFT JOIN",
    "JoinKind.RightOuter": "RIGHT JOIN",
    "JoinKind.FullOuter": "FULL JOIN",
}


def nested_join(call: Call, ctx: StepContext) -> StepResult:
    if len(call.args) < 5:
        return StepResult.unsupported_step("Table.NestedJoin: too few arguments")
    left_keys = parse_string_list(call.args[1])
    right_rel = _resolve_relation(call.args[2], ctx)
    right_keys = parse_string_list(call.args[3])
    if not left_keys or not right_keys or right_rel is None:
        return StepResult.unsupported_step("Table.NestedJoin: unmappable keys/right table")
    if len(left_keys) != len(right_keys):
        return StepResult.unsupported_step("Table.NestedJoin: key count mismatch")
    join_text = " ".join(t.value for t in call.args[5]) if len(call.args) >= 6 else ""
    join_kind = next((v for k, v in _JOIN_MAP.items() if k in join_text), "INNER JOIN")
    on = " AND ".join(
        f"l.{quote_ident(lk)} = r.{quote_ident(rk)}"
        for lk, rk in zip(left_keys, right_keys, strict=True)
    )
    sql = (
        f"SELECT l.*, r.* FROM {ctx.input_relation} AS l "
        f"{join_kind} {right_rel} AS r ON {on}"
    )
    return StepResult(
        sql=sql,
        columns=None,
        warnings=[
            "NestedJoin/Expand simplified: emitted as a flat join bringing in all "
            "right columns. Verify expanded/renamed columns match the original."
        ],
    )


def expand_table_column(call: Call, ctx: StepContext) -> StepResult:
    # The preceding NestedJoin already flattened in the right columns, so expansion
    # is treated as a passthrough. Column selection/renaming inside Expand is lost.
    return StepResult(
        sql=f"SELECT {_proj(ctx.columns)} FROM {ctx.input_relation}",
        columns=ctx.columns,
        notes=["ExpandTableColumn treated as passthrough (join already flattened)."],
    )


def buffer(call: Call, ctx: StepContext) -> StepResult:
    return StepResult(
        sql=f"SELECT {_proj(ctx.columns)} FROM {ctx.input_relation}",
        columns=ctx.columns,
        notes=["Table.Buffer is a no-op in SQL."],
    )


def promote_headers(call: Call, ctx: StepContext) -> StepResult:
    # Native readers (read_csv_auto, read_xlsx, ...) already promote the header
    # row, so this is a passthrough in the reconstructed pipeline.
    return StepResult(
        sql=f"SELECT {_proj(ctx.columns)} FROM {ctx.input_relation}",
        columns=ctx.columns,
        notes=["PromoteHeaders is implicit when reading with native readers."],
    )


# Dispatch table: M function -> handler.
RULES = {
    "Table.SelectRows": select_rows,
    "Table.SelectColumns": select_columns,
    "Table.RemoveColumns": remove_columns,
    "Table.RenameColumns": rename_columns,
    "Table.TransformColumnTypes": transform_column_types,
    "Table.AddColumn": add_column,
    "Table.Distinct": distinct,
    "Table.Sort": sort,
    "Table.Group": group,
    "Table.Combine": combine,
    "Table.NestedJoin": nested_join,
    "Table.ExpandTableColumn": expand_table_column,
    "Table.Buffer": buffer,
    "Table.PromoteHeaders": promote_headers,
}
