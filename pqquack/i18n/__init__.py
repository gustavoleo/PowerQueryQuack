"""Bilingual message catalogs and language handling (goal section 2).

All user-facing UI text, validation messages, and feedback prompts must be
available in pt-BR and en-US, with en-US as the fallback.
"""

from pqquack.i18n.catalog import CATALOGS, t
from pqquack.i18n.detect import detect_language

__all__ = ["CATALOGS", "t", "detect_language"]
