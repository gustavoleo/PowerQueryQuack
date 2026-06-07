"""Lightweight language detection with en-US fallback (goal section 2).

The MVP uses cheap heuristics (explicit override > simple keyword signal >
fallback). A heavier detector can replace this without changing the interface.
"""

from __future__ import annotations

from pqquack.enums import Language

# Common Portuguese signal words/characters. Deliberately small and deterministic
# to avoid any model call for language detection (goal section 23, cost control).
_PT_SIGNALS: tuple[str, ...] = (
    "ção",
    "não",
    "está",
    "código",
    "conversão",
    "coluna",
    "tabela",
    " e ",
    " de ",
    " para ",
    "ç",
    "ã",
    "õ",
)


def detect_language(text: str | None, override: Language | None = None) -> Language:
    """Detect the request language.

    Precedence: explicit ``override`` > Portuguese signal in ``text`` > en-US.
    """
    if override is not None:
        return override
    if not text:
        return Language.default()
    lowered = text.lower()
    if any(signal in lowered for signal in _PT_SIGNALS):
        return Language.PT_BR
    return Language.default()
