"""Rule-locked, traceable Evidence Engine (A2)."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import re

from .schema_validation import validate_payload
from .provenance import sign_evidence, verify_verification_record
from .skill_tree import get_subskills, load_skill_tree

DEFAULT_RULES = Path(__file__).resolve().parents[1] / "evidence_rules.json"


def load_rules(path: Optional[str] = None) -> Dict[str, Any]:
    p = Path(path) if path else DEFAULT_RULES
    rules = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(rules.get("rules"), list) or not rules.get("version"):
        raise ValueError("evidence rule file is malformed")
    return rules


def _canonical(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest(data: Any) -> str:
    return "sha256:" + sha256(_canonical(data).encode("utf-8")).hexdigest()


def _valid_context(context: Dict[str, Any]) -> None:
    required = {
        "user_id", "session_id", "challenge_id", "challenge_type",
        "target_skill", "target_subskill", "difficulty", "challenge_digest",
    }
    missing = sorted(required - set(context))
    if missing:
        raise ValueError(f"evidence context missing fields: {missing}")
    tree = load_skill_tree()
    skills = {item["id"] for item in tree["root_skill"]["children"]}
    if context["target_skill"] not in skills:
        raise ValueError("target_skill is not in skill_tree.json")
    if context["target_subskill"] not in get_subskills(context["target_skill"]):
        raise ValueError("target_subskill does not belong to target_skill")
    if context["difficulty"] not in {"easy", "medium", "hard", "expert"}:
        raise ValueError("difficulty is invalid")
    if not isinstance(context["challenge_digest"], str) or re.fullmatch(r"sha256:[0-9a-f]{64}", context["challenge_digest"]) is None:
        raise ValueError("challenge_digest is invalid")


def _record_index(
    records: Iterable[Dict[str, Any]],
    context: Dict[str, Any],
    provenance_secret: str | bytes,
) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for record in records:
        ref_id = record.get("ref_id")
        if not isinstance(ref_id, str) or not ref_id or ref_id in index:
            continue
        if record.get("status") != "verified":
            continue
        if not verify_verification_record(record, provenance_secret):
            continue
        if any(record.get(k) != context.get(k) for k in ("user_id", "session_id", "challenge_id")):
            continue
        if any(record.get(k) != context.get(k) for k in ("target_skill", "target_subskill", "difficulty")):
            continue
        if record.get("challenge_digest") != context.get("challenge_digest"):
            continue
        digest = record.get("payload_digest")
        if not isinstance(digest, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
            continue
        index[ref_id] = record
    return index


def _resolve_rule_value(value: Any, context: Dict[str, Any]) -> Any:
    if value == "$target_skill":
        return context["target_skill"]
    if value == "$target_subskill":
        return context["target_subskill"]
    return value


def _derived_hint_level(rule: Dict[str, Any], selected: List[Dict[str, Any]]) -> str:
    if rule.get("hint_level"):
        return rule["hint_level"]
    ranking = {"none": 0, "level_1": 1, "level_2": 2, "level_3": 3, "direct_help": 4}
    observed = [record.get("hint_level", "none") for record in selected if record.get("type") == "hint_record"]
    return max(observed, key=lambda value: ranking.get(value, 0), default="none")


def materialize_evidence(
    candidates: Iterable[Dict[str, Any]],
    *,
    context: Dict[str, Any],
    verification_records: Iterable[Dict[str, Any]],
    provenance_secret: str | bytes,
    rules_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Accept rule-known candidates backed by A-signed verification records.

    Candidate fields never override rule-owned skill, strength, direction,
    performance score, delta or reliability.  This closes the original package's
    indirect LLM-scoring path.
    """
    _valid_context(context)
    rules = load_rules(rules_path)
    by_event = {rule["event"]: rule for rule in rules["rules"]}
    records = _record_index(verification_records, context, provenance_secret)
    timestamp = context.get("timestamp") or datetime.now(timezone.utc).isoformat()
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    seen = set()

    for position, candidate in enumerate(candidates):
        event = candidate.get("event") if isinstance(candidate, dict) else None
        rule = by_event.get(event)
        if not rule:
            rejected.append({"index": position, "event": event, "reason": "unknown_event"})
            continue
        refs = candidate.get("verification_refs", [])
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs):
            rejected.append({"index": position, "event": event, "reason": "verification_refs_required"})
            continue
        selected = [records[ref] for ref in refs if ref in records]
        selected_types = {record.get("type") for record in selected}
        required_types = set(rule.get("required_verification_types", []))
        if len(selected) != len(set(refs)) or not required_types.issubset(selected_types):
            rejected.append({
                "index": position,
                "event": event,
                "reason": "missing_or_mismatched_verified_record",
                "required_types": sorted(required_types),
            })
            continue
        identity = {
            "user_id": context["user_id"],
            "session_id": context["session_id"],
            "challenge_id": context["challenge_id"],
            "challenge_digest": context["challenge_digest"],
            "event": event,
            "refs": sorted(set(refs)),
            "rule_id": rule["rule_id"],
            "rule_version": rules["version"],
        }
        evidence_id = "EV-" + sha256(_canonical(identity).encode("utf-8")).hexdigest()[:16]
        if evidence_id in seen:
            rejected.append({"index": position, "event": event, "reason": "duplicate_candidate"})
            continue
        seen.add(evidence_id)
        reason = candidate.get("reason") if isinstance(candidate.get("reason"), str) else rule.get("description", event)
        item = {
            "schema_version": "2.1",
            "evidence_id": evidence_id,
            "rule_id": rule["rule_id"],
            "rule_version": rules["version"],
            "user_id": context["user_id"],
            "session_id": context["session_id"],
            "challenge_id": context["challenge_id"],
            "challenge_digest": context["challenge_digest"],
            "challenge_type": context["challenge_type"],
            "skill": _resolve_rule_value(rule["skill"], context),
            "sub_skill": _resolve_rule_value(rule["sub_skill"], context),
            "event": event,
            "strength": rule["evidence_strength"],
            "direction": rule["direction"],
            "performance_score": rule.get("performance_score"),
            "score_delta": rule.get("score_delta", 0),
            "difficulty": context["difficulty"],
            "hint_level": _derived_hint_level(rule, selected),
            "reliability": rule["reliability"],
            "verification_refs": sorted(set(refs)),
            "source_digest": _digest(selected),
            "reason": reason[:600],
            "timestamp": timestamp,
        }
        trusted_item = sign_evidence(item, provenance_secret)
        try:
            validate_payload(trusted_item, "evidence.schema.json")
        except ValueError as exc:
            rejected.append({"index": position, "event": event, "reason": str(exc)})
            continue
        accepted.append(trusted_item)
    return {"accepted": accepted, "rejected": rejected, "rules_version": rules["version"]}


def build_evidence(
    candidates: Iterable[Dict[str, Any]],
    user_id: str,
    challenge_id: str,
    difficulty: str,
    *,
    session_id: str,
    challenge_type: str,
    target_skill: str,
    target_subskill: str,
    challenge_digest: str,
    verification_records: Iterable[Dict[str, Any]],
    provenance_secret: str | bytes,
    timestamp: Optional[str] = None,
    rules_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compatibility wrapper returning only accepted evidence."""
    result = materialize_evidence(
        candidates,
        context={
            "user_id": user_id,
            "session_id": session_id,
            "challenge_id": challenge_id,
            "challenge_type": challenge_type,
            "target_skill": target_skill,
            "target_subskill": target_subskill,
            "challenge_digest": challenge_digest,
            "difficulty": difficulty,
            **({"timestamp": timestamp} if timestamp else {}),
        },
        verification_records=verification_records,
        provenance_secret=provenance_secret,
        rules_path=rules_path,
    )
    return result["accepted"]
