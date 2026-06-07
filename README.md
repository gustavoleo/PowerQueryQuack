# 🦆 Power Query Quack

**From M to DuckDB, one quack at a time.**

Power Query Quack transforms Power Query (M) solutions into native **DuckDB**,
**GizmoSQL**, or **MotherDuck** SQL. Power Query becomes the *source
specification*; the chosen SQL runtime becomes the *execution layer*. The goal is
not a line-by-line transpile — it is to reconstruct the whole transformation
pipeline as a clean, declarative analytical SQL solution and eliminate Power
Query from execution entirely.

> Status: **early beta / under construction.** See
> [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) for the phased roadmap
> and [`CODEX_GOAL.md`](CODEX_GOAL.md) for the full product specification.

## What it does

- Converts Power Query M into **CTE-based, set-based analytical SQL** (no temp
  tables, no T-SQL, no procedural/cursor logic — ever).
- Analyzes **all queries globally** first: builds a dependency graph and detects
  circular references *before* generating any SQL.
- **Isolates custom-connector / source-acquisition logic** from business
  transformation logic.
- Is **target-runtime aware** (`duckdb` default, `gizmosql`, `motherduck`) with
  explicit compatibility markers.
- Emits a **validation report**, a justified **confidence score**, and a
  **feedback** prompt with every conversion.
- Speaks **Portuguese (pt-BR)** and **English (en-US)**.

## Architecture at a glance

```
ingest → parse (M AST) → dependency graph → [circular check = hard gate]
       → convert (deterministic rules + connector isolation + LLM fallback)
       → validate (live DuckDB) → confidence → 10-section report → API → Web UI
```

The conversion engine is **deterministic-first**: rules handle known M patterns;
a Claude API fallback only handles unknown/uncertain constructs, behind caching
and budget limits (cost control). See [`docs/architecture.md`](docs/architecture.md).

## Requirements

- Python **3.11+**

## Install (development)

```bash
python -m pip install -e ".[dev]"      # core + test/lint tooling
python -m pip install -e ".[dev,llm]"  # also install the Claude API fallback deps
```

## Run the beta server

```bash
pqquack serve            # http://127.0.0.1:8000  (try /health and /meta)
# or
python -m pqquack.cli serve --port 8000
```

## Test & lint

```bash
pytest        # run the test suite
ruff check .  # lint
```

## Repository layout

| Path | Purpose |
|---|---|
| `pqquack/` | Python package (the gated conversion pipeline). |
| `pqquack/knowledge/data/` | Committed JSON knowledge cache (M spec + DuckDB/MotherDuck skills). |
| `pqquack/web/` | Static beta UI (upload / settings / results / feedback). |
| `docs/` | Architecture, conversion rules, connector policy, feedback workflow, plan. |
| `samples/` | Fixture conversion cases for each supported scenario. |
| `tests/` | Test suite. |
| `PowerQueryLanguageSpecification.pdf` | Canonical M reference (dev-time knowledge asset). |
| `agent-skills-main.zip` | MotherDuck / DuckDB skills package (dev-time knowledge asset). |

## Knowledge assets

The Power Query spec PDF and the MotherDuck skills zip are **first-class,
dev-time** inputs. They are extracted once into committed JSON under
`pqquack/knowledge/data/` and read from there at runtime — full documents are
never re-sent to a model (cost control).

## What is not supported yet

This is a Phase 0 scaffold. The M parser, dependency graph, conversion rules,
validation engine, LLM fallback, and full web UI arrive in later phases — see the
[development plan](docs/DEVELOPMENT_PLAN.md).

## Why no temporary tables?

The target is a **declarative analytical pipeline**, not an imperative ETL
script. Temp tables, table variables, and procedural logic are forbidden by
design; the engine uses CTEs, views, and final `SELECT`s (with optional `CREATE
TABLE AS SELECT` only when you explicitly ask for materialization). See
[`docs/conversion-rules.md`](docs/conversion-rules.md).

## License

See [`LICENSE`](LICENSE).
