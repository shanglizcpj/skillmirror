"""Deterministic, explainable and correlation-aware Skill Score Engine (A3)."""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional
import json
import math

from .evidence import load_rules
from .provenance import verify_evidence
from .schema_validation import validate_payload

ALGORITHM_VERSION = "skill-score/2.1.0"
CONFIG = {
    "strength_weight": {"weak": 0.10, "medium": 0.20, "strong": 0.30},
    "difficulty_multiplier": {"easy": 0.85, "medium": 1.00, "hard": 1.15, "expert": 1.30},
    "hint_multiplier": {"none": 1.00, "level_1": 0.95, "level_2": 0.85, "level_3": 0.70, "direct_help": 0.50},
    "max_weight_per_session": 0.40,
    "max_total_update_weight": 0.60,
}
# Neutral and dependency events remain traceable context but must not move the
# ability estimate. This preserves the AB rule that a first failed fix is not a
# direct penalty.
SCORE_DIRECTIONS = {"positive", "negative"}


def _finite(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _hint_level(value: Any) -> str:
    key = str(value or "none").lower().strip()
    return key if key in CONFIG["hint_multiplier"] else "none"


def _adjust_for_independence(raw_score: float, hint_level: str) -> float:
    multiplier = CONFIG["hint_multiplier"][hint_level]
    return 50.0 + (raw_score - 50.0) * multiplier


def _evidence_weight(item: Dict[str, Any]) -> float:
    strength = str(item.get("strength", "")).lower()
    difficulty = str(item.get("difficulty", "")).lower()
    if strength not in CONFIG["strength_weight"]:
        raise ValueError(f"invalid evidence strength: {strength}")
    if difficulty not in CONFIG["difficulty_multiplier"]:
        raise ValueError(f"invalid challenge difficulty: {difficulty}")
    reliability = _finite(item.get("reliability", 1.0), "reliability")
    if not 0 <= reliability <= 1:
        raise ValueError("reliability must be within [0,1]")
    return CONFIG["strength_weight"][strength] * CONFIG["difficulty_multiplier"][difficulty] * reliability


def _calculation_id(previous_score: Optional[float], skill_id: Optional[str], evidence_ids: Iterable[str]) -> str:
    raw = json.dumps(
        {"algorithm": ALGORITHM_VERSION, "previous": previous_score, "skill": skill_id, "evidence": sorted(evidence_ids)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "SC-" + sha256(raw.encode("utf-8")).hexdigest()[:16]


def calculate_skill_update(
    previous_score: Optional[float],
    evidence: List[Dict[str, Any]],
    *,
    skill_id: Optional[str] = None,
    evidence_secret: str | bytes,
) -> Dict[str, Any]:
    """Update one skill from A-signed Evidence Engine output only."""
    previous = None if previous_score is None else _clamp(_finite(previous_score, "previous_score"))
    included: List[Dict[str, Any]] = []
    excluded: List[Dict[str, str]] = []
    seen_ids = set()
    expected_rule_version = load_rules()["version"]
    trusted: List[Dict[str, Any]] = []
    for item in evidence:
        evidence_id = str(item.get("evidence_id") or "") if isinstance(item, dict) else ""
        try:
            validate_payload(item, "evidence.schema.json")
        except (TypeError, ValueError):
            excluded.append({"evidence_id": evidence_id, "reason": "invalid_trusted_evidence_schema"})
            continue
        if item.get("rule_version") != expected_rule_version:
            excluded.append({"evidence_id": evidence_id, "reason": "unsupported_rule_version"})
            continue
        if not verify_evidence(item, evidence_secret):
            excluded.append({"evidence_id": evidence_id, "reason": "invalid_evidence_provenance"})
            continue
        trusted.append(item)
    inferred_skills = {
        str(item.get("skill")) for item in trusted
        if item.get("direction") in SCORE_DIRECTIONS and item.get("performance_score") is not None and item.get("skill")
    }
    target = skill_id or (next(iter(inferred_skills)) if len(inferred_skills) == 1 else None)
    if skill_id is None and len(inferred_skills) > 1:
        raise ValueError("skill_id is required when evidence spans multiple skills")

    for item in trusted:
        evidence_id = str(item.get("evidence_id") or "")
        if not evidence_id:
            excluded.append({"evidence_id": "", "reason": "missing_evidence_id"})
            continue
        if evidence_id in seen_ids:
            excluded.append({"evidence_id": evidence_id, "reason": "duplicate_evidence_id"})
            continue
        seen_ids.add(evidence_id)
        if item.get("skill") != target:
            excluded.append({"evidence_id": evidence_id, "reason": "different_skill"})
            continue
        if item.get("direction") not in SCORE_DIRECTIONS or item.get("performance_score") is None:
            excluded.append({"evidence_id": evidence_id, "reason": "non_score_bearing_direction"})
            continue
        raw = _clamp(_finite(item["performance_score"], "performance_score"))
        hint = _hint_level(item.get("hint_level"))
        weight = _evidence_weight(item)
        included.append({
            **item,
            "_raw": raw,
            "_hint": hint,
            "_adjusted": _adjust_for_independence(raw, hint),
            "_weight": weight,
            "_session": str(item.get("session_id") or item.get("challenge_id") or evidence_id),
        })

    if not included:
        return {
            "algorithm_version": ALGORITHM_VERSION,
            "calculation_id": _calculation_id(previous, target, []),
            "skill_id": target,
            "previous_score": previous,
            "new_score": previous,
            "score_status": "unknown" if previous is None else "unchanged",
            "evidence_weight": 0.0,
            "evidence_score": None,
            "formula": "no score-bearing verified evidence",
            "reason": "No verified score-bearing evidence; score remains Unknown." if previous is None else "No verified score-bearing evidence; score unchanged.",
            "session_breakdown": [],
            "excluded_evidence": excluded,
        }

    sessions: Dict[str, List[Dict[str, Any]]] = {}
    for item in included:
        sessions.setdefault(item["_session"], []).append(item)

    session_breakdown = []
    weighted_score_sum = 0.0
    session_weight_sum = 0.0
    for session_id, items in sorted(sessions.items()):
        raw_weight = sum(item["_weight"] for item in items)
        session_score = sum(item["_adjusted"] * item["_weight"] for item in items) / raw_weight
        session_weight = min(raw_weight, CONFIG["max_weight_per_session"])
        weighted_score_sum += session_score * session_weight
        session_weight_sum += session_weight
        session_breakdown.append({
            "session_id": session_id,
            "session_score": round(session_score, 2),
            "raw_weight": round(raw_weight, 4),
            "capped_weight": round(session_weight, 4),
            "correlation_cap_applied": raw_weight > session_weight,
            "evidence": [
                {
                    "evidence_id": item["evidence_id"],
                    "raw_performance_score": round(item["_raw"], 2),
                    "hint_level": item["_hint"],
                    "hint_multiplier": CONFIG["hint_multiplier"][item["_hint"]],
                    "adjusted_performance_score": round(item["_adjusted"], 2),
                    "strength": item["strength"],
                    "difficulty": item["difficulty"],
                    "reliability": item.get("reliability", 1.0),
                    "raw_weight": round(item["_weight"], 4),
                    "reason": item.get("reason", ""),
                }
                for item in items
            ],
        })

    evidence_score = weighted_score_sum / session_weight_sum
    update_weight = min(session_weight_sum, CONFIG["max_total_update_weight"])
    if previous is None:
        new_score = evidence_score
        status = "provisional"
        formula = "cold_start_score = weighted_session_evidence_score"
        reason = f"Cold start from {len(sessions)} independent verified session(s); provisional evidence score {evidence_score:.1f}."
    else:
        new_score = previous * (1.0 - update_weight) + evidence_score * update_weight
        status = "updated"
        formula = "new_score = previous_score*(1-alpha) + evidence_score*alpha"
        reason = f"Previous {previous:.1f} blended with evidence score {evidence_score:.1f}; alpha={update_weight:.3f}."

    return {
        "algorithm_version": ALGORITHM_VERSION,
        "calculation_id": _calculation_id(previous, target, [item["evidence_id"] for item in included]),
        "skill_id": target,
        "previous_score": previous,
        "new_score": round(_clamp(new_score), 2),
        "score_status": status,
        "evidence_weight": round(update_weight, 4),
        "evidence_score": round(evidence_score, 2),
        "formula": formula,
        "reason": reason,
        "session_breakdown": session_breakdown,
        "excluded_evidence": excluded,
    }
