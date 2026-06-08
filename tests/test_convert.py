"""Phase 3: deterministic Power Query -> SQL conversion (goal sections 9, 13-15)."""

import duckdb
import pytest

from pqquack.convert import convert_text
from pqquack.enums import TargetRuntime


def convert(m: str, **kw):
    return convert_text(m, **kw)


# --- Core single-query concept rules (goal section 14) ----------------------


def test_filter_maps_to_where() -> None:
    r = convert('let S = Table.SelectRows(Orders, each [Amount] > 100) in S')
    assert "WHERE Amount > 100" in r.sql
    assert r.temp_table_free


def test_select_columns_projects_explicitly() -> None:
    r = convert('let S = Table.SelectColumns(T, {"A", "B"}) in S')
    assert "SELECT A, B FROM" in r.sql
    # With a known projection the final must not be a bare SELECT *.
    assert "SELECT *" not in r.sql.split("\n")[-1]


def test_rename_uses_aliases_when_columns_known() -> None:
    r = convert('let A = Table.SelectColumns(T, {"CustId"}), B = Table.RenameColumns(A, {{"CustId", "CustomerId"}}) in B')
    assert "CustId AS CustomerId" in r.sql


def test_type_conversion_uses_try_cast() -> None:
    r = convert('let S = Table.TransformColumnTypes(T, {{"Amount", type number}, {"Id", Int64.Type}}) in S')
    assert "TRY_CAST" in r.sql
    assert "AS DOUBLE" in r.sql and "AS BIGINT" in r.sql


def test_add_column_emits_derived_expression() -> None:
    r = convert('let S = Table.AddColumn(T, "Total", each [Price] * [Qty]) in S')
    assert "Price * Qty AS Total" in r.sql


def test_distinct_and_sort() -> None:
    assert "SELECT DISTINCT" in convert('let S = Table.Distinct(T) in S').sql
    sql = convert('let S = Table.Sort(T, {{"Name", Order.Descending}}) in S').sql
    assert "ORDER BY Name DESC" in sql


def test_group_by_with_aggregations() -> None:
    m = 'let S = Table.Group(T, {"Region"}, {{"Total", each List.Sum([Amount])}, {"N", each Table.RowCount(_)}}) in S'
    sql = convert(m).sql
    assert "GROUP BY Region" in sql
    assert "SUM(Amount) AS Total" in sql
    assert "COUNT(*) AS N" in sql


# --- Multi-input and unsupported -------------------------------------------


def test_append_maps_to_union_all() -> None:
    r = convert("section S; shared A = let x = T1 in x; shared B = let x = T2 in x; "
                "shared C = let x = Table.Combine({A, B}) in x;")
    assert "UNION ALL" in r.sql


def test_unsupported_step_is_flagged_not_guessed() -> None:
    r = convert('let S = Table.Pivot(T, a, b, c) in S')
    assert r.unsupported
    assert "UNSUPPORTED" in r.sql
    assert not r.success


# --- Invariants (non-negotiable, goal section 27) ---------------------------


def test_no_temporary_tables_or_procedural_sql_ever() -> None:
    samples = [
        'let S = Table.SelectRows(T, each [A] > 1) in S',
        'let S = Table.Group(T, {"R"}, {{"N", each Table.RowCount(_)}}) in S',
        'section S; shared A = let x = Sql.Database("h","db"){[Schema="dbo",Item="t"]}[Data] in x; '
        'shared B = let x = Table.SelectRows(A, each [Q] = true) in x;',
    ]
    for m in samples:
        result = convert(m)
        assert result.temp_table_free, f"forbidden constructs in: {m}"
        assert result.forbidden_constructs == []


def test_uses_cte_pipeline() -> None:
    r = convert('let A = Table.SelectColumns(T, {"X"}), B = Table.SelectRows(A, each [X] > 0) in B')
    assert r.sql.startswith("WITH ")


# --- Connector isolation + targets (goal sections 8, 11-12) -----------------


def test_connector_source_is_isolated_to_base_table() -> None:
    m = 'let Source = Sql.Database("srv","wh"), Data = Source{[Schema="dbo", Item="Customer"]}[Data] in Data'
    r = convert(m)
    assert "dbo.Customer" in r.sql
    assert any("isolated" in n for n in r.notes)


def test_remote_target_flags_local_file_paths() -> None:
    m = 'let Source = Csv.Document(File.Contents("/tmp/x.csv")) in Source'
    r = convert(m, target_runtime=TargetRuntime.MOTHERDUCK)
    assert "read_csv_auto('/tmp/x.csv')" in r.sql
    assert any("MotherDuck" in n for n in r.notes)


# --- Live execution against DuckDB ------------------------------------------


def test_generated_sql_executes_in_duckdb(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("id,amount,qty\n1,10,2\n2,40,2\n3,5,1\n")  # totals: 20, 80, 5

    m = f'''let
        Source = Csv.Document(File.Contents("{csv_path}"), [Delimiter=","]),
        Promoted = Table.PromoteHeaders(Source),
        Typed = Table.TransformColumnTypes(Promoted, {{{{"amount", type number}}, {{"qty", Int64.Type}}}}),
        Added = Table.AddColumn(Typed, "total", each [amount] * [qty]),
        Filtered = Table.SelectRows(Added, each [total] > 50)
    in Filtered'''

    result = convert(m)
    assert result.temp_table_free
    rows = duckdb.sql(result.sql).fetchall()
    # Only id=2 has total (80) > 50.
    assert len(rows) == 1
    assert rows[0][0] == 2


@pytest.mark.parametrize("runtime", list(TargetRuntime))
def test_all_runtimes_produce_temp_free_sql(runtime) -> None:
    r = convert('let S = Table.SelectRows(T, each [A] > 1) in S', target_runtime=runtime)
    assert r.temp_table_free
    assert r.target_runtime is runtime
