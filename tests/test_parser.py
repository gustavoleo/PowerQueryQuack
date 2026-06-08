"""Lexer, parser, and document-splitting behavior."""

from pqquack.ingest import split_queries
from pqquack.parser import TokenType, parse_query, tokenize


def test_lexer_handles_dotted_idents_strings_and_field_access() -> None:
    toks = [t for t in tokenize('Table.SelectRows(Source, each [Amount] > 100)')]
    values = [(t.type, t.value) for t in toks if t.type is not TokenType.EOF]
    assert (TokenType.IDENT, "Table.SelectRows") in values
    assert (TokenType.IDENT, "Amount") in values  # field name, still an ident token


def test_lexer_ignores_comments_and_strings() -> None:
    src = '"let in shared" // shared Foo = let\n/* shared Bar */ 1'
    kinds = {t.type for t in tokenize(src) if t.type is not TokenType.EOF}
    # No keyword tokens should leak out of the string/comment content.
    assert TokenType.KEYWORD not in kinds


def test_parse_let_extracts_steps_and_output() -> None:
    q = parse_query("Q", 'let\n A = Source,\n B = Table.SelectRows(A, each [x] > 1)\nin B')
    assert q.is_let
    assert [s.name for s in q.steps[:2]] == ["A", "B"]
    assert q.output == "B"
    assert "Table.SelectRows" in q.head_functions


def test_free_identifiers_exclude_local_steps_and_fields() -> None:
    src = (
        "let\n Source = Other,\n"
        " Filtered = Table.SelectRows(Source, each [Amount] > 0)\nin Filtered"
    )
    q = parse_query("Q", src)
    # `Other` is a free identifier (a reference); local steps and [Amount] are not.
    assert "Other" in q.free_identifiers
    assert "Source" not in q.free_identifiers
    assert "Filtered" not in q.free_identifiers
    assert "Amount" not in q.free_identifiers


def test_parameters_are_not_free_identifiers() -> None:
    q = parse_query("Fn", '(amount as number, label) => if amount > label then 1 else 0')
    assert "amount" not in q.free_identifiers
    assert "label" not in q.free_identifiers


def test_record_literal_field_names_are_not_references() -> None:
    src = 'let Source = Sql.Database("h", "db"){[Schema="dbo", Item="T"]}[Data] in Source'
    q = parse_query("Q", src)
    assert "Schema" not in q.free_identifiers
    assert "Item" not in q.free_identifiers
    assert "Sql.Database" in q.head_functions


def test_split_single_query() -> None:
    assert split_queries("let A = 1 in A") == [("Query1", "let A = 1 in A")]


def test_split_section_document_with_quoted_names() -> None:
    doc = 'section S;\nshared Customer = let A = 1 in A;\nshared #"Cust Staging" = let B = 2 in B;'
    result = dict(split_queries(doc))
    assert set(result) == {"Customer", "Cust Staging"}
    assert result["Customer"] == "let A = 1 in A"
    # A ';' inside a string must not split the query.
    doc2 = 'shared Q = let A = "x;y" in A;'
    assert split_queries(doc2) == [("Q", 'let A = "x;y" in A')]
