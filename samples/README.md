# Samples

Fixture-driven conversion cases. Each scenario from `CODEX_GOAL.md` section 25
gets its own folder containing the input Power Query (`input.pq`) and the
expected SQL shape (`expected.sql`), so the conversion engine can be tested
deterministically.

Planned scenarios (Phase 3 fills these in):

- `filter/` — simple filter (`Table.SelectRows` → `WHERE`)
- `select-columns/` — column selection
- `rename/` — column rename
- `type-cast/` — type conversion (`Table.TransformColumnTypes` → `TRY_CAST`)
- `add-column/` — calculated column
- `join/` — `Table.NestedJoin` → `JOIN`
- `group-by/` — `Table.Group` → `GROUP BY`
- `append/` — `Table.Combine` → `UNION ALL`
- `pivot-unpivot/`
- `query-reference/` — query reference conversion
- `multi-query-graph/` — multi-query dependency graph
- `circular-reference/` — circular reference detection
- `custom-connector/` — connector isolation

Every generated result is also checked against invariants: no temporary tables,
no T-SQL, no `SELECT *` in final outputs, no connector functions in
transformation logic.
