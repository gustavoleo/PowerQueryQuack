"""Helpers for picking apart an M function call's arguments.

The parser hands each step its raw expression text; these helpers turn the common
``Table.Function(input, arg2, arg3, ...)`` shape and M list/record literals into
Python structures the conversion rules can act on. Everything returns ``None`` (or
an empty result) when the shape is not recognized, so callers can fall back
cleanly rather than misread an expression.
"""

from __future__ import annotations

from dataclasses import dataclass

from pqquack.convert.mexpr import m_string_to_sql
from pqquack.parser.lexer import Token, TokenType, tokenize

_OPEN = {"(", "[", "{"}
_CLOSE = {")", "]", "}"}


@dataclass
class Call:
    """A parsed ``Function(arg, arg, ...)`` call."""

    func: str
    args: list[list[Token]]


def lex(text: str) -> list[Token]:
    return [t for t in tokenize(text) if t.type is not TokenType.EOF]


def split_top_commas(tokens: list[Token]) -> list[list[Token]]:
    """Split a token list on top-level commas (respecting bracket nesting)."""
    parts: list[list[Token]] = []
    current: list[Token] = []
    depth = 0
    for t in tokens:
        if t.type is TokenType.PUNCT and t.value in _OPEN:
            depth += 1
        elif t.type is TokenType.PUNCT and t.value in _CLOSE:
            depth -= 1
        if depth == 0 and t.type is TokenType.PUNCT and t.value == ",":
            parts.append(current)
            current = []
            continue
        current.append(t)
    if current:
        parts.append(current)
    return parts


def parse_call(text: str) -> Call | None:
    """Parse ``Func( ... )`` into a :class:`Call`; ``None`` if not a call."""
    tokens = lex(text)
    if len(tokens) < 3:
        return None
    if tokens[0].type is not TokenType.IDENT:
        return None
    if not (tokens[1].type is TokenType.PUNCT and tokens[1].value == "("):
        return None
    if not (tokens[-1].type is TokenType.PUNCT and tokens[-1].value == ")"):
        return None
    inner = tokens[2:-1]
    args = split_top_commas(inner) if inner else []
    return Call(func=tokens[0].value, args=args)


def string_value(tokens: list[Token]) -> str | None:
    """Return the text of a single string-literal argument (M-unescaped)."""
    if len(tokens) == 1 and tokens[0].type is TokenType.STRING:
        sql = m_string_to_sql(tokens[0].value)
        return sql[1:-1].replace("''", "'")
    return None


def _strip_braces(tokens: list[Token]) -> list[Token] | None:
    if (
        len(tokens) >= 2
        and tokens[0].type is TokenType.PUNCT
        and tokens[0].value == "{"
        and tokens[-1].type is TokenType.PUNCT
        and tokens[-1].value == "}"
    ):
        return tokens[1:-1]
    return None


def parse_string_list(tokens: list[Token]) -> list[str] | None:
    """Parse ``{"A", "B"}`` (or a single ``"A"``) into ``["A", "B"]``."""
    single = string_value(tokens)
    if single is not None:
        return [single]
    inner = _strip_braces(tokens)
    if inner is None:
        return None
    result: list[str] = []
    for element in split_top_commas(inner):
        value = string_value(element)
        if value is None:
            return None
        result.append(value)
    return result


def parse_list_of_lists(tokens: list[Token]) -> list[list[list[Token]]] | None:
    """Parse ``{{a, b}, {c, d}}`` into element token-lists per pair.

    Returns a list whose items are the inner elements (each a token list), e.g.
    ``[[<a tokens>, <b tokens>], [<c tokens>, <d tokens>]]``.
    """
    inner = _strip_braces(tokens)
    if inner is None:
        return None
    pairs: list[list[list[Token]]] = []
    for element in split_top_commas(inner):
        element_inner = _strip_braces(element)
        if element_inner is None:
            return None
        pairs.append(split_top_commas(element_inner))
    return pairs
