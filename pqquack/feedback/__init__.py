"""Feedback capture and human-supervisor review records (goal sections 19-20).

Phase 7 adds persistence; Phase 0 ships the review-record schema so the rest of
the pipeline can produce well-typed records from day one.
"""

from pqquack.feedback.records import ReviewRecord

__all__ = ["ReviewRecord"]
