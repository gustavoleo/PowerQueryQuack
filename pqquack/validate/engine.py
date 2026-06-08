"""Validation engine: aggregate checks into a report (goal section 16).

Runs the static checks and, when sample relations are supplied, a live DuckDB
execution check. Decides whether the SQL may be presented as production-ready —
it may not if any check FAILs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pqquack.convert.pipeline import ConversionResult
from pqquack.graph import AnalysisResult
from pqquack.validate import checks
from pqquack.validate.checks import CheckResult, CheckStatus


@dataclass
class ValidationReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def overall(self) -> CheckStatus:
        statuses = {r.status for r in self.results}
        if CheckStatus.FAIL in statuses:
            return CheckStatus.FAIL
        if CheckStatus.WARNING in statuses:
            return CheckStatus.WARNING
        return CheckStatus.PASS

    @property
    def production_ready(self) -> bool:
        """Production-ready only when no check failed (goal section 16)."""
        return self.overall is not CheckStatus.FAIL

    def render(self) -> str:
        lines = ["Validation Report", ""]
        for r in self.results:
            suffix = f" — {r.detail}" if r.detail else ""
            lines.append(f"{r.name}: {r.status.value}{suffix}")
        lines.append("")
        lines.append(f"Overall: {self.overall.value}")
        return "\n".join(lines)


def _live_execution_check(
    sql: str, relations: Mapping[str, Any] | None
) -> CheckResult:
    """Run the SQL against in-process DuckDB using sample relations.

    ``relations`` maps a relation name to a SQL SELECT that defines its rows, e.g.
    ``{"orders": "SELECT 1 AS id, 150 AS amount"}``. Each becomes a base table so
    the generated SQL can bind and execute.
    """
    if not relations:
        return CheckResult(
            "Live execution (DuckDB)",
            CheckStatus.SKIP,
            "No sample data supplied.",
        )
    try:
        import duckdb
    except Exception:  # pragma: no cover - duckdb is a core dep
        return CheckResult("Live execution (DuckDB)", CheckStatus.SKIP, "duckdb unavailable.")
    try:
        con = duckdb.connect()
        for name, definition in relations.items():
            con.execute(f'CREATE OR REPLACE TABLE "{name}" AS {definition}')
        con.execute(sql).fetchall()
    except Exception as exc:  # noqa: BLE001 - surface any execution error to the report
        return CheckResult("Live execution (DuckDB)", CheckStatus.FAIL, str(exc))
    return CheckResult("Live execution (DuckDB)", CheckStatus.PASS, "Executed successfully.")


def validate(
    analysis: AnalysisResult,
    conversion: ConversionResult,
    sample_relations: Mapping[str, Any] | None = None,
) -> ValidationReport:
    """Produce a validation report for a conversion (goal section 16)."""
    results = [
        checks.check_dependency_graph(analysis),
        checks.check_circular_references(analysis),
        checks.check_missing_references(analysis),
        checks.check_unsupported_functions(conversion),
        checks.check_forbidden_constructs(conversion),
        checks.check_column_preservation(conversion),
        checks.check_business_logic(conversion),
        checks.check_target_compatibility(conversion),
        _live_execution_check(conversion.sql, sample_relations),
    ]
    return ValidationReport(results=results)
