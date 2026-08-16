"""Examiner Agent (A5): information-gain target selection with repeat control."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import math

from agents.common import render_prompt, safe_llm_json
from skill_engine.adaptive import choose_policy
from skill_engine.skill_tree import get_subskills, load_skill_tree

SKILL_TO_CHALLENGE_TYPE = {
    "coding": "implementation",
    "debugging": "debugging_runtime",
    "testing": "testing_edge_cases",
    "problem_solving": "problem_decomposition",
    "code_reading": "code_trace",
}


def _bounded(value: Any, low: float, high: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{name} must be within [{low},{high}]")
    return number


def _normalize_skills(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    known = {item["id"] for item in load_skill_tree()["root_skill"]["children"]}
    normalized = []
    seen = set()
    for item in items:
        skill_id = item.get("skill_id") or item.get("id")
        if skill_id not in known or skill_id in seen:
            raise ValueError(f"unknown or duplicate skill_id: {skill_id}")
        seen.add(skill_id)
        score = item.get("score")
        normalized.append({
            "skill_id": skill_id,
            "score": None if score is None else _bounded(score, 0, 100, "score"),
            "confidence": _bounded(item.get("confidence", 0.0) or 0.0, 0, 1, "confidence"),
            "subskills": item.get("subskills", []),
        })
    if not normalized:
        raise ValueError("skill_mirror.skills must not be empty")
    return normalized


def _recent_penalty(skill_id: str, previous: List[Dict[str, Any]]) -> float:
    targets = [item.get("target_skill") for item in previous[-3:]]
    penalty = 0.0
    for index, target in enumerate(reversed(targets)):
        if target == skill_id:
            penalty += (0.30, 0.15, 0.08)[index]
    return min(0.45, penalty)


def _priority(item: Dict[str, Any], previous: List[Dict[str, Any]], evidence_count: int) -> Dict[str, Any]:
    unknown_bonus = 0.30 if item["score"] is None else 0.0
    confidence_gap = 1.0 - item["confidence"]
    weakness_bonus = 0.12 if item["score"] is not None and item["score"] < 60 else 0.0
    no_evidence_bonus = 0.08 if evidence_count == 0 else 0.0
    repeat_penalty = _recent_penalty(item["skill_id"], previous)
    value = 0.55 * confidence_gap + unknown_bonus + weakness_bonus + no_evidence_bonus - repeat_penalty
    return {
        "priority": round(value, 4),
        "confidence_gap": round(confidence_gap, 4),
        "unknown_bonus": unknown_bonus,
        "weakness_bonus": weakness_bonus,
        "no_evidence_bonus": no_evidence_bonus,
        "recent_repeat_penalty": repeat_penalty,
        "evidence_count": evidence_count,
    }


def _select_subskill(target: Dict[str, Any]) -> Optional[str]:
    allowed = get_subskills(target["skill_id"])
    supplied = target.get("subskills") or []
    if not supplied:
        return allowed[0] if allowed else None
    candidates = []
    for sub in supplied:
        sub_id = sub.get("sub_skill_id") or sub.get("id")
        if sub_id not in allowed:
            continue
        score = sub.get("score")
        confidence = _bounded(sub.get("confidence", 0.0) or 0.0, 0, 1, "subskill confidence")
        candidates.append((0 if score is None else 1, confidence, sub_id))
    return min(candidates)[2] if candidates else (allowed[0] if allowed else None)


def examine(
    skill_mirror: Dict[str, Any],
    evidence_history: Optional[List[Dict[str, Any]]] = None,
    previous_challenges: Optional[List[Dict[str, Any]]] = None,
    llm=None,
    *,
    llm_timeout_seconds: float = 8.0,
) -> Dict[str, Any]:
    skills = _normalize_skills(skill_mirror.get("skills", []))
    history = evidence_history or []
    previous = previous_challenges or []
    counts = {
        item["skill_id"]: len({ev.get("session_id") or ev.get("challenge_id") for ev in history if ev.get("skill") == item["skill_id"]})
        for item in skills
    }
    breakdown = {item["skill_id"]: _priority(item, previous, counts[item["skill_id"]]) for item in skills}
    target = max(skills, key=lambda item: (breakdown[item["skill_id"]]["priority"], -item["confidence"], item["skill_id"]))
    policy = choose_policy(target.get("score"), target["confidence"])
    subskill = _select_subskill(target)
    result = {
        "target_skill": target["skill_id"],
        "target_subskill": subskill,
        "difficulty": policy["difficulty"],
        "challenge_type": SKILL_TO_CHALLENGE_TYPE[target["skill_id"]],
        "mode": policy["mode"],
        "reason": f"{policy['reason']} {target['skill_id']} has the highest deterministic verification priority after recent-challenge penalty.",
        "decision_source": "deterministic_information_gain",
        "reasoning_source": "deterministic",
        "priority_breakdown": breakdown,
    }
    prompt = render_prompt(
        "examiner",
        {
            "skill_mirror": skill_mirror,
            "evidence_history": history,
            "previous_challenges": previous,
            "locked_decision": result,
        },
        "examiner_output.schema.json",
    )
    model = safe_llm_json(
        llm,
        prompt,
        schema_name="examiner_output.schema.json",
        timeout_seconds=llm_timeout_seconds,
    )
    if model and all(model.get(key) == result[key] for key in ("target_skill", "target_subskill", "difficulty", "challenge_type", "mode")):
        result["reason"] = model["reason"]
        result["reasoning_source"] = "llm_refined_locked_decision"
    return result
