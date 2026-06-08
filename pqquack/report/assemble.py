"""Assemble the 10-section conversion output (goal section 18).

Combines the dependency analysis, generated SQL, validation report, and
confidence score into the fixed 10-section structure every conversion response
uses, localized to the requested language.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pqquack.confidence import ConfidenceScore, score
from pqquack.convert import ConversionResult, convert_analysis, convert_query
from pqquack.enums import Language, TargetRuntime
from pqquack.graph import AnalysisResult, analyze
from pqquack.i18n import t
from pqquack.knowledge import KnowledgeStore
from pqquack.validate import ValidationReport, validate

RUNTIME_LABEL = {
    TargetRuntime.DUCKDB: "DuckDB",
    TargetRuntime.GIZMOSQL: "GizmoSQL",
    TargetRuntime.MOTHERDUCK: "MotherDuck",
}


@dataclass
class Report:
    """A fully assembled conversion report."""

    sections: list[tuple[str, str]] = field(default_factory=list)
    conversion: ConversionResult | None = None
    validation: ValidationReport | None = None
    confidence: ConfidenceScore | None = None

    @property
    def production_ready(self) -> bool:
        return bool(self.validation and self.validation.production_ready)

    def render(self) -> str:
        out: list[str] = []
        for idx, (title, body) in enumerate(self.sections, start=1):
            out.append(f"## {idx}. {title}")
            out.append("")
            out.append(body.strip() or "—")
            out.append("")
        return "\n".join(out).strip() + "\n"

    def to_dict(self) -> dict:
        """Structured form for the API / web UI."""
        return {
            "sections": [{"title": title, "body": body} for title, body in self.sections],
            "markdown": self.render(),
            "sql": self.conversion.sql if self.conversion else "",
            "production_ready": self.production_ready,
            "validation_overall": self.validation.overall.value if self.validation else None,
            "confidence_percent": self.confidence.percent if self.confidence else None,
            "needs_more_info": bool(self.confidence and self.confidence.needs_more_info),
            "unsupported": list(self.conversion.unsupported) if self.conversion else [],
        }


def _feedback_block(language: Language) -> str:
    return (
        f"{t('feedback.question', language)}\n\n"
        f"👍 {t('feedback.correct', language)}\n"
        f"👎 {t('feedback.incorrect', language)}\n"
        f"🛠 {t('feedback.help_me_fix_it', language)}"
    )


def build_report(
    analysis: AnalysisResult,
    conversion: ConversionResult,
    validation: ValidationReport,
    confidence: ConfidenceScore,
    language: Language = Language.EN_US,
    output_name: str | None = None,
    target_specified: bool = True,
) -> Report:
    """Build the 10-section :class:`Report` (goal section 18)."""
    runtime = conversion.target_runtime
    runtime_label = (
        RUNTIME_LABEL[runtime] if target_specified else t("report.not_specified_runtime", language)
    )

    n = len(analysis.queries)
    ready = (
        "production-ready"
        if validation.production_ready
        else "NOT production-ready (validation failed)"
    )
    summary = (
        f"Converted {n} Power Query definition(s)"
        + (f"; final output: '{output_name}'." if output_name else ".")
        + f" Result is {ready}."
    )
    none_label = t("report.none", language)
    graph_text = analysis.graph.render_ascii() or none_label

    circular = (
        t("report.no_circular", language)
        if not analysis.has_cycle
        else "\n".join(
            f"{c.chain}\nRoot cause: {c.root_cause}\nResolution: {c.resolution}"
            for c in analysis.cycles
        )
    )

    notes_lines = [f"- {note}" for note in conversion.notes]
    notes_lines += [f"- ⚠️ {w}" for w in conversion.warnings]
    notes_lines += [f"- ⛔ {u}" for u in conversion.unsupported]
    conversion_notes = "\n".join(notes_lines) or none_label

    markers = [
        note for note in conversion.notes
        if "only" in note.lower() or "guaranteed" in note.lower()
    ]
    compatibility = "\n".join(f"- {m}" for m in markers) or none_label
    sql_block = f"```sql\n{conversion.sql}\n```"

    sections = [
        (t("report.executive_summary", language), summary),
        (t("report.detected_target_runtime", language), runtime_label),
        (t("report.dependency_graph", language), graph_text),
        (t("report.circular_reference_report", language), circular),
        (t("report.conversion_notes", language), conversion_notes),
        (t("report.generated_sql", language), sql_block),
        (t("report.validation_report", language), validation.render()),
        (t("report.compatibility_notes", language), compatibility),
        (t("report.confidence_score", language), confidence.render()),
        (t("report.feedback_request", language), _feedback_block(language)),
    ]
    return Report(
        sections=sections,
        conversion=conversion,
        validation=validation,
        confidence=confidence,
    )


def convert_and_report(
    text: str,
    target_runtime: TargetRuntime = TargetRuntime.DUCKDB,
    language: Language = Language.EN_US,
    target_specified: bool = True,
    sample_relations=None,
    store: KnowledgeStore | None = None,
) -> Report:
    """Full pipeline: analyze → convert → validate → score → assemble the report."""
    analysis = analyze(text, store=store)
    output_name = analysis.graph.outputs()[0] if analysis.graph.outputs() else None

    if len(analysis.queries) == 1 and not analysis.has_cycle:
        conversion = convert_query(analysis.queries[0], target_runtime, store)
        output_name = analysis.queries[0].name
    else:
        conversion = convert_analysis(analysis, target_runtime, store)

    validation = validate(analysis, conversion, sample_relations)
    confidence = score(analysis, conversion)
    return build_report(
        analysis,
        conversion,
        validation,
        confidence,
        language=language,
        output_name=output_name,
        target_specified=target_specified,
    )
