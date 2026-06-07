# Conversion Rules

Power Query Quack translates **concepts, not syntax** (goal section 14). The
output is a declarative, set-based analytical SQL pipeline.

## Forbidden output (non-negotiable)

The generated SQL must **never** contain:

- Temporary / global temporary / local temporary tables
- Table variables
- T-SQL procedural logic, stored procedures, cursors, imperative loops
- SQL Server-specific syntax
- `SELECT *` in final outputs (unless explicitly required to preserve unknown schema)

## Preferred output

- CTEs via `WITH`
- Views when appropriate
- A final `SELECT`
- `CREATE TABLE AS SELECT` **only** when the user explicitly requests materialization
- Native DuckDB-compatible functions and set-based patterns

## Concept mapping (goal section 14)

| Power Query concept | SQL concept |
|---|---|
| `Table.SelectRows` | `WHERE` |
| `Table.SelectColumns` | `SELECT` column list |
| `Table.RemoveColumns` | Projection excluding removed columns (DuckDB `EXCLUDE` where helpful) |
| `Table.RenameColumns` | Column aliases |
| `Table.TransformColumnTypes` | `CAST` / `TRY_CAST` (prefer `TRY_CAST`) |
| `Table.AddColumn` | Derived column expression |
| `Table.NestedJoin` | `JOIN` (preserve join kind) |
| `Table.ExpandTableColumn` | Join projection / struct expansion |
| `Table.Group` | `GROUP BY` (DuckDB `GROUP BY ALL` where helpful) |
| `Table.Combine` | `UNION ALL` |
| `Table.Distinct` | `DISTINCT` |
| `Table.Sort` | `ORDER BY` **only** when order is required |
| `Table.Buffer` | Usually a no-op in SQL; explained if ignored |
| `Table.Pivot` | `PIVOT` or conditional aggregation |
| `Table.Unpivot` | `UNPIVOT` or equivalent |
| `Table.FillDown` / `Table.FillUp` | Window-function strategy |
| `Table.ReplaceValue` | `CASE` / `NULLIF` / `COALESCE` / `REPLACE` per semantics |

## Type mapping (goal section 15)

Implemented in `pqquack/convert/types.py`. Conversions are conservative — prefer
`TRY_CAST` when source data quality is uncertain.

| M type | DuckDB type |
|---|---|
| `text` | `VARCHAR` |
| `number` | `DOUBLE` |
| `Int64.Type` | `BIGINT` |
| `Int32.Type` | `INTEGER` |
| `date` | `DATE` |
| `datetime` | `TIMESTAMP` |
| `datetimezone` | `TIMESTAMPTZ` *(documented limitation when unsupported)* |
| `logical` | `BOOLEAN` |
| `duration` | `INTERVAL` |
| `any` | Inferred safely, else `VARCHAR` with documented uncertainty |

## Semantics to preserve

The engine must preserve M semantics for nulls, errors, type conversion, text
comparison, date/time behavior, case sensitivity, join kind, and duplicate-column
behavior. When exact behavior is uncertain, the conversion marks the risk and the
confidence score reflects it.

## Pipeline reconstruction

- Consolidate steps; **do not** emit one CTE per M step unless it improves
  clarity or validation.
- Push down filters, projections, type casts, and source pruning.
- Remove intermediate steps that do not change the final result.
- Prefer native readers for file sources (`read_parquet`, `read_csv_auto`,
  `read_json_auto`, `read_xlsx`) in preference order Parquet → JSON → CSV → XLSX
  (goal section 10).

## Source of truth

These rules are derived from `CODEX_GOAL.md` and the cached knowledge layer
extracted from `PowerQueryLanguageSpecification.pdf` and `agent-skills-main.zip`.
The Phase 1 extractor expands this document with concrete, citable M semantics.
