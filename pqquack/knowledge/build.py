"""Regenerate the committed knowledge cache from the repo assets.

Run from the repo root:

    python -m pqquack.knowledge.build

Writes ``pqquack/knowledge/data/m_spec.json`` and ``duckdb_skills.json`` from
``PowerQueryLanguageSpecification.pdf`` and ``agent-skills-main.zip``. Safe to
re-run; output is deterministic. The generated JSON is committed so nothing is
parsed at request time (goal section 23).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pqquack.knowledge import extract_skills, extract_spec

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = Path(__file__).parent / "data"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build(
    pdf_path: Path | None = None,
    zip_path: Path | None = None,
    data_dir: Path | None = None,
) -> dict[str, dict]:
    """Extract both caches and write them. Returns the two payloads."""
    pdf_path = pdf_path or _REPO_ROOT / "PowerQueryLanguageSpecification.pdf"
    zip_path = zip_path or _REPO_ROOT / "agent-skills-main.zip"
    data_dir = data_dir or _DATA_DIR

    m_spec = extract_spec.extract(pdf_path)
    duckdb_skills = extract_skills.extract(zip_path)

    _write_json(data_dir / "m_spec.json", m_spec)
    _write_json(data_dir / "duckdb_skills.json", duckdb_skills)
    return {"m_spec": m_spec, "duckdb_skills": duckdb_skills}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Power Query Quack knowledge cache.")
    parser.add_argument("--pdf", type=Path, default=None, help="Path to the M spec PDF.")
    parser.add_argument("--zip", type=Path, default=None, help="Path to the skills zip.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Output data directory.")
    args = parser.parse_args(argv)

    payloads = build(args.pdf, args.zip, args.data_dir)
    m_spec, skills = payloads["m_spec"], payloads["duckdb_skills"]
    print(
        f"m_spec: available={m_spec['available']} "
        f"libraries={len(m_spec['libraries'])} functions={m_spec['function_count']}"
    )
    print(
        f"duckdb_skills: available={skills['available']} "
        f"skills={skills['skill_count']} constructs={len(skills['native_constructs'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
