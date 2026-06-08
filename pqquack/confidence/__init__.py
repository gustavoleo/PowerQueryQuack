"""Confidence scoring (goal section 17).

Every conversion carries a justified confidence percentage with concrete reasons.
Low confidence triggers a request for additional information instead of a
confident-but-wrong answer.
"""

from pqquack.confidence.score import LOW_CONFIDENCE_THRESHOLD, ConfidenceScore, score

__all__ = ["LOW_CONFIDENCE_THRESHOLD", "ConfidenceScore", "score"]
