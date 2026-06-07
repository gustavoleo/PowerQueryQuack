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
