"""Shared enums used across the conversion pipeline.

Centralized here so every module (convert, validate, report, api, i18n) agrees on
the same vocabulary for languages, target runtimes, output modes, and review
status values defined in ``CODEX_GOAL.md``.
"""

from __future__ import annotations

from enum import StrEnum


class Language(StrEnum):
    """Supported user-facing languages (goal section 2). Fallback is en-US."""

    PT_BR = "pt-BR"
    EN_US = "en-US"

    @classmethod
    def default(cls) -> Language:
        return cls.EN_US


class TargetRuntime(StrEnum):
    """Supported SQL target runtimes (goal section 3). Default is duckdb."""

    DUCKDB = "duckdb"
    GIZMOSQL = "gizmosql"
    MOTHERDUCK = "motherduck"

    @classmethod
    def default(cls) -> TargetRuntime:
        return cls.DUCKDB


class OutputMode(StrEnum):
    """How the generated SQL is materialized (goal section 22).

    CTAS is only ever produced on explicit user request (goal section 9).
    """

    SELECT = "select"
    VIEW = "view"
    CTAS = "ctas"

    @classmethod
    def default(cls) -> OutputMode:
        return cls.SELECT


class ReviewStatus(StrEnum):
    """Conversion / human-review status (goal section 20)."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    NEEDS_HELP = "needs_help"
    HUMAN_REVIEW = "human_review"
