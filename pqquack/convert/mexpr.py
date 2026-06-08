"""Translate small M scalar/boolean expressions into DuckDB SQL.

Used by the conversion rules to turn ``each`` predicates and derived-column
expressions into SQL. Deliberately conservative: anything it cannot confidently
translate yields ``None`` so the caller can mark the step unsupported (and route
it to the LLM fallback) rather than emit wrong SQL.
"""

from __future__ import annotations

import re

from pqquack.parser.lexer import Token, TokenType, tokenize

# M scalar functions we can map directly to a DuckDB function name.
FUNCTION_MAP: dict[str, str] = {
    "Text.Upper": "upper",
    "Text.Lower": "lower",
    "Text.Length": "length",
    "Text.Trim": "trim",
    "Text.Start": "left",
    "Text.End": "right",
    "Text.Reverse": "reverse",
    "Number.Abs": "abs",
    "Number.Round": "round",
    "Number.RoundDown": "floor",
    "Number.RoundUp": "ceil",
    "Number.Sqrt": "sqrt",
    "List.Sum": "sum",
    "List.Max": "max",
    "List.Min": "min",
    "List.Average": "avg",
    "List.Count": "count",
}

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Reserved words we always quote when used as a column identifier.
_RESERVED = {"select", "from", "where", "group", "order", "by", "join", "table",
             "all", "and", "or", "not", "case", "when", "then", "else", "end"}


def quote_ident(name: str) -> str:
    """Quote a column/identifier only when needed (names with spaces/keywords)."""
    if _IDENT_RE.match(name) and name.lower() not in _RESERVED:
        return name
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def m_string_to_sql(raw: str) -> str:
    """Convert an M string literal token (incl. quotes) to a SQL string literal."""
    inner = raw[1:-1] if len(raw) >= 2 and raw[0] == '"' else raw
    inner = inner.replace('""', '"')  # un-escape M doubled quotes
    return "'" + inner.replace("'", "''") + "'"


def translate_scalar(tokens: list[Token]) -> str | None:
    """Translate a list of M expression tokens into a SQL scalar/boolean string.

    Returns ``None`` when an unmappable construct is encountered.
    """
    out: list[str] = []
    n = len(tokens)
    if_count = 0
    i = 0

    while i < n:
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < n else None

        if t.type is TokenType.KEYWORD and t.value == "each":
            i += 1
            continue

        # `[Column]` / `[Order Date]` field access -> column reference. M allows
        # generalized identifiers (spaces) inside the brackets.
        if t.type is TokenType.PUNCT and t.value == "[":
            j = i + 1
            parts: list[str] = []
            while j < n and not (tokens[j].type is TokenType.PUNCT and tokens[j].value == "]"):
                inner = tokens[j]
                # A record literal ([a = 1]) or nested bracket isn't a column name.
                if inner.type is TokenType.PUNCT or (
                    inner.type is TokenType.OPERATOR and inner.value == "="
                ):
                    return None
                parts.append(inner.value)
                j += 1
            if j >= n or not parts:
                return None
            out.append(quote_ident(" ".join(parts)))
            i = j + 1
            continue

        # Standalone `_` before a field access is the implicit row; drop it.
        if t.type is TokenType.IDENT and t.value == "_" and nxt and nxt.value == "[":
            i += 1
            continue

        if t.type is TokenType.STRING:
            out.append(m_string_to_sql(t.value))
            i += 1
            continue

        if t.type is TokenType.NUMBER:
            out.append(t.value)
            i += 1
            continue

        if t.type is TokenType.KEYWORD:
            v = t.value
            if v == "true":
                out.append("TRUE")
            elif v == "false":
                out.append("FALSE")
            elif v == "null":
                out.append("NULL")
            elif v == "and":
                out.append("AND")
            elif v == "or":
                out.append("OR")
            elif v == "not":
                out.append("NOT")
            elif v == "if":
                out.append("CASE WHEN")
                if_count += 1
            elif v == "then":
                out.append("THEN")
            elif v == "else":
                out.append("ELSE")
            else:
                return None
            i += 1
            continue

        if t.type is TokenType.OPERATOR:
            mapping = {"&": "||", "<>": "<>", "=": "=", "<": "<", ">": ">",
                       "<=": "<=", ">=": ">=", "+": "+", "-": "-", "*": "*", "/": "/"}
            if t.value not in mapping:
                return None
            out.append(mapping[t.value])
            i += 1
            continue

        if t.type is TokenType.PUNCT and t.value in ("(", ")", ","):
            out.append(t.value)
            i += 1
            continue

        if t.type is TokenType.IDENT:
            # Mapped scalar function call, e.g. Text.Upper(...).
            if "." in t.value and nxt is not None and nxt.value == "(":
                sql_fn = FUNCTION_MAP.get(t.value)
                if sql_fn is None:
                    return None
                out.append(sql_fn + "(")  # attach paren so there is no gap
                i += 2
                continue
            return None

        return None

    out.extend(["END"] * if_count)
    sql = " ".join(out)
    return _postprocess(sql)


def _postprocess(sql: str) -> str:
    """Tidy spacing and translate equality-with-null into IS [NOT] NULL."""
    sql = re.sub(r"\s+", " ", sql).strip()
    sql = re.sub(r"\(\s+", "(", sql)
    sql = re.sub(r"\s+\)", ")", sql)
    sql = re.sub(r"\s+,", ",", sql)
    sql = re.sub(r"<>\s*NULL", "IS NOT NULL", sql)
    sql = re.sub(r"=\s*NULL", "IS NULL", sql)
    return sql


def translate_expr_text(text: str) -> str | None:
    """Convenience: tokenize raw M expression text and translate it."""
    tokens = [t for t in tokenize(text) if t.type is not TokenType.EOF]
    return translate_scalar(tokens)
