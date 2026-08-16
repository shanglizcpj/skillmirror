"""A-side trusted orchestration used by the internal API and demo."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from agents.evaluator import evaluate
from agents.examiner import examine
from .challenge_validation import validate_challenge
from .confidence_engine import calculate_confidence
from .evidence import load_rules, materialize_evidence
from .provenance import content_digest, verify_b_record, verify_challenge, verify_evidence
from .schema_validation import validate_payload
from .skill_engine import calculate_skill_update


def _skill_entry(skill_mirror: Dict[str, Any], skill_id: str) -> Dict[str, Any]:
    for item in skill_mirror.get("skills", []):
        if item.get("skill_id") == skill_id or item.get("id") == skill_id:
            return item
    raise ValueError(f"skill_mirror does not contain target skill: {skill_id}")


def _sanitize_b_record(
    record: Dict[str, Any],
    *,
    expected_type: str,
    user_id: str,
    session_id: str,
    challenge_id: str,
    b_provenance_secret: str | bytes,
    submitted_code_digest: Optional[str] = None,
    challenge_digest: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    result = deepcopy(record)
    reason: Optional[str] = None
    if not verify_b_record(result, b_provenance_secret):
        reason = "invalid_b_record_provenance"
    elif result.get("record_type") != expected_type:
        reason = "record_type_mismatch"
    elif any(result.get(key) != expected for key, expected in (
        ("user_id", user_id), ("session_id", session_id), ("challenge_id", challenge_id)
    )):
        reason = "record_identity_mismatch"
    elif expected_type == "test_result" and (
        result.get("submission_digest") != submitted_code_digest
        or result.get("challenge_digest") != challenge_digest
    ):
        reason = "test_result_binding_mismatch"
    # Caller-supplied verification_status never crosses this assignment.
    result["verification_status"] = "verified" if reason is None else "unverified"
    return result, reason


def _sanitize_collection(
    records: List[Dict[str, Any]],
    *,
    expected_type: str,
    payload: Dict[str, Any],
    challenge: Dict[str, Any],
    b_provenance_secret: str | bytes,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    trusted_or_flagged: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for index, record in enumerate(records):
        normalized, reason = _sanitize_b_record(
            record,
            expected_type=expected_type,
            user_id=payload["user_id"],
            session_id=payload["session_id"],
            challenge_id=challenge["challenge_id"],
            b_provenance_secret=b_provenance_secret,
            submitted_code_digest=content_digest(payload["submitted_code"]),
            challenge_digest=challenge.get("content_hash"),
        )
        trusted_or_flagged.append(normalized)
        if reason:
            rejected.append({"collection": expected_type, "index": index, "reason": reason})
    return trusted_or_flagged, rejected


def _trusted_evidence_history(
    evidence: List[Dict[str, Any]],
    evidence_secret: str | bytes,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    trusted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    expected_rule_version = load_rules()["version"]
    for index, item in enumerate(evidence):
        try:
            validate_payload(item, "evidence.schema.json")
        except (TypeError, ValueError):
            rejected.append({"index": index, "reason": "invalid_trusted_evidence_schema"})
            continue
        if item.get("rule_version") != expected_rule_version:
            rejected.append({"index": index, "reason": "unsupported_rule_version"})
            continue
        if not verify_evidence(item, evidence_secret):
            rejected.append({"index": index, "reason": "invalid_evidence_provenance"})
            continue
        trusted.append(item)
    return trusted, rejected


def complete_assessment(
    payload: Dict[str, Any],
    *,
    b_provenance_secret: str | bytes,
    a_evidence_secret: str | bytes,
    llm=None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    required = {"user_id", "session_id", "skill_mirror", "challenge", "submitted_code"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"assessment payload missing fields: {missing}")
    challenge = payload["challenge"]
    if not verify_challenge(challenge, a_evidence_secret):
        raise ValueError("assessment challenge lacks valid A-side provenance")
    challenge_report = validate_challenge(challenge)
    if not challenge_report["valid"] or challenge.get("content_hash") != challenge_report["content_hash"]:
        raise ValueError("assessment challenge failed integrity/oracle validation")

    target_skill = challenge.get("target_skill")
    target_subskill = challenge.get("target_subskill")
    current_entry = _skill_entry(payload["skill_mirror"], target_skill)
    rejected_records: List[Dict[str, Any]] = []

    action_logs, rejected = _sanitize_collection(
        payload.get("action_logs", []), expected_type="action_log", payload=payload,
        challenge=challenge, b_provenance_secret=b_provenance_secret,
    )
    rejected_records.extend(rejected)
    code_versions, rejected = _sanitize_collection(
        payload.get("code_versions", []), expected_type="code_version", payload=payload,
        challenge=challenge, b_provenance_secret=b_provenance_secret,
    )
    rejected_records.extend(rejected)
    # Untrusted code-version metadata is omitted because it is only contextual.
    code_versions = [item for item in code_versions if item["verification_status"] == "verified"]
    test_results, rejected = _sanitize_collection(
        payload.get("test_results", []), expected_type="test_result", payload=payload,
        challenge=challenge, b_provenance_secret=b_provenance_secret,
    )
    rejected_records.extend(rejected)
    hint_history, rejected = _sanitize_collection(
        payload.get("hint_history", []), expected_type="hint_record", payload=payload,
        challenge=challenge, b_provenance_secret=b_provenance_secret,
    )
    rejected_records.extend(rejected)

    evaluation = evaluate(
        challenge,
        action_logs=action_logs,
        code_versions=code_versions,
        test_results=test_results,
        hint_history=hint_history,
        submitted_code=payload["submitted_code"],
        elapsed_seconds=payload.get("elapsed_seconds"),
        user_id=payload["user_id"],
        session_id=payload["session_id"],
        verification_provenance_secret=a_evidence_secret,
        llm=llm,
    )
    context = {
        "user_id": payload["user_id"],
        "session_id": payload["session_id"],
        "challenge_id": challenge["challenge_id"],
        "challenge_digest": challenge["content_hash"],
        "challenge_type": challenge["challenge_type"],
        "target_skill": target_skill,
        "target_subskill": target_subskill,
        "difficulty": challenge["difficulty"],
        **({"timestamp": payload["timestamp"]} if payload.get("timestamp") else {}),
    }
    materialized = materialize_evidence(
        evaluation["evidence_candidates"],
        context=context,
        verification_records=evaluation["verification_records"],
        provenance_secret=a_evidence_secret,
    )
    prior_evidence, rejected_history = _trusted_evidence_history(
        list(payload.get("evidence_history", [])), a_evidence_secret
    )
    prior_ids = {item["evidence_id"] for item in prior_evidence}
    replayed_evidence = [
        {"evidence_id": item["evidence_id"], "reason": "already_present_in_trusted_history"}
        for item in materialized["accepted"]
        if item["evidence_id"] in prior_ids
    ]
    newly_materialized = [
        item for item in materialized["accepted"] if item["evidence_id"] not in prior_ids
    ]
    new_target_evidence = [item for item in newly_materialized if item["skill"] == target_skill]
    prior_target = [item for item in prior_evidence if item.get("skill") == target_skill]
    score = calculate_skill_update(
        current_entry.get("score"), new_target_evidence,
        skill_id=target_skill, evidence_secret=a_evidence_secret,
    )
    validate_payload(score, "skill_update.schema.json")
    confidence = calculate_confidence(
        prior_target + new_target_evidence,
        skill_id=target_skill,
        now=now,
        evidence_secret=a_evidence_secret,
    )
    validate_payload(confidence, "confidence.schema.json")

    updated_mirror = deepcopy(payload["skill_mirror"])
    updated_entry = _skill_entry(updated_mirror, target_skill)
    updated_entry["score"] = score["new_score"]
    updated_entry["confidence"] = confidence["confidence"]
    updated_entry["evidence_count"] = len(prior_target) + len(new_target_evidence)
    previous_challenges = list(payload.get("previous_challenges", [])) + [{
        "challenge_id": challenge["challenge_id"],
        "target_skill": target_skill,
        "target_subskill": target_subskill,
        "difficulty": challenge["difficulty"],
    }]
    next_decision = examine(
        updated_mirror,
        evidence_history=prior_evidence + newly_materialized,
        previous_challenges=previous_challenges,
        llm=llm,
    )
    validate_payload(next_decision, "examiner_output.schema.json")
    return {
        "schema_version": "2.1",
        "trust_report": {
            "rejected_b_records": rejected_records,
            "rejected_evidence_history": rejected_history,
            "replayed_evidence": replayed_evidence,
            "caller_verification_status_trusted": False,
        },
        "evaluation": evaluation,
        "evidence_materialization": materialized,
        "score": score,
        "confidence": confidence,
        "updated_skill_mirror": updated_mirror,
        "next_examiner": next_decision,
    }
