"""A lexer for the Power Query M language.

Tokenizes M source so downstream analysis never mistakes text inside strings,
comments, or bracketed field-access for query references. This is deliberately a
*lexer*, not a full grammar: it produces a faithful token stream that the
pragmatic parser in :mod:`pqquack.parser.parser` structures into queries and
steps for dependency analysis (goal sections 6-7).

Token offsets (``start``/``end``) index into the original source so the ingest
layer can slice exact query/expression text.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TokenType(StrEnum):
    IDENT = "ident"  # bare identifier, possibly dotted (Table.SelectRows, Int64.Type)
    QUOTED_IDENT = "quoted_ident"  # #"Customer Staging"
    KEYWORD = "keyword"  # let, in, each, true, #table, ...
    NUMBER = "number"
    STRING = "string"
    OPERATOR = "operator"  # = => < <= & + - ...
    PUNCT = "punct"  # ( ) { } [ ] , ;
    EOF = "eof"


# Lowercase M keywords. true/false/null are kept here too so they are never
# treated as identifier references.
KEYWORDS: frozenset[str] = frozenset(
    {
        "and", "as", "each", "else", "error", "false", "if", "in", "is", "let",
        "meta", "not", "otherwise", "or", "section", "shared", "then", "true",
        "try", "type", "null",
    }
)


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    start: int
    end: int


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_part(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def tokenize(source: str) -> list[Token]:
    """Tokenize M ``source`` into a list of tokens, ending with an EOF token."""
    tokens: list[Token] = []
    i = 0
    n = len(source)

    while i < n:
        ch = source[i]

        # Whitespace.
        if ch.isspace():
            i += 1
            continue

        # Comments.
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            j = source.find("\n", i)
            i = n if j == -1 else j
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "*":
            j = source.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue

        # String literal: "..." with "" as an escaped quote.
        if ch == '"':
            j = i + 1
            while j < n:
                if source[j] == '"':
                    if j + 1 < n and source[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            tokens.append(Token(TokenType.STRING, source[i : j + 1], i, j + 1))
            i = j + 1
            continue

        # Quoted identifier: #"..."
        if ch == "#" and i + 1 < n and source[i + 1] == '"':
            j = i + 2
            while j < n:
                if source[j] == '"':
                    if j + 1 < n and source[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            inner = source[i + 2 : j]
            tokens.append(Token(TokenType.QUOTED_IDENT, inner, i, j + 1))
            i = j + 1
            continue

        # Hash keyword: #table, #date, #shared, #datetimezone, ...
        if ch == "#" and i + 1 < n and source[i + 1].isalpha():
            j = i + 1
            while j < n and source[j].isalpha():
                j += 1
            tokens.append(Token(TokenType.KEYWORD, source[i:j], i, j))
            i = j
            continue

        # Number (including hex and fractional, but not the .. range operator).
        if ch.isdigit():
            j = i + 1
            if ch == "0" and j < n and source[j] in "xX":
                j += 1
                while j < n and source[j] in "0123456789abcdefABCDEF":
                    j += 1
            else:
                while j < n and source[j].isdigit():
                    j += 1
                # Fractional part only if '.' is not the start of a '..' range.
                if j < n and source[j] == "." and not (j + 1 < n and source[j + 1] == "."):
                    j += 1
                    while j < n and source[j].isdigit():
                        j += 1
                if j < n and source[j] in "eE":
                    k = j + 1
                    if k < n and source[k] in "+-":
                        k += 1
                    if k < n and source[k].isdigit():
                        j = k
                        while j < n and source[j].isdigit():
                            j += 1
            tokens.append(Token(TokenType.NUMBER, source[i:j], i, j))
            i = j
            continue

        # Identifier (dotted: a '.' is consumed only when followed by an ident char).
        if _is_ident_start(ch):
            j = i + 1
            while j < n:
                if _is_ident_part(source[j]):
                    j += 1
                elif source[j] == "." and j + 1 < n and _is_ident_start(source[j + 1]):
                    j += 1
                else:
                    break
            value = source[i:j]
            ttype = TokenType.KEYWORD if value in KEYWORDS else TokenType.IDENT
            tokens.append(Token(ttype, value, i, j))
            i = j
            continue

        # Multi-character operators.
        two = source[i : i + 2]
        if two in {"=>", "<=", ">=", "<>", ".."}:
            tokens.append(Token(TokenType.OPERATOR, two, i, i + 2))
            i += 2
            continue

        # Single-character punctuation and operators.
        if ch in "(){}[],;":
            tokens.append(Token(TokenType.PUNCT, ch, i, i + 1))
            i += 1
            continue
        tokens.append(Token(TokenType.OPERATOR, ch, i, i + 1))
        i += 1

    tokens.append(Token(TokenType.EOF, "", n, n))
    return tokens
