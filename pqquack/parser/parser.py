"""Pragmatic recursive parser for the M subset Power Query Quack needs.

Parses a single query into its ``let`` steps (or a single expression), extracting
per-step identifier references, invoked library functions, and column names. The
goal is reliable *dependency* information across the full breadth of real M —
not a complete evaluator — so unknown expression shapes are tolerated rather than
rejected (goal section 4.1: don't guess semantics we can't derive).
"""

from __future__ import annotations

from pqquack.parser.ast import Query, Step
from pqquack.parser.lexer import Token, TokenType, tokenize

_OPEN = {"(", "[", "{"}
_CLOSE = {")", "]", "}"}


def parse_query(name: str, source: str) -> Query:
    """Parse one query's source into a :class:`Query`."""
    tokens = [t for t in tokenize(source) if t.type is not TokenType.EOF]
    if not tokens:
        return Query(name=name, source_text=source, is_let=False)

    if tokens[0].type is TokenType.KEYWORD and tokens[0].value == "let":
        steps, output = _parse_let(tokens, source)
        is_let = True
    else:
        steps = [_build_step(name, tokens, source)]
        output = name
        is_let = False

    params = _collect_parameters(tokens)
    local_names = {s.name for s in steps}
    free: set[str] = set()
    head: list[str] = []
    for step in steps:
        free |= step.identifiers
        head.extend(step.head_functions)
    free -= local_names
    free -= params
    free.discard("_")

    return Query(
        name=name,
        source_text=source,
        steps=steps,
        output=output,
        is_let=is_let,
        free_identifiers=free,
        head_functions=head,
    )


def _parse_let(tokens: list[Token], source: str) -> tuple[list[Step], str | None]:
    """Parse ``let <steps> in <output>`` into steps and the output step name."""
    steps: list[Step] = []
    i = 1  # skip 'let'
    n = len(tokens)

    while i < n:
        name_tok = tokens[i]
        if name_tok.type not in (TokenType.IDENT, TokenType.QUOTED_IDENT):
            break
        step_name = name_tok.value
        i += 1
        # Skip to '='.
        while i < n and not (tokens[i].type is TokenType.OPERATOR and tokens[i].value == "="):
            i += 1
        i += 1  # skip '='

        start = i
        i = _scan_expression(tokens, i)
        expr_tokens = tokens[start:i]
        steps.append(_build_step(step_name, expr_tokens, source))

        if i < n and tokens[i].type is TokenType.PUNCT and tokens[i].value == ",":
            i += 1
            continue
        if i < n and tokens[i].type is TokenType.KEYWORD and tokens[i].value == "in":
            i += 1
            break
        break

    # Remaining tokens are the output expression.
    output_tokens = tokens[i:]
    output: str | None = None
    if len(output_tokens) == 1 and output_tokens[0].type in (
        TokenType.IDENT,
        TokenType.QUOTED_IDENT,
    ):
        output = output_tokens[0].value
    if output_tokens:
        steps.append(_build_step("$output", output_tokens, source))

    return steps, output


def _scan_expression(tokens: list[Token], start: int) -> int:
    """Return the index of the top-level terminator (',' or 'in') after ``start``.

    Respects bracket nesting and nested ``let .. in`` blocks so a comma or ``in``
    inside a sub-expression does not end the step early.
    """
    depth = 0
    let_depth = 0
    i = start
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t.type is TokenType.PUNCT and t.value in _OPEN:
            depth += 1
        elif t.type is TokenType.PUNCT and t.value in _CLOSE:
            depth -= 1
        elif t.type is TokenType.KEYWORD and t.value == "let":
            let_depth += 1
        elif t.type is TokenType.KEYWORD and t.value == "in":
            if let_depth > 0:
                let_depth -= 1
            elif depth == 0:
                return i
        elif (
            t.type is TokenType.PUNCT
            and t.value == ","
            and depth == 0
            and let_depth == 0
        ):
            return i
        i += 1
    return i


def _build_step(name: str, expr_tokens: list[Token], source: str) -> Step:
    """Build a :class:`Step` from its expression tokens."""
    identifiers, head_functions, field_names = _analyze_tokens(expr_tokens)
    if expr_tokens:
        text = source[expr_tokens[0].start : expr_tokens[-1].end]
    else:
        text = ""
    return Step(
        name=name,
        text=text,
        identifiers=identifiers,
        head_functions=head_functions,
        field_names=field_names,
    )


def _analyze_tokens(tokens: list[Token]) -> tuple[set[str], list[str], set[str]]:
    """Extract (reference identifiers, invoked functions, column names)."""
    identifiers: set[str] = set()
    head_functions: list[str] = []
    field_names: set[str] = set()

    for idx, t in enumerate(tokens):
        prev = tokens[idx - 1] if idx > 0 else None
        nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None

        if t.type is TokenType.QUOTED_IDENT:
            identifiers.add(t.value)
            continue
        if t.type is not TokenType.IDENT:
            continue

        # Bracketed field access: `[Column]` -> a column name, not a reference.
        is_field = (
            prev is not None
            and prev.type is TokenType.PUNCT
            and prev.value == "["
            and nxt is not None
            and nxt.type is TokenType.PUNCT
            and nxt.value == "]"
        )
        if is_field:
            field_names.add(t.value)
            continue

        # Record-literal field name: `[Name = ...]` / `[a = 1, Name = ...]`.
        # The identifier names a record field, not a query reference.
        is_record_field = (
            nxt is not None
            and nxt.type is TokenType.OPERATOR
            and nxt.value == "="
            and prev is not None
            and prev.type is TokenType.PUNCT
            and prev.value in ("[", ",")
        )
        if is_record_field:
            field_names.add(t.value)
            continue

        if "." in t.value:
            # Dotted library function/value (Table.SelectRows, Sql.Database). Not a
            # query reference; record it when it is actually invoked.
            if nxt is not None and nxt.type is TokenType.PUNCT and nxt.value == "(":
                head_functions.append(t.value)
            continue

        identifiers.add(t.value)

    return identifiers, head_functions, field_names


def _collect_parameters(tokens: list[Token]) -> set[str]:
    """Collect parameter names from any ``(a, b as text) => ...`` function headers."""
    params: set[str] = set()
    for k, t in enumerate(tokens):
        if not (t.type is TokenType.OPERATOR and t.value == "=>"):
            continue
        j = k - 1
        if j < 0 or not (tokens[j].type is TokenType.PUNCT and tokens[j].value == ")"):
            continue
        # Walk back to the matching '('.
        depth = 0
        m = j
        while m >= 0:
            v = tokens[m].value
            if tokens[m].type is TokenType.PUNCT and v == ")":
                depth += 1
            elif tokens[m].type is TokenType.PUNCT and v == "(":
                depth -= 1
                if depth == 0:
                    break
            m -= 1
        segment = tokens[m + 1 : j]
        expect_name = True
        for s in segment:
            if s.type is TokenType.PUNCT and s.value == ",":
                expect_name = True
            elif expect_name and s.type is TokenType.IDENT:
                params.add(s.value)
                expect_name = False
            # 'as <type>' annotations are skipped until the next comma.
    return params
