# Architecture

Power Query Quack is a **gated pipeline**. Data flows left → right; the
dependency graph and validation act as hard gates. The engine is
**deterministic-first** with a Claude API fallback used only for unknown or
uncertain constructs.

```
              ingest → parse (M AST) → dependency graph → circular check
                                                          │ (gate: must pass)
                                                          ▼
                          convert: deterministic rule engine
                            ├─ connector isolation
                            ├─ concept mapping (Table.* → SQL)
                            ├─ type mapping (M → DuckDB)
                            └─ LLM fallback (Claude) for unknown/uncertain
                                                          │
                                                          ▼
                          validate (DuckDB live + static) → confidence
                                                          │
                                                          ▼
                       report assembler (10-section output) → API → Web UI
                                  ▲                                    │
                  knowledge layer ┘                  feedback / human review
              (cached from PDF + skills zip)
```

## Modules

| Module | Responsibility | Phase |
|---|---|---|
| `pqquack.ingest` | Accept inputs (`.pq/.m/.txt/.zip`, pasted text, About exports), normalize, split multi-query exports. | 2 |
| `pqquack.knowledge` | Read the cached M-spec + DuckDB/MotherDuck knowledge JSON. Extractors build it at dev time. | 1 |
| `pqquack.parser` | M lexer/parser → AST (`let..in`, records, lists, invocation, references). | 2 |
| `pqquack.graph` | Global dependency graph; circular detection (chain, root cause, resolution). **Hard gate.** | 2 |
| `pqquack.convert` | Deterministic concept rules, type mapping, connector isolation, pipeline assembly, per-target dialects. | 3 |
| `pqquack.llm` | Claude API fallback with caching + budget limits. | 5 |
| `pqquack.validate` | Static + live-DuckDB validation report. | 4 |
| `pqquack.confidence` | Confidence score with concrete reasons. | 4 |
| `pqquack.report` | 10-section output assembly + compatibility markers. | 4 |
| `pqquack.i18n` | pt-BR / en-US catalogs + language detection (en-US fallback). | 0/8 |
| `pqquack.feedback` | Feedback capture + human-review records. | 7 |
| `pqquack.api` | FastAPI app (`/health`, `/meta`, later `/convert`, `/feedback`). | 0/6 |
| `pqquack.web` | Static beta UI. | 6 |

## Hard gates

1. **Dependency analysis before conversion.** No SQL is generated until the
   global dependency graph is built (goal section 6).
2. **Circular references resolved before conversion.** Unresolved cycles block
   SQL generation; the engine reports the chain, root cause, and a resolution
   proposal (goal section 7).
3. **Validation before "production-ready".** Failing validation prevents the SQL
   from being presented as production-ready (goal section 16).

## Dependency analysis (Phase 2)

`pqquack.graph.analyze(text)` runs the full pre-conversion analysis:

1. **Split** the document into named queries (`ingest.split_queries`) — section
   documents (`shared Name = ...;`) or a single bare query.
2. **Parse** each query (`parser.parse_query`) into `let` steps, extracting per
   step the identifier references, invoked library functions, and column names.
   The lexer makes this robust: strings, comments, dotted identifiers
   (`Table.SelectRows`), quoted identifiers (`#"Customer Staging"`), bracketed
   field access (`[Amount]`), and record-literal fields (`[Schema="dbo"]`) are
   all distinguished so none are mistaken for query references.
3. **Build** the cross-query graph (`graph.build_dependency_graph`): resolve
   references, flag unresolved ones as *missing references*, and mark queries
   using source-acquisition functions (`Sql.Database`, `Web.Contents`, …) via the
   knowledge layer's access-library classification (connector isolation, §8).
4. **Detect cycles** (`graph.find_cycles`): DFS back-edge detection yielding the
   chain, root cause, and a resolution proposal. `AnalysisResult.is_convertible`
   is `False` whenever a cycle exists — the hard gate before SQL generation.

### Role classification (heuristic)

| Role | Rule |
|---|---|
| `dead` | isolated: nothing references it and it references nothing |
| `source` | references no other query (leaf) — or isolated but using a connector |
| `output` | nothing references it, but it consumes other queries (final) |
| `staging` | name contains "stag" |
| `lookup` | referenced by ≥2 queries (reused dimension/lookup) |
| `fact` | references ≥2 queries (combines inputs) |
| `intermediate` | everything else |

Missing-reference detection is conservative: unresolved free identifiers may
occasionally include uncaptured parameters, so they are surfaced as *candidates*
for the validation layer rather than hard errors.

## Deterministic-first + LLM fallback

Cost control (goal section 23) drives the design:

- Every M construct the rule engine can map, it maps — no model call.
- The LLM is invoked only for unmapped/uncertain constructs or low-confidence
  retries.
- Prompts are **small** and seeded with the *cached* knowledge layer; full
  documents are never sent.
- Responses are cached; per-conversion model-call counts and input sizes are
  capped.

## Knowledge layer

The Power Query spec PDF and skills zip are extracted **once at dev time** into
committed JSON (`pqquack/knowledge/data/`). Runtime reads only the JSON via
`KnowledgeStore`, which returns empty structures if a file is missing or corrupt
— the "asset unparseable → safe fallback" requirement (goal section 4).

## Future multi-LLM review pipeline

The stages (generate → review → compatibility → performance → human approval,
goal section 21) are kept separable so additional model reviewers can be added
later without restructuring the pipeline.

## Target runtimes

`duckdb` is the default and the only runtime used for **live** validation.
`gizmosql` and `motherduck` get static compatibility checks and explicit markers
(e.g. *"Local DuckDB only — GizmoSQL compatibility not guaranteed"*) because
remote runtimes differ in file access, extensions, and execution model
(goal sections 10–12).
