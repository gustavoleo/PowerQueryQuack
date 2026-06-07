"""Cached knowledge layer (goal sections 4 & 23).

Dev-time extractors turn ``PowerQueryLanguageSpecification.pdf`` and
``agent-skills-main.zip`` into structured JSON committed under ``data/``. At
runtime only the cached JSON is read — the source PDF/zip are never re-parsed or
re-sent to a model. If an asset cannot be parsed, callers fall back safely.

Phase 1 implements ``extract_spec`` / ``extract_skills``; :mod:`.store` provides
read access with a graceful empty-fallback today.
"""

from pqquack.knowledge.store import KnowledgeStore

__all__ = ["KnowledgeStore"]
