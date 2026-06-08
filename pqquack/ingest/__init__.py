"""Input ingestion (goal section 5).

Accepts raw M, ``.pq``/``.m``/``.txt`` files, pasted text, and (preferred) Power BI
"About" / section-document exports containing all queries at once. The key job is
splitting a multi-query export into individually named queries so the dependency
graph can be built globally (goal section 6).

Two input shapes are supported today:

1. **Section document** — the canonical Power BI export::

       section Section1;
       shared Customer = let ... in ...;
       shared #"Customer Staging" = let ... in ...;

2. **Single query** — a bare ``let ... in ...`` (or any single expression), which
   becomes one query named ``Query1``.
"""

from pqquack.ingest.split import split_queries

__all__ = ["split_queries"]
