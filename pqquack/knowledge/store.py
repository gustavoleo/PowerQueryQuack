"""Runtime accessor for the cached knowledge layer.

Reads committed JSON under ``pqquack/knowledge/data/``. Missing files return empty
structures rather than raising, satisfying the goal's "asset unparseable -> safe
fallback" requirement (goal section 4.2).
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


class KnowledgeStore:
    """Lazy, read-only access to extracted M-spec and DuckDB/MotherDuck knowledge."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or _DATA_DIR

    def _load(self, name: str) -> dict:
        path = self.data_dir / name
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Safe fallback: never let a corrupt cache break a conversion.
            return {}

    def m_spec(self) -> dict:
        """Extracted Power Query M language rules (functions, types, semantics)."""
        return self._load("m_spec.json")

    def duckdb_skills(self) -> dict:
        """Extracted DuckDB / MotherDuck conventions from the skills package."""
        return self._load("duckdb_skills.json")
