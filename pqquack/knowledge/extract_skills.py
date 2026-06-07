"""Extract a structured knowledge cache from ``agent-skills-main.zip``.

Dev-time only. Produces ``duckdb_skills.json`` consumed at runtime. Per goal
section 4.2 we inspect the package rather than assuming its contents, and fall
back safely (``available: False``) if it cannot be opened.

Captured:
- the MotherDuck skill catalog (name + description per skill), so the converter
  can cite relevant guidance without re-reading the package;
- DuckDB-native constructs worth preferring in generated SQL (goal sections 13-14);
- native file readers and their preference order (goal section 10).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

# DuckDB-native constructs the skills package recommends preferring. We record
# which are actually mentioned in the package so the converter only "prefers"
# documented features (goal section 13).
NATIVE_CONSTRUCT_CANDIDATES: tuple[str, ...] = (
    "GROUP BY ALL", "QUALIFY", "UNION BY NAME", "EXCLUDE", "REPLACE",
    "arg_max", "arg_min", "PIVOT", "UNPIVOT", "list_aggregate", "COLUMNS",
)

# Native readers, in the goal's preference order (section 10).
NATIVE_READERS: tuple[str, ...] = (
    "read_parquet", "read_json_auto", "read_csv_auto", "read_xlsx",
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_SKILLS_PREFIX = "agent-skills-main/skills/"


def _parse_frontmatter(md: str) -> dict[str, str]:
    """Parse the simple ``name:``/``description:`` YAML frontmatter of a SKILL.md."""
    match = _FRONTMATTER_RE.match(md)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            if key in {"name", "description", "license"}:
                fields[key] = value.strip()
    return fields


def _fallback(reason: str) -> dict:
    return {
        "source": "agent-skills-main.zip",
        "available": False,
        "reason": reason,
        "skills": [],
        "native_constructs": [],
        "native_readers": list(NATIVE_READERS),
        "skill_count": 0,
    }


def extract(zip_path: str | Path) -> dict:
    """Extract the DuckDB/MotherDuck knowledge cache from the skills zip."""
    path = Path(zip_path)
    if not path.exists():
        return _fallback(f"asset not found: {path}")

    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        return _fallback(f"could not open zip: {exc}")

    skills: list[dict[str, str]] = []
    duckdb_sql_text = ""
    with zf:
        names = zf.namelist()
        # Read each top-level skill's SKILL.md frontmatter.
        for name in names:
            if name.startswith(_SKILLS_PREFIX) and name.endswith("/SKILL.md"):
                # Canonical top-level copy is ``skills/<name>/SKILL.md`` (one slash).
                # Plugin duplicates live under ``plugins/.../skills/`` and don't
                # match _SKILLS_PREFIX, so this also guards against deeper nesting.
                rel = name[len(_SKILLS_PREFIX) :]
                if rel.count("/") != 1:
                    continue
                try:
                    md = zf.read(name).decode("utf-8", errors="replace")
                except KeyError:
                    continue
                fm = _parse_frontmatter(md)
                if fm.get("name"):
                    skills.append(
                        {"name": fm["name"], "description": fm.get("description", "")}
                    )
                if fm.get("name") == "motherduck-duckdb-sql":
                    duckdb_sql_text = md

    native_constructs = [
        c for c in NATIVE_CONSTRUCT_CANDIDATES if c.lower() in duckdb_sql_text.lower()
    ] or list(NATIVE_CONSTRUCT_CANDIDATES)

    skills.sort(key=lambda s: s["name"])
    return {
        "source": "agent-skills-main.zip",
        "available": True,
        "skills": skills,
        "native_constructs": native_constructs,
        "native_readers": list(NATIVE_READERS),
        "skill_count": len(skills),
    }
