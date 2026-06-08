"""Output report assembly (goal section 18).

Every conversion response uses the same 10-section structure. The ordered section
keys live here so the assembler (Phase 4) and the web UI render them
consistently and in both languages.
"""

from __future__ import annotations

# Ordered i18n keys for the 10-section conversion output (goal section 18).
SECTION_KEYS: tuple[str, ...] = (
    "report.executive_summary",
    "report.detected_target_runtime",
    "report.dependency_graph",
    "report.circular_reference_report",
    "report.conversion_notes",
    "report.generated_sql",
    "report.validation_report",
    "report.compatibility_notes",
    "report.confidence_score",
    "report.feedback_request",
)

__all__ = ["SECTION_KEYS"]
