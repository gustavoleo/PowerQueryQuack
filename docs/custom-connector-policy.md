# Custom Connector Policy

> This rule is **non-negotiable** (goal section 8).

Power Query Quack strictly separates **source-acquisition logic** (how data is
fetched) from **business-transformation logic** (what is done to the data). Only
business transformations are converted into SQL.

## What counts as connector / source-acquisition logic

Functions and metadata related to:

- Custom connectors and proprietary connectors
- Vendor-specific APIs
- Connector authentication
- Connector navigation tables
- Connector-specific metadata
- Connector-specific implementation functions

## Rules

1. **Isolate.** Connector/source-acquisition steps are identified and separated
   from transformation steps during parsing (`Query.uses_custom_connector` flags
   the boundary).
2. **Never use as guidance.** Connector functions must **not** be used as
   transformation guidance, and the engine must **never** recommend new Power
   Query connector functions as part of query improvement.
3. **Tag, don't convert.** When documentation includes custom-connector content,
   it is segregated and marked as *connector-only knowledge*. Connector-only
   knowledge must not influence SQL transformation recommendations — except to
   identify the original source.
4. **Source substitution.** Where a runtime supports it, the acquired source is
   replaced with a native reader (e.g. `read_parquet`, `read_csv_auto`) or a
   view/external table, so the connector is eliminated from execution entirely
   (goal sections 9–10).

## Why

The objective is to **eliminate Power Query from execution**. Connector logic is
environment-specific (auth, gateways, proprietary APIs) and cannot — and must not
— be reproduced as analytical SQL. Treating it as transformation guidance would
leak non-portable, non-analytical behavior into the generated SQL.

## Runtime notes

For `gizmosql` and `motherduck`, be especially careful: local file paths, local
extensions, local filesystem access, and authentication assumptions may not be
valid in a remote context. Such cases are surfaced with explicit compatibility
markers (goal sections 11–12).
