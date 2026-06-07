# Knowledge data cache

Generated, committed JSON produced by the Phase 1 extractors:

- `m_spec.json` — extracted from `PowerQueryLanguageSpecification.pdf`
- `duckdb_skills.json` — extracted from `agent-skills-main.zip`

Runtime reads only these files (see `pqquack/knowledge/store.py`). They are
intentionally committed so no PDF/zip parsing happens at request time.

Regenerate after changing either asset:

```bash
python -m pqquack.knowledge.build
```
