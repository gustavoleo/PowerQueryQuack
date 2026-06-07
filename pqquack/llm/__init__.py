"""Claude API fallback for unmapped / uncertain M constructs (goal sections 21 & 23).

Only invoked when the deterministic rule engine cannot confidently convert a
construct, or on low-confidence retries. Prompts are small and seeded with the
*cached* knowledge layer — full docs are never sent. Cost controls (response
caching, per-conversion call caps, file/query limits) live alongside the client.

Phase 5 implements ``client`` / ``cache`` / ``budget``. The model choice and
budget are confirmed with the user before wiring real calls.
"""
