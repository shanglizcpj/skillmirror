"""Adaptive Challenge Strategy (A9)."""
from __future__ import annotations
from typing import Any, Dict, Optional
import math

CONFIG = {
    # Project-extension thresholds; intentionally centralized for later calibration.
    "low_score": 60.0,
    "high_score": 80.0,
    "high_confidence": 0.75,
    "very_high_confidence": 0.90,
}


def choose_policy(score: Optional[float], confidence: float) -> Dict[str, str]:
    """Map Score + Confidence to the four policies specified in AB分工.docx."""
    try:
        c = float(confidence or 0.0)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be numeric") from exc
    if not math.isfinite(c) or not 0.0 <= c <= 1.0:
        raise ValueError("confidence must be within [0,1]")
    if score is None:
        return {"mode": "diagnostic", "difficulty": "easy", "reason": "Skill score is Unknown; collect baseline evidence first."}

    try:
        s = float(score)
    except (TypeError, ValueError) as exc:
        raise ValueError("score must be numeric or null") from exc
    if not math.isfinite(s) or not 0.0 <= s <= 100.0:
        raise ValueError("score must be within [0,100]")
    if s < CONFIG["low_score"] and c >= CONFIG["high_confidence"]:
        return {"mode": "teaching", "difficulty": "easy", "reason": "Low score with high confidence: use a teaching-oriented challenge."}
    if s >= CONFIG["high_score"] and c < CONFIG["high_confidence"]:
        return {"mode": "verification", "difficulty": "medium", "reason": "High score with low confidence: verify with additional evidence."}
    if s >= CONFIG["high_score"] and c >= CONFIG["high_confidence"]:
        diff = "expert" if c >= CONFIG["very_high_confidence"] else "hard"
        return {"mode": "stretch", "difficulty": diff, "reason": "High score with high confidence: increase challenge difficulty."}
    if s < CONFIG["low_score"] and c < CONFIG["high_confidence"]:
        return {"mode": "diagnostic", "difficulty": "easy", "reason": "Low score with low confidence: run a basic diagnostic challenge."}
    return {"mode": "development", "difficulty": "medium", "reason": "Mid-range evidence: continue balanced skill development."}
