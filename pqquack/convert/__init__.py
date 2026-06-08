"""Conversion engine: deterministic rules first, Claude API fallback second.

Phase 3+ fills in the concept rules (``rules/``), connector isolation, pipeline
assembly, and per-target dialects (``targets/``). Phase 0 ships the fully
specified :mod:`pqquack.convert.types` type mapping.
"""

from pqquack.convert import types
from pqquack.convert.pipeline import (
    ConversionResult,
    convert_analysis,
    convert_query,
    convert_text,
)

__all__ = [
    "types",
    "ConversionResult",
    "convert_analysis",
    "convert_query",
    "convert_text",
]
