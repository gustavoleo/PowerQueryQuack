"""Human-review record schema (goal section 20).

Mirrors the suggested JSON record exactly so failed/uncertain conversions can be
exported for human supervision and re-tested after correction.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from pqquack.enums import Language, ReviewStatus, TargetRuntime


class ReviewRecord(BaseModel):
    """A single conversion's review record, anonymized by default (goal section 19)."""

    conversion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    language: Language = Language.EN_US
    target_runtime: TargetRuntime = TargetRuntime.DUCKDB
    status: ReviewStatus = ReviewStatus.HUMAN_REVIEW
    original_power_query_summary: str = ""
    generated_sql_summary: str = ""
    error_message: str | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    human_supervisor_notes: str | None = None
    approved_by_human: bool = False
