from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from agents.challenge_generator import generate_challenge
from skill_engine.challenge_validation import canonical_digest
from skill_engine.provenance import sign_evidence, sign_verification_record


TEST_A_SECRET = "test-a-evidence-secret-0123456789abcdef"
TEST_B_SECRET = "test-b-provenance-secret-0123456789abcdef"
TEST_INTERNAL_TOKEN = "test-internal-token-0123456789abcdef"
TEST_CHALLENGE_DIGEST = canonical_digest({"challenge": "DBG001"})


@pytest.fixture
def mirror():
    return {"user_id": "U1", "skills": [
        {"skill_id": "coding", "score": 78, "confidence": 0.81},
        {"skill_id": "debugging", "score": None, "confidence": 0.0, "subskills": [{"id": "boundary_awareness", "score": None, "confidence": 0.0}]},
        {"skill_id": "testing", "score": 61, "confidence": 0.42},
        {"skill_id": "problem_solving", "score": 70, "confidence": 0.68},
        {"skill_id": "code_reading", "score": 74, "confidence": 0.76},
    ]}


@pytest.fixture
def debugging_challenge():
    return generate_challenge({"target_skill": "debugging", "target_subskill": "boundary_awareness", "difficulty": "medium"})


def verification_record(
    ref_id="RUN1", record_type="hidden_test_result", status="verified",
    user_id="U1", session_id="S1", challenge_id="DBG001", hint_level=None,
    challenge_digest=TEST_CHALLENGE_DIGEST, target_skill="debugging",
    target_subskill="boundary_awareness", difficulty="medium",
):
    item = {
        "ref_id": ref_id,
        "type": record_type,
        "status": status,
        "user_id": user_id,
        "session_id": session_id,
        "challenge_id": challenge_id,
        "challenge_digest": challenge_digest,
        "target_skill": target_skill,
        "target_subskill": target_subskill,
        "difficulty": difficulty,
        "timestamp": "2026-08-14T01:00:00+00:00",
        "payload_digest": canonical_digest({"ref": ref_id, "type": record_type}),
    }
    if hint_level:
        item["hint_level"] = hint_level
    return sign_verification_record(item, TEST_A_SECRET)


def evidence_item(
    evidence_id="EV-0000000000000001",
    *,
    skill="debugging",
    session_id="S1",
    challenge_id="DBG001",
    challenge_type="debugging_runtime",
    score=90,
    strength="strong",
    difficulty="medium",
    hint_level="none",
    reliability=1.0,
    direction="positive",
    timestamp="2026-08-14T01:00:00+00:00",
):
    item = {
        "schema_version": "2.1",
        "evidence_id": evidence_id,
        "rule_id": "EVR-TEST-001",
        "rule_version": "2.1.0",
        "user_id": "U1",
        "skill": skill,
        "sub_skill": "boundary_awareness",
        "session_id": session_id,
        "challenge_id": challenge_id,
        "challenge_digest": TEST_CHALLENGE_DIGEST,
        "challenge_type": challenge_type,
        "event": "test_fixture_event",
        "performance_score": score,
        "score_delta": 0,
        "strength": strength,
        "difficulty": difficulty,
        "hint_level": hint_level,
        "reliability": reliability,
        "direction": direction,
        "verification_refs": ["TEST-REF-1"],
        "source_digest": canonical_digest({"evidence_id": evidence_id}),
        "timestamp": timestamp,
        "reason": "test evidence",
    }
    return sign_evidence(item, TEST_A_SECRET)


@pytest.fixture
def now():
    return datetime(2026, 8, 14, 2, 0, tzinfo=timezone.utc)
