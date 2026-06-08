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

    # --- Convenience accessors (used by the convert/validate layers) ---------

    def access_libraries(self) -> set[str]:
        """M libraries that perform source acquisition (connector isolation, goal section 8)."""
        return set(self.m_spec().get("access_libraries", []))

    def is_access_function(self, qualified_name: str) -> bool:
        """True when ``Library.Function`` belongs to a source-acquisition library.

        Such functions must be isolated from transformation logic and never used
        as transformation guidance (goal section 8).
        """
        library = qualified_name.split(".", 1)[0]
        return library in self.access_libraries()

    def enumerations(self) -> dict[str, list[str]]:
        """M enumerations and their members (e.g. JoinKind.Inner)."""
        return self.m_spec().get("enumerations", {})

    def native_constructs(self) -> list[str]:
        """DuckDB-native constructs to prefer in generated SQL (goal section 13)."""
        return self.duckdb_skills().get("native_constructs", [])

    def native_readers(self) -> list[str]:
        """Native file readers in preference order (goal section 10)."""
        return self.duckdb_skills().get("native_readers", [])

    def skills(self) -> list[dict]:
        """The MotherDuck skill catalog (name + description)."""
        return self.duckdb_skills().get("skills", [])
