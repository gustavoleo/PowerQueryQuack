"""Confidence scoring with concrete reasons (goal section 17).

Every conversion carries a justified confidence percentage. Low confidence
triggers a request for additional information instead of a confident-but-wrong
answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pqquack.convert.pipeline import ConversionResult
from pqquack.graph import AnalysisResult

# Below this, the engine asks the user for more information (goal section 17).
LOW_CONFIDENCE_THRESHOLD = 70.0


@dataclass
class ConfidenceScore:
    percent: float
    reasons: list[str] = field(default_factory=list)
    needs_more_info: bool = False

    def render(self) -> str:
        lines = [f"Translation Confidence: {self.percent:.1f}%", "", "Reasons:"]
        lines.extend(f"- {r}" for r in self.reasons)
        if self.needs_more_info:
            lines.append("")
            lines.append(
                "Confidence is low — please provide sample data, the source schema, "
                "or clarify the flagged steps so the conversion can be improved."
            )
        return "\n".join(lines)


def score(analysis: AnalysisResult, conversion: ConversionResult) -> ConfidenceScore:
    """Compute a confidence score and the reasons behind it."""
    reasons: list[str] = []

    if analysis.has_cycle:
        return ConfidenceScore(
            percent=5.0,
            reasons=["Circular references must be resolved before SQL generation."],
            needs_more_info=True,
        )

    percent = 100.0

    if conversion.unsupported:
        penalty = min(60.0, 15.0 * len(conversion.unsupported))
        percent -= penalty
        n_unsupported = len(conversion.unsupported)
        reasons.append(f"{n_unsupported} unsupported step(s) flagged (-{penalty:.0f}).")
    else:
        reasons.append("All steps mapped by deterministic rules.")

    if "<source" in conversion.sql:
        percent -= 20.0
        reasons.append("Data source could not be fully determined (-20).")

    missing = analysis.graph.missing_references
    if missing:
        penalty = min(20.0, 5.0 * len(missing))
        percent -= penalty
        n_missing = len(missing)
        reasons.append(f"{n_missing} query/queries with unresolved identifiers (-{penalty:.0f}).")
    else:
        reasons.append("No missing references.")

    if conversion.warnings:
        penalty = min(15.0, 3.0 * len(conversion.warnings))
        percent -= penalty
        n_warn = len(conversion.warnings)
        reasons.append(f"{n_warn} step(s) simplified, e.g. joins (-{penalty:.0f}).")

    if not analysis.has_cycle:
        reasons.append("No circular references found.")

    percent = max(0.0, min(100.0, percent))
    return ConfidenceScore(
        percent=percent,
        reasons=reasons,
        needs_more_info=percent < LOW_CONFIDENCE_THRESHOLD,
    )
