"""Validation engine (goal section 16).

Static checks plus optional live execution against an in-process DuckDB:
dependency resolution, circular references, unsupported functions, forbidden
constructs, column preservation, business-rule preservation, and target-runtime
compatibility. Failing validation prevents the SQL from being presented as
production-ready.
"""

from pqquack.validate.checks import CheckResult, CheckStatus
from pqquack.validate.engine import ValidationReport, validate

__all__ = ["CheckResult", "CheckStatus", "ValidationReport", "validate"]
