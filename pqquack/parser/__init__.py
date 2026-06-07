"""Power Query (M) lexer + parser producing an AST (goal section 4.1).

Targets the M subset needed for the goal section 25 scenarios first
(``let .. in`` blocks, records, lists, function invocation, query references),
expanding iteratively. Unknown constructs are surfaced for the LLM fallback
rather than guessed.

Phase 2 implements ``lexer`` / ``parser``; :mod:`.ast` holds node definitions.
"""
