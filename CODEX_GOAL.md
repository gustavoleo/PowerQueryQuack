# 🦆 Power Query Quack — Codex Master Goal

## Product Name

**Power Query Quack**

## Tagline

**From M to DuckDB, one quack at a time.**

---

# 1. Mission

Build a production-ready AI agent and beta website/background service called **Power Query Quack**.

The core mission is:

> Transform Power Query solutions into native DuckDB, GizmoSQL, or MotherDuck compatible SQL, using the uploaded Power Query language reference and MotherDuck skills package in the project repository as first-class development resources.

The objective is **not** to translate Power Query line by line.

The objective is to reconstruct the full transformation pipeline as a clean analytical SQL solution that can run in the selected target environment.

The agent must eliminate Power Query from execution entirely.

Power Query becomes the source specification. DuckDB, GizmoSQL, or MotherDuck becomes the execution layer.

---

# 2. Target Languages

The product must support:

- Portuguese Brazil (`pt-BR`)
- English US (`en-US`)

The UI, explanations, validation messages, and feedback workflow must be available in both languages.

Default language selection behavior:

1. Detect the language of the user request when possible.
2. Allow manual language selection.
3. Use English US as fallback.

---

# 3. Target SQL Runtimes

The conversion agent must support these target modes:

- `duckdb`
- `gizmosql`
- `motherduck`

Default target:

- `duckdb`

When no target mode is selected, generate the safest common DuckDB-compatible SQL.

The generated SQL must avoid SQL Server assumptions.

The generated SQL must never generate:

- T-SQL procedural logic
- SQL Server-specific syntax
- Stored procedures
- Temporary tables
- Temp tables
- Global temporary tables
- Local temporary tables
- Table variables
- Procedural ETL scripts
- Cursor-based logic
- Imperative SQL loops

The generated solution must primarily use:

- CTEs using `WITH`
- Views when appropriate
- Final `SELECT` statements
- Optional `CREATE TABLE AS SELECT` only when the user explicitly requests materialization
- Native DuckDB-compatible functions
- Set-based analytical SQL patterns

The target architecture is a declarative analytical pipeline, not an imperative ETL workflow.

---

# 4. Repository Assets

The project repository is:

`https://github.com/gustavoleo/PowerQueryQuack`

The repository is expected to contain these first-class knowledge assets:

1. `PowerQueryLanguageSpecification.pdf`
2. `agent-skills-main.zip`

Codex must inspect these assets before implementing transformation rules.

## 4.1 Power Query Language Reference

Treat `PowerQueryLanguageSpecification.pdf` as the canonical reference for Power Query M behavior.

Use it to understand:

- M syntax
- Expressions
- `let ... in` blocks
- Evaluation behavior
- Functions
- Records
- Lists
- Tables
- Types
- Operators
- Errors
- Null handling
- Function invocation
- Variable scope
- Query references

Do not invent M semantics when the reference can be used.

## 4.2 MotherDuck Skills Package

Treat `agent-skills-main.zip` as the MotherDuck / DuckDB skills package.

Codex must:

1. Unzip or inspect the package.
2. Extract relevant SQL generation guidance.
3. Reuse conventions and patterns when compatible with this product.
4. Document useful extracted rules.
5. Avoid assuming package contents without inspection.

If any repository asset cannot be opened, parsed, or understood, report that clearly and continue with a safe fallback.

---

# 5. Supported Inputs

The platform must accept, or be designed to accept, these input types:

- Raw Power Query M code
- Power BI About section exports
- Power BI metadata exports
- PBIP projects
- Multiple Power Query definitions at once
- ZIP packages containing multiple query files
- Documentation files
- Screenshots in future versions
- Dataflow exports in future versions
- AnalyticsCreator exports in future versions

The preferred input format is the **Power BI About section export containing all Power Query definitions at once**.

Reason:

> Having all queries at the same time makes it easier to detect query references, circular references, staging queries, reused queries, dependency chains, and dead queries.

---

# 6. Global Query Analysis Requirement

Before generating SQL, the agent must analyze all provided Power Query queries globally.

The agent must build a complete dependency graph.

Example:

```text
Customer
└── Customer_Staging

Product
└── Product_Staging

Sales
├── Customer
├── Product
└── Calendar
```

The dependency engine must detect:

- Query references
- Query reuse
- Staging layers
- Fact-like queries
- Dimension-like queries
- Lookup queries
- Dead queries
- Circular references
- Missing references
- Source queries
- Final output queries

No SQL generation may begin until dependency analysis is complete.

---

# 7. Circular Reference Detection

The agent must detect circular dependencies before generating SQL.

Example:

```text
A -> B
B -> C
C -> A
```

Output:

```text
Circular Dependency Found

A -> B -> C -> A
```

The agent must provide:

- Circular chain
- Root cause
- A safe resolution proposal
- Which query or reference should be changed

Never generate final SQL from unresolved circular dependencies.

---

# 8. Custom Connector Rule

This rule is non-negotiable.

The agent must identify Power Query functions related to:

- Custom connectors
- Proprietary connectors
- Vendor-specific APIs
- Connector authentication
- Connector navigation tables
- Connector-specific metadata
- Connector-specific implementation functions

These functions must not be used as transformation guidance.

The agent must isolate connector/source acquisition logic from business transformation logic.

Only business transformations should be converted into SQL.

The agent must never recommend new Power Query functions from custom connectors as part of query improvement.

When documentation includes custom connector content, the agent must segregate it and mark it as connector-only knowledge.

Connector-only knowledge must not influence SQL transformation recommendations except for identifying the original source.

---

# 9. Native SQL Replacement Rule

The generated result must be executable directly in the selected SQL runtime without:

- Power BI
- Power Query
- M engine
- Gateways
- Custom connectors
- Intermediate Power Query artifacts

The agent must eliminate all Power Query execution steps.

The generated SQL must preserve:

- Business logic
- Row counts
- Column names
- Data types
- Filters
- Joins
- Aggregations
- Conditional columns
- Lookup logic
- Query dependencies
- Final analytical output

The agent should remove unnecessary intermediate Power Query steps when they do not change the final result.

The final output should be a clean SQL pipeline using:

- CTEs
- Views when appropriate
- Final SELECT statements
- Optional CTAS only when explicitly requested

Temporary tables are forbidden.

---

# 10. Source Reader Optimization

When the original source is a file and the selected runtime supports it, prefer native readers:

```sql
read_parquet()
read_csv_auto()
read_json_auto()
read_xlsx()
```

Preference order:

1. Parquet
2. JSON when source is JSON
3. CSV when source is CSV
4. XLSX when source is Excel
5. Views or external tables when runtime requires remote-compatible access

Avoid importing files into staging tables unless explicitly required by the user.

For GizmoSQL and MotherDuck, be careful with local file paths, authentication, remote execution, and filesystem access.

---

# 11. GizmoSQL Compatibility Rule

GizmoSQL is a first-class target runtime.

When target mode is `gizmosql`, the agent must generate SQL that is compatible with GizmoSQL whenever possible.

The agent must avoid assumptions that may fail in a remote SQL server context, especially:

- Local file paths
- Local extensions
- Local filesystem access
- Client-only execution features
- Authentication assumptions
- Connection-specific behavior

If a generated SQL feature is valid in local DuckDB but may not work in GizmoSQL, clearly mark it:

```text
Local DuckDB only — GizmoSQL compatibility not guaranteed.
```

If a generated SQL feature depends on GizmoSQL server configuration, clearly mark it:

```text
GizmoSQL runtime dependent.
```

---

# 12. MotherDuck Compatibility Rule

MotherDuck is a first-class target runtime.

When target mode is `motherduck`, the agent must prefer SQL that works in MotherDuck.

The agent must use the uploaded MotherDuck skills package as guidance.

If a feature is valid in local DuckDB but may not work in MotherDuck, clearly mark it:

```text
Local DuckDB only — MotherDuck compatibility not guaranteed.
```

If a feature is valid in MotherDuck but not guaranteed for local DuckDB or GizmoSQL, clearly mark it:

```text
MotherDuck only — not guaranteed for DuckDB/GizmoSQL.
```

---

# 13. SQL Architecture Rules

Generated SQL must be:

- Readable
- Maintainable
- Deterministic
- Set-based
- Production-ready
- DuckDB-compatible
- Target-runtime aware

Generated SQL must minimize:

- Duplicate transformations
- Unnecessary intermediate layers
- Redundant joins
- Repeated scans
- Unused columns
- Unnecessary sorts

Generated SQL must never use `SELECT *` in final outputs unless explicitly required to preserve unknown schema behavior.

Push down:

- Filters
- Projections
- Type casts
- Source pruning

Use CTE names that reflect Power Query steps when helpful, but consolidate steps when possible.

Do not create one CTE per Power Query step unless it improves clarity or validation.

---

# 14. Power Query Concept Translation Rules

Translate concepts, not syntax.

Common mapping examples:

| Power Query Concept | SQL Concept |
|---|---|
| `Table.SelectRows` | `WHERE` |
| `Table.SelectColumns` | `SELECT column list` |
| `Table.RemoveColumns` | Projection excluding removed columns |
| `Table.RenameColumns` | Column aliases |
| `Table.TransformColumnTypes` | `CAST` / `TRY_CAST` when needed |
| `Table.AddColumn` | Derived column expression |
| `Table.NestedJoin` | `JOIN` |
| `Table.ExpandTableColumn` | Join projection / struct expansion |
| `Table.Group` | `GROUP BY` |
| `Table.Combine` | `UNION ALL` |
| `Table.Distinct` | `DISTINCT` |
| `Table.Sort` | `ORDER BY` only when order is required by final result or subsequent logic |
| `Table.Buffer` | Usually no-op in SQL; explain if ignored |
| `Table.Pivot` | `PIVOT` or conditional aggregation |
| `Table.Unpivot` | `UNPIVOT` or equivalent |
| `Table.FillDown` | Window function strategy |
| `Table.FillUp` | Window function strategy |
| `Table.ReplaceValue` | `CASE`, `NULLIF`, `COALESCE`, or `REPLACE` depending on semantics |

The agent must preserve M semantics for:

- Nulls
- Errors
- Type conversion
- Text comparison
- Date/time behavior
- Case sensitivity
- Join kind
- Duplicate column behavior

When exact behavior is uncertain, the agent must mark the risk clearly.

---

# 15. Data Type Mapping

Default type mapping:

| Power Query / M Type | DuckDB-Compatible Type |
|---|---|
| `text` | `VARCHAR` |
| `number` | `DOUBLE` |
| `Int64.Type` | `BIGINT` |
| `Int32.Type` | `INTEGER` |
| `date` | `DATE` |
| `datetime` | `TIMESTAMP` |
| `datetimezone` | `TIMESTAMPTZ` when supported, otherwise document limitation |
| `logical` | `BOOLEAN` |
| `duration` | `INTERVAL` |
| `any` | Infer safely, otherwise preserve as `VARCHAR` or document uncertainty |

Type conversion must be conservative.

Prefer safe casts when source data quality is uncertain.

---

# 16. Validation Engine

Before presenting final SQL, the agent must generate a validation report.

Validation must check:

- Dependency resolution
- Circular references
- Missing queries
- Unsupported functions
- Column count
- Column names
- Data types
- Join logic
- Filter logic
- Aggregation logic
- Distinct logic
- Sort requirements
- Business rule preservation
- Target runtime compatibility

Validation output format:

```text
Validation Report

Dependency graph: PASS / FAIL
Circular references: PASS / FAIL
Unsupported functions: PASS / WARNING / FAIL
Column preservation: PASS / WARNING / FAIL
Business logic preservation: PASS / WARNING / FAIL
Target runtime compatibility: PASS / WARNING / FAIL
```

If validation fails, do not present the SQL as production-ready.

---

# 17. Confidence Engine

Every conversion must include a confidence score.

Example:

```text
Translation Confidence: 97.8%
```

The confidence score must be justified with concrete reasons.

Example:

```text
Reasons:
- All dependencies resolved
- No circular references found
- Standard table functions only
- Join kinds mapped directly
- Two type conversions require validation with sample data
```

Low confidence must trigger a request for additional information.

---

# 18. Output Format for Each Conversion

Every conversion response must use this structure:

## 1. Executive Summary

What was converted and what the generated SQL does.

## 2. Detected Target Runtime

One of:

- DuckDB
- GizmoSQL
- MotherDuck
- Not specified, using safest DuckDB-compatible SQL

## 3. Dependency Graph

Show the query dependency hierarchy.

## 4. Circular Reference Report

State whether circular references exist.

## 5. Conversion Notes

Explain important implementation decisions.

## 6. Generated SQL

Provide the full SQL.

## 7. Validation Report

Show validation checks.

## 8. Compatibility Notes

Mention runtime-specific limitations.

## 9. Confidence Score

Give percentage and reasons.

## 10. Feedback Request

Ask for beta feedback using the feedback options.

---

# 19. Feedback Workflow

After every conversion, present exactly these beta feedback options:

```text
Was the conversion successful?

👍 Correct
👎 Incorrect
🛠 Help Me Fix It
```

If the user selects `👍 Correct`:

- Mark conversion as successful.
- Save anonymized conversion metadata when possible.
- Do not save sensitive data unless explicitly allowed.

If the user selects `👎 Incorrect`:

Ask for:

1. Original Power Query code
2. Generated SQL
3. Error message
4. Expected result
5. Actual result
6. Target runtime

Then regenerate a corrected version.

If the user selects `🛠 Help Me Fix It`:

Start an assisted debugging flow.

Ask for the smallest missing information needed.

Do not restart the whole conversion unless required.

---

# 20. Human Supervisor Workflow

Every failed or uncertain conversion must be exportable for human review.

The product owner is the primary human supervisor.

The system must support:

- Human validation
- Human correction
- Human approval
- Human notes
- Re-test after correction

Suggested review record:

```json
{
  "conversion_id": "string",
  "language": "pt-BR or en-US",
  "target_runtime": "duckdb | gizmosql | motherduck",
  "status": "correct | incorrect | needs_help | human_review",
  "original_power_query_summary": "string",
  "generated_sql_summary": "string",
  "error_message": "string or null",
  "expected_result": "string or null",
  "actual_result": "string or null",
  "human_supervisor_notes": "string or null",
  "approved_by_human": false
}
```

---

# 21. Future Multi-LLM Review Pipeline

Design the architecture so future versions can support multiple model reviewers.

Future pipeline:

1. Agent A generates SQL.
2. Agent B reviews SQL correctness.
3. Agent C checks runtime compatibility.
4. Agent D checks performance and simplification.
5. Human supervisor approves uncertain or failed cases.

The MVP does not need all models implemented today.

The architecture must not block this future pipeline.

---

# 22. Website / UI MVP

Build a simple beta website or local web app that can be tested today.

The MVP must include:

## Upload Area

Accept:

- `.pq`
- `.m`
- `.txt`
- `.zip`
- `.pbip` where feasible
- pasted Power Query text

## Settings Area

Allow user to select:

- Language: Portuguese Brazil or English US
- Target runtime: DuckDB, GizmoSQL, or MotherDuck
- Output mode: final SELECT, view, or CTAS when explicitly requested

## Results Area

Show:

- Dependency Graph
- Conversion Report
- Generated SQL
- Validation Report
- Compatibility Notes
- Confidence Score

## Feedback Area

Show:

```text
👍 Correct
👎 Incorrect
🛠 Help Me Fix It
```

The MVP should be simple, usable, and inexpensive to run.

Prefer local execution, static UI, or existing available infrastructure before adding paid services.

---

# 23. Cost Control Rules

The beta must avoid unnecessary cost.

Implementation should prefer:

- Local parsing when possible
- Deterministic rules before LLM calls
- Small prompts
- File chunking
- Reuse of extracted repository knowledge
- Caching parsed documentation
- Caching conversion attempts
- Manual review for hard failures

Do not send entire documentation files to a model repeatedly.

Extract and cache reusable knowledge from the Power Query language reference and MotherDuck skills package.

For beta testing, enforce reasonable limits on:

- File size
- Number of queries per conversion
- Number of model calls per conversion
- Stored feedback data

---

# 24. Documentation Requirements

Codex must create or update documentation explaining:

- What Power Query Quack does
- How to run the beta
- How to use the website/UI
- How to paste Power Query About exports
- How to choose DuckDB, GizmoSQL, or MotherDuck
- How feedback works
- What is not supported yet
- Why temporary tables are forbidden
- How custom connector logic is isolated

Recommended files:

- `README.md`
- `CODEX_GOAL.md`
- `docs/architecture.md`
- `docs/conversion-rules.md`
- `docs/custom-connector-policy.md`
- `docs/feedback-workflow.md`

---

# 25. Test Requirements

Create tests or sample cases for:

- Simple filter conversion
- Column selection
- Column rename
- Type conversion
- Add calculated column
- Join conversion
- Group by conversion
- Append / union conversion
- Pivot / unpivot conversion
- Query reference conversion
- Multi-query dependency graph
- Circular reference detection
- Custom connector isolation
- DuckDB target mode
- GizmoSQL target mode
- MotherDuck target mode
- Portuguese UI text
- English UI text

Tests must verify that temporary tables are not generated.

---

# 26. Development Instructions for Codex

Before building new implementation files, Codex must inspect the existing repository structure.

First tasks:

1. Read the repository file tree.
2. Inspect `PowerQueryLanguageSpecification.pdf`.
3. Extract useful M language rules from the Power Query reference.
4. Inspect `agent-skills-main.zip`.
5. Extract DuckDB/MotherDuck implementation guidance from the skills package.
6. Create a reusable project knowledge layer from these assets.
7. Build the Power Query to SQL conversion agent using this knowledge layer.
8. Build the beta website or background interface.
9. Add tests.
10. Update documentation.

Do not start implementation only from this prompt.

The uploaded repository assets must guide implementation.

---

# 27. Non-Negotiable Rules

1. Never generate temporary tables.
2. Never generate SQL Server procedural logic.
3. Never use custom connector functions as transformation recommendations.
4. Never translate line by line when pipeline reconstruction is better.
5. Never ignore query dependencies.
6. Never generate SQL from unresolved circular references.
7. Never claim production readiness when validation fails.
8. Never assume MotherDuck or GizmoSQL compatibility when runtime behavior is uncertain.
9. Always preserve business logic.
10. Always produce target-runtime-aware SQL.

---

# 28. Success Criteria

The project is successful only when:

- Power Query is completely eliminated from execution.
- The generated SQL can target DuckDB, GizmoSQL, or MotherDuck.
- Generated SQL is production-ready when validation passes.
- Business logic remains identical.
- Query dependencies are correctly resolved.
- Circular references are detected before SQL generation.
- Custom connector logic is isolated.
- Temporary tables are never generated.
- Feedback can continuously improve the platform.
- The MVP website or background interface is operational.
- Portuguese Brazil and English US are supported.
- The uploaded Power Query language reference and MotherDuck skills package are used as first-class development resources.

---

# 29. Final Product Vision

Power Query Quack should become the best Power Query to DuckDB, GizmoSQL, and MotherDuck conversion platform available.

It should help users move transformation logic out of Power Query and into a modern, fast, testable, SQL-native analytical execution layer.
