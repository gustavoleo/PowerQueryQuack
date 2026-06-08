"""Split a Power Query document into individually named queries.

Uses the lexer so that ``shared`` / ``section`` / ``;`` tokens inside strings,
comments, or nested ``let .. in`` blocks never cause a wrong split.
"""

from __future__ import annotations

from pqquack.parser.lexer import TokenType, tokenize

_OPEN = {"(", "[", "{"}
_CLOSE = {")", "]", "}"}


def split_queries(text: str, default_name: str = "Query1") -> list[tuple[str, str]]:
    """Return ``[(name, source_text), ...]`` for every query in ``text``.

    A section document yields one entry per ``shared`` declaration; any other
    input is treated as a single query named ``default_name``.
    """
    tokens = tokenize(text)
    has_shared = any(t.type is TokenType.KEYWORD and t.value == "shared" for t in tokens)
    if not has_shared:
        stripped = text.strip()
        return [(default_name, stripped)] if stripped else []

    queries: list[tuple[str, str]] = []
    i = 0
    n = len(tokens)

    while i < n:
        t = tokens[i]
        if t.type is TokenType.EOF:
            break

        if t.type is TokenType.KEYWORD and t.value == "section":
            while i < n and not (tokens[i].type is TokenType.PUNCT and tokens[i].value == ";"):
                i += 1
            i += 1
            continue

        if t.type is TokenType.KEYWORD and t.value == "shared":
            i += 1
            if i >= n:
                break
            name = tokens[i].value
            i += 1
            # Skip to '='.
            while i < n and not (tokens[i].type is TokenType.OPERATOR and tokens[i].value == "="):
                i += 1
            i += 1  # skip '='
            if i >= n:
                break

            expr_start = tokens[i].start
            last_end = expr_start
            depth = 0
            let_depth = 0
            while i < n:
                tt = tokens[i]
                if tt.type is TokenType.EOF:
                    break
                if tt.type is TokenType.PUNCT and tt.value in _OPEN:
                    depth += 1
                elif tt.type is TokenType.PUNCT and tt.value in _CLOSE:
                    depth -= 1
                elif tt.type is TokenType.KEYWORD and tt.value == "let":
                    let_depth += 1
                elif tt.type is TokenType.KEYWORD and tt.value == "in" and let_depth > 0:
                    let_depth -= 1
                elif (
                    tt.type is TokenType.PUNCT
                    and tt.value == ";"
                    and depth == 0
                    and let_depth == 0
                ):
                    break
                last_end = tt.end
                i += 1

            queries.append((name, text[expr_start:last_end].strip()))
            if i < n and tokens[i].type is TokenType.PUNCT and tokens[i].value == ";":
                i += 1
            continue

        i += 1

    return queries
