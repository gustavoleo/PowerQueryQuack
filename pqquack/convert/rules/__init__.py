"""Deterministic concept-mapping rules (goal section 14).

One module per Power Query concept (``Table.SelectRows`` -> WHERE,
``Table.Group`` -> GROUP BY, ``Table.NestedJoin`` -> JOIN, ...). Rules translate
*concepts*, not syntax, and preserve M semantics for nulls, errors, type
conversion, text comparison, dates, case sensitivity, and join kind.

Phase 3 populates this package.
"""
