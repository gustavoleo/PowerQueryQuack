# 🦆 Power Query Quack — Development Plan

> Living plan that turns `CODEX_GOAL.md` into an executable, phased build.
> Source of truth for *behavior* is `CODEX_GOAL.md`; this document is the source
> of truth for *how we build it*.

---

## 0. Decisions locked in

| Decision | Choice | Rationale |
|---|---|---|
| **Tech stack** | **Python + DuckDB**, FastAPI backend, lightweight HTML/JS frontend | Tightest fit with DuckDB (native Python bindings for live validation), cheapest to run, best parsing/testing ecosystem. |
| **Conversion engine** | **Deterministic rule engine first, Claude API fallback** | Matches the goal's cost-control + "deterministic rules before LLM" mandate. Rules handle known M patterns; the LLM only handles unknown/uncertain ones, behind caching + limits. |
| **First milestone** | **Repo scaffolding + docs + knowledge-extraction pipeline** | Safest groundwork. Establishes structure, CI, test harness, and the cached knowledge layer the goal requires *before* any conversion logic. |

Open items still to confirm later (do not block Phase 0):
- Claude model + budget for the LLM fallback (see Phase 5). Default target: latest Sonnet for cost/quality balance; escalate to Opus only on low-confidence retries.
- Persistence backend for feedback/human-review records (default: local SQLite/DuckDB file for the beta).
- Hosting (default: local-only beta; deploy later).

---

## 1. Guiding principles (from the goal)

1. **Reconstruct the pipeline, don't transpile line-by-line.** M is the *spec*; SQL is the *execution*.
2. **Deterministic before LLM.** Every M construct we can map with rules, we do — cheaply and testably.
3. **No SQL Server-isms, ever.** No temp tables, table variables, procedural/cursor logic, T-SQL.
4. **Declarative analytical SQL:** CTEs (`WITH`), views when appropriate, final `SELECT`, CTAS *only* on explicit request.
5. **Dependency analysis is a hard gate.** No SQL generation before the global dependency graph is built and circular references are resolved.
6. **Isolate connector/source-acquisition logic** from business-transformation logic. Connector knowledge never drives transformation recommendations.
7. **Target-runtime aware** (`duckdb` default, `gizmosql`, `motherduck`) with explicit compatibility markers.
8. **Always emit** dependency graph, validation report, confidence score, and feedback prompt.
9. **Bilingual:** pt-BR and en-US for all user-facing text.
10. **Use the repo assets** (`PowerQueryLanguageSpecification.pdf`, `agent-skills-main.zip`) as first-class knowledge, extracted and cached — never re-sent to the model wholesale.

---

## 2. Target architecture

Python package `pqquack/` with clear, independently testable modules. Data flows
left→right; the dependency graph and validation act as gates.

```
              ┌────────────────────────────────────────────────────────────┐
 Inputs  ───► │ ingest → parse (M AST) → dependency graph → circular check  │
 (.pq/.m/     └─────────────────────────────────────────┬──────────────────┘
  .txt/.zip/                                             │ (gate: must pass)
  About export/                                          ▼
  pasted text)        ┌─────────────────────────────────────────────────┐
                      │ convert: deterministic rule engine               │
                      │   ├─ connector isolation                         │
                      │   ├─ concept mapping (Table.* → SQL)             │
                      │   ├─ type mapping (M → DuckDB)                    │
                      │   └─ LLM fallback (Claude) for unknown/uncertain │
                      └───────────────────┬─────────────────────────────┘
                                          ▼
                      ┌─────────────────────────────────────────────────┐
                      │ validate (DuckDB live + static) → confidence     │
                      └───────────────────┬─────────────────────────────┘
                                          ▼
                      report assembler (10-section output) ─► API ─► Web UI
                                          ▲                            │
                          knowledge layer ┘            feedback / human review
                       (cached from PDF + skills zip)
```

### Proposed module layout

```
pqquack/
  __init__.py
  ingest/          # accept inputs, normalize, unzip, split About exports into queries
  knowledge/       # extract + cache M-spec rules and MotherDuck/DuckDB guidance
    extract_spec.py        # PDF → structured M rules (functions, types, semantics)
    extract_skills.py      # skills zip → DuckDB/MotherDuck conventions
    store.py               # cached knowledge access (JSON/SQLite), no live PDF parsing at runtime
  parser/          # M lexer + parser → AST (let..in, records, lists, invocations)
    lexer.py
    parser.py
    ast.py
  graph/           # dependency graph, classification, circular detection
    build.py               # references, reuse, staging/fact/dim/lookup/dead detection
    cycles.py              # circular chain + root cause + resolution proposal
  convert/         # deterministic conversion + LLM fallback orchestration
    rules/                 # one module per concept (select_rows, group, join, ...)
    connector.py           # custom-connector isolation + tagging
    types.py               # M → DuckDB type mapping (conservative casts)
    pipeline.py            # assemble CTE pipeline per query, consolidate steps
    targets/               # duckdb.py / gizmosql.py / motherduck.py dialect specifics
  llm/             # Claude API fallback: prompts, caching, budget/limits
    client.py
    cache.py
    budget.py
  validate/        # validation engine (static + DuckDB live execution checks)
    engine.py
    checks.py
  confidence/      # confidence scoring + reasons
    score.py
  report/          # 10-section output assembler, runtime compatibility markers
    assemble.py
  i18n/            # pt-BR / en-US message catalogs + language detection
    catalog_pt_BR.py
    catalog_en_US.py
    detect.py
  feedback/        # feedback capture + human-supervisor review records
    store.py               # SQLite/DuckDB-backed, anonymized by default
    records.py             # review-record schema (per goal §20)
  api/             # FastAPI app exposing convert + feedback endpoints
    app.py
  web/             # static frontend: upload / settings / results / feedback areas
    index.html, app.js, styles.css, i18n.js
docs/
tests/
samples/           # fixture M queries + expected SQL for each test scenario
```

---

## 3. Knowledge layer (build once, cache, reuse)

The goal forbids re-sending whole docs to the model. So Phase 1 produces a
**cached, structured knowledge layer** committed to the repo:

- **From `PowerQueryLanguageSpecification.pdf`:** extract M function catalog,
  type system, null/error semantics, `let..in` evaluation, operator behavior,
  case-sensitivity and date/time rules → `pqquack/knowledge/data/m_spec.json`.
- **From `agent-skills-main.zip`:** extract DuckDB/MotherDuck conventions —
  `motherduck-duckdb-sql` (native constructs: `GROUP BY ALL`, `QUALIFY`,
  `UNION BY NAME`, `EXCLUDE`, `REPLACE`, `arg_max`), `motherduck-load-data`
  (native readers), `motherduck-connect` (PG-endpoint vs native limits),
  `motherduck-migrate-to-motherduck` → `pqquack/knowledge/data/duckdb_skills.json`.
- Runtime reads only the cached JSON; the PDF/zip are dev-time inputs.

> ⚠️ Note: `pdftotext`/`pypdf` are not preinstalled in this environment. Phase 1
> must add a PDF text-extraction dependency (e.g. `pypdf`) and handle the
> "asset cannot be parsed → safe fallback" path the goal requires.

---

## 4. Phased delivery

Each phase is independently shippable and test-gated. ✅ = done, 🔵 = in progress, ⬜ = todo.

### Phase 0 — Scaffolding + docs  *(Milestone 1)*  ✅
- Python project: `pyproject.toml`, `pqquack/` package skeleton, `ruff` + `pytest` config.
- `requirements`/deps: `fastapi`, `uvicorn`, `duckdb`, `pypdf`, `pydantic`, `anthropic` (fallback), `pytest`, `ruff`.
- Docs per goal §24: `README.md`, `docs/architecture.md`, `docs/conversion-rules.md`,
  `docs/custom-connector-policy.md`, `docs/feedback-workflow.md`.
- CI: GitHub Actions running lint + tests. Test harness + `samples/` skeleton.
- `SessionStart` hook so web sessions can run tests/linters (see `session-start-hook` skill).
- **Exit criteria:** `pytest` runs green (even if near-empty), CI passes, docs stubs in place.

### Phase 1 — Knowledge extraction layer  ✅
- `extract_spec.py` + `extract_skills.py` + `build.py` produce committed JSON; `store.py` accessor with convenience queries.
- M catalog (~117 libraries / ~819 functions), enumerations, type tokens, access/connector-library classification; MotherDuck skill catalog + native constructs/readers.
- Documented in `docs/conversion-rules.md`.
- **Exit met:** knowledge JSON committed; tests assert key M functions/enums/access-libs and DuckDB conventions are present; extractors fall back safely on missing/unreadable assets. Regenerate via `python -m pqquack.knowledge.build`.

### Phase 2 — M parser + dependency graph + circular detection  ✅
- M lexer (`parser/lexer.py`) + pragmatic parser (`parser/parser.py`) → AST of `let` steps with per-step references, invoked functions, and column names; `ingest.split_queries` splits section documents into named queries.
- `graph/build.py`: reference resolution, missing-reference flagging, connector-acquisition marking via the knowledge layer, role classification (source/staging/fact/lookup/output/dead/intermediate), ASCII hierarchy rendering.
- `graph/cycles.py`: DFS cycle detection with chain, root cause, and resolution proposal. `graph.analyze(text)` ties it together; `AnalysisResult.is_convertible` is the **hard gate**.
- **Exit met:** multi-query dependency-graph and circular-reference sample fixtures + unit tests pass (lexer, parser, splitter, graph, cycles). 48 tests, ruff clean.

### Phase 3 — Deterministic conversion core  ⬜
- Concept rules (goal §14): `SelectRows`→WHERE, `SelectColumns`→projection, rename→aliases,
  `TransformColumnTypes`→CAST/TRY_CAST, `AddColumn`, `NestedJoin`→JOIN, `Group`→GROUP BY,
  `Combine`→UNION ALL, `Distinct`, `Sort` (only when order matters), Pivot/Unpivot, FillDown/Up→windows.
- Type mapping (goal §15), conservative casts. Connector isolation (goal §8).
- Pipeline assembler: consolidate steps into clean CTEs; **never** temp tables/`SELECT *` in finals.
- Per-target dialects: `duckdb` (default), `gizmosql`, `motherduck` + native readers (goal §10).
- **Exit:** sample-based tests for each scenario in goal §25; a test asserts **no temp tables** ever appear.

### Phase 4 — Validation + confidence + report assembly  ⬜
- `validate/engine.py`: static checks + optional live DuckDB execution (column count/names/types,
  joins, filters, aggregations, runtime compatibility). Report format per goal §16.
- `confidence/score.py`: percentage + concrete reasons (goal §17); low confidence requests more info.
- `report/assemble.py`: the 10-section output (goal §18) with compatibility markers (§11–12).
- **Exit:** validation report + confidence emitted; failing validation never marked production-ready.

### Phase 5 — LLM fallback (Claude)  ⬜
- `llm/client.py` using the `anthropic` SDK; small prompts seeded with *cached* knowledge (never full docs).
- Triggered only for unmapped/uncertain constructs or low-confidence retries.
- Cost controls (goal §23): response caching, per-conversion call cap, file-size/query limits, deterministic-first ordering.
- **Confirm before building:** model choice + budget (default Sonnet, escalate to Opus on low-confidence retry only). Consult the `claude-api` skill for current model IDs.
- **Exit:** fallback covered by tests with the client mocked; budget guardrails enforced.

### Phase 6 — Web MVP  ⬜
- FastAPI endpoints: `POST /convert`, `POST /feedback`. Static UI with Upload / Settings
  (language, target runtime, output mode) / Results (graph, report, SQL, validation, compat, confidence) / Feedback areas (goal §22).
- **Exit:** end-to-end conversion runnable locally in the browser.

### Phase 7 — Feedback + human supervisor  ⬜
- Feedback options 👍/👎/🛠 (goal §19); review-record schema + store (goal §20), anonymized by default.
- Export of uncertain/failed conversions for human review.
- **Exit:** feedback persisted; human-review export works; `docs/feedback-workflow.md` complete.

### Phase 8 — i18n + hardening  ⬜
- Full pt-BR/en-US catalogs + language detection with en-US fallback; localized validation/feedback text.
- Broaden parser/rule coverage, edge cases, performance, beta limits.
- **Exit:** pt-BR and en-US UI tests pass (goal §25); README explains what's not yet supported.

> The architecture must not block the **future multi-LLM review pipeline** (goal §21):
> keep generate / review / compatibility / performance as separable stages with clean interfaces.

---

## 5. Testing strategy

- **Fixture-driven:** every scenario in goal §25 gets a `samples/<case>/` with input M + expected SQL shape.
- **Invariant tests:** no temp tables, no T-SQL, no `SELECT *` in finals, no connector functions in transformation output.
- **Graph tests:** dependency resolution, circular detection, dead/missing queries.
- **Live validation tests:** generated SQL executes in an in-process DuckDB.
- **Per-target tests:** duckdb / gizmosql / motherduck compatibility markers.
- **i18n tests:** pt-BR and en-US strings present and selected correctly.
- LLM is **mocked** in tests for determinism and zero cost.

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| M parsing is large/complex | Support a pragmatic M subset first (the §25 scenarios); fall back to LLM for the rest; expand iteratively. |
| PDF extraction is brittle | Extract once at dev time into committed JSON; graceful "asset unparseable → safe fallback" path. |
| GizmoSQL/MotherDuck behavior differences | Explicit compatibility markers; live-validate only against DuckDB; mark remote-only features. |
| LLM cost creep | Deterministic-first, caching, per-conversion caps, small knowledge-seeded prompts, beta limits. |
| Semantic drift (nulls/errors/case/dates) | Encode M semantics from the spec into rules; mark uncertain conversions; conservative `TRY_CAST`. |

---

## 7. Immediate next steps (Phase 0)

1. Scaffold `pyproject.toml` + `pqquack/` package skeleton + `pytest`/`ruff` config.
2. Add dependency manifest (fastapi, uvicorn, duckdb, pypdf, pydantic, anthropic, pytest, ruff).
3. Write doc stubs: `README.md`, `docs/architecture.md`, `docs/conversion-rules.md`,
   `docs/custom-connector-policy.md`, `docs/feedback-workflow.md`.
4. Add GitHub Actions CI (lint + test) and a `SessionStart` hook.
5. Create `samples/` + `tests/` skeleton with one passing smoke test.

**Approval gate:** confirm this plan, then I execute Phase 0 on `claude/development-planning-7BEpp`.
