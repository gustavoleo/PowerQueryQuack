-- Target: duckdb (default)
-- Pipeline reconstruction of the `filter` sample. Illustrative expected shape;
-- the Phase 3 engine will assert structure/semantics, not exact whitespace.
WITH source AS (
    SELECT *
    FROM read_csv_auto('sales.csv')
)
SELECT *
FROM source
WHERE Amount > 100;
