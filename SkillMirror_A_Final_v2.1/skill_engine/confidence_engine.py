"""Independent-session Confidence Engine (A4)."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import math
import statistics

from .evidence import load_rules
from .provenance import verify_evidence
from .schema_validation import validate_payload

ALGORITHM_VERSION = "skill-confidence/2.1.0"
CONFIG = {
    "factor_weights": {"quantity": 0.30, "strength": 0.20, "freshness": 0.20, "diversity": 0.15, "consistency": 0.15},
    "strength_value": {"weak": 0.25, "medium": 0.60, "strong": 1.00},
    "freshness_half_life_days": 30.0,
    "quantity_scale_sessions": 3.0,
    "diversity_target": 4,
    "single_session_consistency": 0.35,
}
SCORE_DIRECTIONS = {"positive", "negative"}


def _parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _status(confidence: float) -> str:
    if confidence < 0.45:
        return "low"
    if confidence < 0.75:
        return "medium"
    return "high"


def calculate_confidence(
    evidence: List[Dict[str, Any]],
    *,
    skill_id: Optional[str] = None,
    now: Optional[datetime] = None,
    evidence_secret: str | bytes,
) -> Dict[str, Any]:
    """Estimate certainty from independent A-signed Evidence only."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    seen = set()
    usable = []
    warnings: List[str] = []
    expected_rule_version = load_rules()["version"]
    for item in evidence:
        evidence_id = item.get("evidence_id") if isinstance(item, dict) else None
        try:
            validate_payload(item, "evidence.schema.json")
        except (TypeError, ValueError):
            warnings.append(f"invalid trusted evidence schema ignored: {evidence_id or 'unknown'}")
            continue
        if item.get("rule_version") != expected_rule_version:
            warnings.append(f"unsupported evidence rule version ignored: {evidence_id}")
            continue
        if not verify_evidence(item, evidence_secret):
            warnings.append(f"invalid evidence provenance ignored: {evidence_id}")
            continue
        if not evidence_id or evidence_id in seen:
            if evidence_id in seen:
                warnings.append(f"duplicate evidence ignored: {evidence_id}")
            continue
        seen.add(evidence_id)
        if skill_id is not None and item.get("skill") != skill_id:
            continue
        if item.get("direction") not in SCORE_DIRECTIONS or item.get("performance_score") is None:
            continue
        try:
            score = float(item["performance_score"])
        except (TypeError, ValueError):
            warnings.append(f"invalid performance score ignored: {evidence_id}")
            continue
        if not math.isfinite(score) or not 0 <= score <= 100:
            warnings.append(f"out-of-range performance score ignored: {evidence_id}")
            continue
        usable.append({**item, "_score": score, "_session": str(item.get("session_id") or item.get("challenge_id") or evidence_id)})

    if not usable:
        return {
            "algorithm_version": ALGORITHM_VERSION,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "confidence_status": "low",
            "formula": "confidence = 0 when no independent verified evidence exists",
            "reason": "No verified score-bearing evidence. Confidence = 0.",
            "factors": {key: 0.0 for key in CONFIG["factor_weights"]},
            "counts": {"evidence_items": 0, "independent_sessions": 0, "challenge_contexts": 0},
            "warnings": sorted(set(warnings)),
        }

    sessions: Dict[str, List[Dict[str, Any]]] = {}
    for item in usable:
        sessions.setdefault(item["_session"], []).append(item)
    session_scores = []
    session_strengths = []
    session_freshness = []
    contexts = set()
    for session_id, items in sessions.items():
        reliabilities = [max(0.0, min(1.0, float(item.get("reliability", 1.0)))) for item in items]
        denom = sum(reliabilities) or 1.0
        session_scores.append(sum(item["_score"] * rel for item, rel in zip(items, reliabilities)) / denom)
        session_strengths.append(max(CONFIG["strength_value"].get(str(item.get("strength", "weak")).lower(), 0.25) for item in items))
        contexts.add((str(items[0].get("challenge_type", "unknown")), str(items[0].get("difficulty", "unknown"))))
        parsed_times = [_parse_time(item.get("timestamp")) for item in items]
        valid_times = [value.astimezone(timezone.utc) for value in parsed_times if value is not None]
        if not valid_times:
            warnings.append(f"session {session_id} has no valid timestamp")
            session_freshness.append(0.0)
        else:
            latest = max(valid_times)
            if latest > current.astimezone(timezone.utc) + timedelta(minutes=5):
                warnings.append(f"session {session_id} has a future timestamp")
                session_freshness.append(0.0)
            else:
                age_days = max(0.0, (current.astimezone(timezone.utc) - latest).total_seconds() / 86400.0)
                session_freshness.append(0.5 ** (age_days / CONFIG["freshness_half_life_days"]))

    independent_sessions = len(sessions)
    quantity = 1.0 - math.exp(-independent_sessions / CONFIG["quantity_scale_sessions"])
    strength = sum(session_strengths) / independent_sessions
    freshness = sum(session_freshness) / independent_sessions
    diversity = min(1.0, len(contexts) / CONFIG["diversity_target"])
    if independent_sessions == 1:
        consistency = CONFIG["single_session_consistency"]
    else:
        consistency = max(0.0, min(1.0, 1.0 - statistics.pstdev(session_scores) / 25.0))
    factors = {
        "quantity": quantity,
        "strength": strength,
        "freshness": freshness,
        "diversity": diversity,
        "consistency": consistency,
    }
    base = sum(factors[key] * weight for key, weight in CONFIG["factor_weights"].items())
    independence_gate = 0.30 + 0.70 * quantity
    confidence = max(0.0, min(1.0, base * independence_gate))
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "confidence": round(confidence, 4),
        "confidence_percent": round(confidence * 100, 1),
        "confidence_status": _status(confidence),
        "formula": "confidence = weighted_five_factors * (0.30 + 0.70*independent_session_quantity)",
        "reason": f"Calculated from {independent_sessions} independent verified session(s); multiple events in one session do not inflate quantity.",
        "factors": {key: round(value, 4) for key, value in factors.items()},
        "counts": {
            "evidence_items": len(usable),
            "independent_sessions": independent_sessions,
            "challenge_contexts": len(contexts),
        },
        "warnings": sorted(set(warnings)),
    }
