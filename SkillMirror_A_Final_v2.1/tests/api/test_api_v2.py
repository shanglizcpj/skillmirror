from __future__ import annotations

from copy import deepcopy
import json

from fastapi.testclient import TestClient

from agents.challenge_generator import TEMPLATES
from api.app import app, configure_llm
from api.security import (
    A_EVIDENCE_SECRET_ENV,
    B_PROVENANCE_SECRET_ENV,
    INTERNAL_TOKEN_ENV,
    INTERNAL_TOKEN_HEADER,
)
from conftest import TEST_A_SECRET, TEST_B_SECRET, TEST_INTERNAL_TOKEN
from skill_engine.challenge_validation import canonical_digest, run_code_tests
from skill_engine.provenance import content_digest, sign_b_record


client = TestClient(app)


def _configure_security(monkeypatch):
    monkeypatch.setenv(INTERNAL_TOKEN_ENV, TEST_INTERNAL_TOKEN)
    monkeypatch.setenv(B_PROVENANCE_SECRET_ENV, TEST_B_SECRET)
    monkeypatch.setenv(A_EVIDENCE_SECRET_ENV, TEST_A_SECRET)


def _headers(token=TEST_INTERNAL_TOKEN):
    return {INTERNAL_TOKEN_HEADER: token}


def _mirror():
    return {"user_id": "U-API", "skills": [
        {"skill_id": "coding", "score": 78, "confidence": 0.81},
        {"skill_id": "debugging", "score": None, "confidence": 0.0},
        {"skill_id": "testing", "score": 61, "confidence": 0.42},
        {"skill_id": "problem_solving", "score": 70, "confidence": 0.68},
        {"skill_id": "code_reading", "score": 74, "confidence": 0.76},
    ]}


def _submission():
    return (
        "def average_price(items):\n"
        "    return 0 if len(items) == 0 else sum(items) / len(items)\n\n"
        "def discounted_total(prices, threshold=100):\n"
        "    if len(prices) == 0:\n"
        "        return 0\n"
        "    total = sum(prices)\n"
        "    return total * 0.9 if average_price(prices) > threshold else total\n"
    )


def _server_challenge(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post(
        "/v1/challenges/generate",
        json={
            "examiner_decision": {
                "target_skill": "debugging",
                "target_subskill": "boundary_awareness",
                "difficulty": "medium",
            },
            "response_view": "server",
        },
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    return response.json()["challenge"]


def _signed_b_record(record_type, challenge, **fields):
    return sign_b_record(
        {
            "record_type": record_type,
            "user_id": "U-API",
            "session_id": "S-API-1",
            "challenge_id": challenge["challenge_id"],
            **fields,
        },
        TEST_B_SECRET,
    )


def _assessment_payload(challenge):
    submitted = _submission()
    actual = run_code_tests(submitted, challenge["entry_point"], challenge["test_cases"])
    return {
        "user_id": "U-API",
        "session_id": "S-API-1",
        "skill_mirror": _mirror(),
        "challenge": challenge,
        "action_logs": [
            _signed_b_record(
                "action_log", challenge, log_id="L-API-1", event="code_executed",
                timestamp="2026-08-14T01:00:00+00:00",
            ),
            _signed_b_record(
                "action_log", challenge, log_id="L-API-2", event="reproduced_error",
                timestamp="2026-08-14T01:00:15+00:00",
            ),
            _signed_b_record(
                "action_log", challenge, log_id="L-API-3", event="boundary_input_tested",
                timestamp="2026-08-14T01:00:30+00:00",
            ),
        ],
        "code_versions": [
            _signed_b_record(
                "code_version", challenge, version=1,
                code_digest=canonical_digest(challenge["starter_code"]),
            ),
            _signed_b_record(
                "code_version", challenge, version=2,
                code_digest=canonical_digest(submitted),
            ),
        ],
        "test_results": [
            _signed_b_record(
                "test_result", challenge,
                run_id="R-API-1", passed=actual["passed"], total=actual["total"],
                scope="hidden_and_public", runner="test",
                timestamp="2026-08-14T01:01:00+00:00",
                result_digest=canonical_digest(actual),
                submission_digest=content_digest(submitted),
                challenge_digest=challenge["content_hash"],
            )
        ],
        "submitted_code": submitted,
        "timestamp": "2026-08-14T01:02:00+00:00",
    }


def _complete(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    response = client.post(
        "/v1/assessment/complete",
        json=_assessment_payload(challenge),
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_health_and_openapi_are_available():
    health = client.get("/health").json()
    assert health["llm_required"] is False
    assert health["version"] == "2.1.0"
    assert client.get("/openapi.json").status_code == 200


def test_strict_request_rejects_unknown_top_level_fields(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post(
        "/v1/examiner/decide",
        json={"skill_mirror": _mirror(), "unexpected": "must fail"},
        headers=_headers(),
    )
    assert response.status_code == 422


def test_examiner_endpoint_returns_locked_decision(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post(
        "/v1/examiner/decide",
        json={"skill_mirror": _mirror()},
        headers=_headers(),
    )
    assert response.status_code == 200
    assert response.json()["target_skill"] == "debugging"


def test_examiner_internal_endpoint_rejects_missing_token(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post("/v1/examiner/decide", json={"skill_mirror": _mirror()})
    assert response.status_code == 401


def test_challenge_defaults_to_public_learner_safe_view(monkeypatch):
    monkeypatch.delenv(INTERNAL_TOKEN_ENV, raising=False)
    monkeypatch.delenv(A_EVIDENCE_SECRET_ENV, raising=False)
    response = client.post("/v1/challenges/generate", json={
        "examiner_decision": {"target_skill": "debugging", "difficulty": "medium"},
    })
    assert response.status_code == 200
    body = response.json()
    assert body["view"] == "learner"
    assert "reference_solution" not in body["challenge"]
    assert "test_cases" not in body["challenge"]
    assert "hidden_bugs" not in body["challenge"]
    assert "validation_report" not in body["challenge"]
    assert "provenance" not in body["challenge"]
    assert all(case["visibility"] == "public" for case in body["challenge"]["public_tests"])


def test_server_challenge_rejects_missing_token_without_leaking_oracle(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post("/v1/challenges/generate", json={
        "examiner_decision": {"target_skill": "debugging", "difficulty": "medium"},
        "response_view": "server",
    })
    assert response.status_code == 401
    assert "reference_solution" not in response.text
    assert "hidden_bugs" not in response.text


def test_server_challenge_rejects_wrong_token_without_leaking_oracle(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post(
        "/v1/challenges/generate",
        json={
            "examiner_decision": {"target_skill": "debugging", "difficulty": "medium"},
            "response_view": "server",
        },
        headers=_headers("wrong-token-that-is-long-enough-000000"),
    )
    assert response.status_code == 401
    assert "reference_solution" not in response.text
    assert "hidden_bugs" not in response.text


def test_server_challenge_view_with_internal_token_contains_signed_oracle(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    assert "reference_solution" in challenge
    assert "hidden_bugs" in challenge
    assert any(case["visibility"] == "hidden" for case in challenge["test_cases"])
    assert challenge["provenance"]["purpose"] == "internal-challenge"


def test_server_challenge_fails_closed_when_auth_not_configured(monkeypatch):
    monkeypatch.delenv(INTERNAL_TOKEN_ENV, raising=False)
    response = client.post(
        "/v1/challenges/generate",
        json={
            "examiner_decision": {"target_skill": "debugging", "difficulty": "medium"},
            "response_view": "server",
        },
        headers=_headers(),
    )
    assert response.status_code == 503


def test_api_can_inject_optional_llm_without_making_it_required():
    configure_llm(lambda _prompt: json.dumps(TEMPLATES["debugging"]))
    try:
        response = client.post("/v1/challenges/generate", json={
            "examiner_decision": {"target_skill": "debugging", "difficulty": "medium"},
        })
        assert response.json()["challenge"]["generation_source"] == "llm_oracle_validated"
    finally:
        configure_llm(None)


def test_complete_assessment_endpoint_runs_full_signed_loop(monkeypatch):
    body = _complete(monkeypatch)
    assert body["evaluation"]["verification_records"]
    assert body["evidence_materialization"]["accepted"]
    assert body["score"]["score_status"] == "provisional"
    assert body["confidence"]["confidence_status"] == "low"
    assert body["next_examiner"]["target_skill"] == "testing"
    assert body["trust_report"]["rejected_b_records"] == []
    assert body["trust_report"]["replayed_evidence"] == []
    assert body["trust_report"]["caller_verification_status_trusted"] is False


def test_complete_assessment_is_internal_only(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    response = client.post(
        "/v1/assessment/complete", json=_assessment_payload(challenge),
    )
    assert response.status_code == 401


def test_complete_assessment_rejects_missing_target_skill_in_mirror(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    payload = _assessment_payload(challenge)
    payload["skill_mirror"] = {"skills": []}
    response = client.post(
        "/v1/assessment/complete", json=payload, headers=_headers(),
    )
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_complete_assessment_rejects_unsigned_challenge(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    challenge.pop("provenance")
    response = client.post(
        "/v1/assessment/complete",
        json=_assessment_payload(challenge),
        headers=_headers(),
    )
    assert response.status_code == 422
    assert "valid A-side provenance" in response.text


def test_caller_self_declared_verified_record_is_not_trusted(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    payload = _assessment_payload(challenge)
    payload["action_logs"] = []
    payload["code_versions"] = []
    payload["test_results"] = [{
        "record_type": "test_result",
        "user_id": "U-API",
        "session_id": "S-API-1",
        "challenge_id": challenge["challenge_id"],
        "run_id": "FORGED-RUN",
        "passed": 4,
        "total": 4,
        "scope": "hidden_and_public",
        "verification_status": "verified",
        "submission_digest": content_digest(payload["submitted_code"]),
        "challenge_digest": challenge["content_hash"],
    }]
    response = client.post(
        "/v1/assessment/complete", json=payload, headers=_headers(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence_materialization"]["accepted"] == []
    assert body["score"]["new_score"] is None
    assert body["trust_report"]["rejected_b_records"] == [{
        "collection": "test_result", "index": 0, "reason": "invalid_b_record_provenance",
    }]


def test_tampered_signed_test_result_binding_is_rejected(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    payload = _assessment_payload(challenge)
    payload["action_logs"] = []
    payload["code_versions"] = []
    payload["test_results"][0]["passed"] = 100
    payload["test_results"][0]["total"] = 100
    response = client.post(
        "/v1/assessment/complete", json=payload, headers=_headers(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence_materialization"]["accepted"] == []
    assert body["score"]["new_score"] is None
    assert body["trust_report"]["rejected_b_records"][0]["reason"] == "invalid_b_record_provenance"


def test_skill_update_is_internal_only(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post("/v1/skills/update", json={
        "skill_id": "debugging",
        "previous_score": 10,
        "trusted_evidence": [],
    })
    assert response.status_code == 401


def test_skill_update_rejects_legacy_arbitrary_evidence_field(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post(
        "/v1/skills/update",
        json={
            "skill_id": "debugging",
            "previous_score": 10,
            "new_evidence": [{"performance_score": 100, "strength": "strong"}],
        },
        headers=_headers(),
    )
    assert response.status_code == 422


def test_forged_100_strong_expert_evidence_cannot_change_score(monkeypatch):
    genuine_body = _complete(monkeypatch)
    forged = deepcopy(genuine_body["evidence_materialization"]["accepted"][0])
    forged.update({
        "performance_score": 100,
        "strength": "strong",
        "difficulty": "expert",
        "reliability": 1.0,
        "direction": "positive",
    })
    response = client.post(
        "/v1/skills/update",
        json={
            "skill_id": "debugging",
            "previous_score": 10,
            "trusted_evidence": [forged],
        },
        headers=_headers(),
    )
    assert response.status_code == 422
    assert "invalid provenance" in response.text


def test_skill_update_accepts_only_genuine_materialized_evidence(monkeypatch):
    body = _complete(monkeypatch)
    genuine = body["evidence_materialization"]["accepted"]
    response = client.post(
        "/v1/skills/update",
        json={
            "skill_id": "debugging",
            "previous_score": None,
            "trusted_evidence": genuine,
            "trusted_evidence_history": [],
        },
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["score"]["new_score"] > 70


def test_skill_update_rejects_replay_from_trusted_history(monkeypatch):
    body = _complete(monkeypatch)
    genuine = [
        item for item in body["evidence_materialization"]["accepted"]
        if item["skill"] == "debugging"
    ]
    response = client.post(
        "/v1/skills/update",
        json={
            "skill_id": "debugging",
            "previous_score": body["score"]["new_score"],
            "trusted_evidence": [genuine[0]],
            "trusted_evidence_history": genuine,
        },
        headers=_headers(),
    )
    assert response.status_code == 422
    assert "replays evidence already present in history" in response.text


def test_complete_assessment_does_not_score_replayed_evidence_twice(monkeypatch):
    first = _complete(monkeypatch)
    challenge = _server_challenge(monkeypatch)
    payload = _assessment_payload(challenge)
    payload["skill_mirror"] = first["updated_skill_mirror"]
    payload["evidence_history"] = first["evidence_materialization"]["accepted"]
    response = client.post(
        "/v1/assessment/complete", json=payload, headers=_headers(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["score"]["new_score"] == first["score"]["new_score"]
    assert body["score"]["evidence_weight"] == 0
    assert body["trust_report"]["replayed_evidence"]


def test_evidence_materialization_is_internal_only(monkeypatch):
    _configure_security(monkeypatch)
    response = client.post("/v1/evidence/materialize", json={
        "candidates": [], "context": {}, "verification_records": [],
    })
    assert response.status_code == 401


def test_evidence_api_rejects_self_declared_verified_record(monkeypatch):
    challenge = _server_challenge(monkeypatch)
    response = client.post(
        "/v1/evidence/materialize",
        json={
            "candidates": [{
                "event": "challenge_tests_passed",
                "verification_refs": ["FORGED-VERIFICATION"],
            }],
            "context": {
                "user_id": "U-API",
                "session_id": "S-API-1",
                "challenge_id": challenge["challenge_id"],
                "challenge_digest": challenge["content_hash"],
                "challenge_type": challenge["challenge_type"],
                "target_skill": challenge["target_skill"],
                "target_subskill": challenge["target_subskill"],
                "difficulty": challenge["difficulty"],
            },
            "verification_records": [{
                "ref_id": "FORGED-VERIFICATION",
                "type": "hidden_test_result",
                "status": "verified",
                "user_id": "U-API",
                "session_id": "S-API-1",
                "challenge_id": challenge["challenge_id"],
                "challenge_digest": challenge["content_hash"],
                "target_skill": challenge["target_skill"],
                "target_subskill": challenge["target_subskill"],
                "difficulty": challenge["difficulty"],
                "payload_digest": canonical_digest({"forged": True}),
            }],
        },
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["accepted"] == []
    assert response.json()["rejected"][0]["reason"] == "missing_or_mismatched_verified_record"
