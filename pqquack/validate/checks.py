"""Individual validation checks (goal section 16).

Each check inspects the analysis + conversion and returns a :class:`CheckResult`
with a PASS / WARNING / FAIL / SKIP status. The engine aggregates them into a
report and decides whether the SQL may be called production-ready.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pqquack.convert.pipeline import ConversionResult
from pqquack.graph import AnalysisResult


class CheckStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    detail: str = ""


def check_dependency_graph(analysis: AnalysisResult) -> CheckResult:
    if not analysis.queries:
        return CheckResult("Dependency graph", CheckStatus.FAIL, "No queries parsed.")
    return CheckResult(
        "Dependency graph",
        CheckStatus.PASS,
        f"{len(analysis.queries)} queries resolved.",
    )


def check_circular_references(analysis: AnalysisResult) -> CheckResult:
    if analysis.has_cycle:
        chains = "; ".join(c.chain for c in analysis.cycles)
        return CheckResult("Circular references", CheckStatus.FAIL, chains)
    return CheckResult("Circular references", CheckStatus.PASS, "None found.")


def check_missing_references(analysis: AnalysisResult) -> CheckResult:
    missing = analysis.graph.missing_references
    if not missing:
        return CheckResult("Missing references", CheckStatus.PASS, "None found.")
    detail = "; ".join(f"{q}: {sorted(ids)}" for q, ids in missing.items())
    return CheckResult(
        "Missing references",
        CheckStatus.WARNING,
        f"Unresolved identifiers (may be parameters): {detail}",
    )


def check_unsupported_functions(conversion: ConversionResult) -> CheckResult:
    if not conversion.unsupported:
        return CheckResult("Unsupported functions", CheckStatus.PASS, "None.")
    return CheckResult(
        "Unsupported functions",
        CheckStatus.FAIL,
        "; ".join(conversion.unsupported),
    )


def check_forbidden_constructs(conversion: ConversionResult) -> CheckResult:
    bad = conversion.forbidden_constructs
    if not bad:
        return CheckResult(
            "Forbidden constructs (temp tables / procedural)",
            CheckStatus.PASS,
            "None — declarative SQL only.",
        )
    return CheckResult(
        "Forbidden constructs (temp tables / procedural)",
        CheckStatus.FAIL,
        f"Found: {bad}",
    )


def check_column_preservation(conversion: ConversionResult) -> CheckResult:
    if "<source" in conversion.sql:
        return CheckResult(
            "Column preservation",
            CheckStatus.WARNING,
            "Source schema unknown; verify columns against the real source.",
        )
    if not conversion.final_projection_explicit:
        return CheckResult(
            "Column preservation",
            CheckStatus.WARNING,
            "Final projection preserves an unknown schema (SELECT *).",
        )
    return CheckResult(
        "Column preservation",
        CheckStatus.PASS,
        "Explicit final projection.",
    )


def check_business_logic(conversion: ConversionResult) -> CheckResult:
    if conversion.unsupported:
        return CheckResult(
            "Business logic preservation",
            CheckStatus.FAIL,
            "Unsupported steps would drop business logic.",
        )
    if conversion.warnings:
        return CheckResult(
            "Business logic preservation",
            CheckStatus.WARNING,
            f"{len(conversion.warnings)} step(s) simplified — review.",
        )
    return CheckResult("Business logic preservation", CheckStatus.PASS, "Preserved.")


def check_target_compatibility(conversion: ConversionResult) -> CheckResult:
    markers = [n for n in conversion.notes if "only" in n.lower() or "guaranteed" in n.lower()]
    if markers:
        return CheckResult(
            "Target runtime compatibility",
            CheckStatus.WARNING,
            "; ".join(markers),
        )
    return CheckResult(
        "Target runtime compatibility",
        CheckStatus.PASS,
        f"No runtime-specific concerns for {conversion.target_runtime.value}.",
    )
