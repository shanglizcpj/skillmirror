import json

from conftest import TEST_A_SECRET
from agents.challenge_generator import generate_challenge
from agents.evaluator import evaluate
from skill_engine.evidence import materialize_evidence
from skill_engine.schema_validation import validate_payload


def hidden_result(status="verified", passed=4, total=4, **extra):
    return {
        "run_id": "RUN1",
        "passed": passed,
        "total": total,
        "scope": "hidden",
        "runner": "sandbox",
        "verification_status": status,
        "timestamp": "2026-08-14T01:00:00+00:00",
        **extra,
    }


def test_verified_hidden_pass_proposes_outcome(debugging_challenge):
    result = evaluate(debugging_challenge, test_results=[hidden_result()], submitted_code="fixed", user_id="U1", session_id="S1")
    assert "challenge_tests_passed" in {item["event"] for item in result["evidence_candidates"]}


def test_public_only_test_does_not_prove_completion(debugging_challenge):
    public = hidden_result(scope="public")
    result = evaluate(debugging_challenge, test_results=[public], submitted_code="fixed", user_id="U1", session_id="S1")
    assert "challenge_tests_passed" not in {item["event"] for item in result["evidence_candidates"]}


def test_unverified_test_does_not_prove_completion(debugging_challenge):
    result = evaluate(debugging_challenge, test_results=[hidden_result(status="unverified")], submitted_code="fixed", user_id="U1", session_id="S1")
    assert "challenge_tests_passed" not in {item["event"] for item in result["evidence_candidates"]}
    assert "unverified_test_result" in result["flags"]


def test_malformed_counts_are_flagged(debugging_challenge):
    result = evaluate(debugging_challenge, test_results=[hidden_result(passed=5, total=4)], submitted_code="fixed", user_id="U1", session_id="S1")
    assert "malformed_test_result" in result["flags"]


def test_malformed_regression_count_is_flagged_not_crashed(debugging_challenge):
    result = evaluate(
        debugging_challenge,
        test_results=[hidden_result(regressions="not-a-number")],
        submitted_code="fixed", user_id="U1", session_id="S1",
    )
    assert "malformed_test_result" in result["flags"]


def test_malformed_hint_level_is_flagged_not_crashed(debugging_challenge):
    result = evaluate(
        debugging_challenge,
        hint_history=[{"hint_id": "H1", "level": "bad", "verification_status": "verified"}],
        submitted_code="fixed", user_id="U1", session_id="S1",
    )
    assert "malformed_hint_record" in result["flags"]


def test_empty_submission_cannot_receive_completion_evidence(debugging_challenge):
    result = evaluate(debugging_challenge, test_results=[hidden_result()], submitted_code="", user_id="U1", session_id="S1")
    assert "empty_submission" in result["flags"]
    assert "challenge_tests_passed" not in {item["event"] for item in result["evidence_candidates"]}


def test_debugging_process_events_require_debugging_target(debugging_challenge):
    logs = [{"log_id": "L1", "event": "code_executed", "verification_status": "verified"}]
    debug = evaluate(debugging_challenge, action_logs=logs, submitted_code="x", user_id="U1", session_id="S1")
    coding = generate_challenge({"target_skill": "coding", "difficulty": "easy"})
    code = evaluate(coding, action_logs=logs, submitted_code="x", user_id="U1", session_id="S1")
    assert "ran_program_proactively" in {item["event"] for item in debug["evidence_candidates"]}
    assert "ran_program_proactively" not in {item["event"] for item in code["evidence_candidates"]}


def test_hint_history_creates_dependency_candidate(debugging_challenge):
    hints = [{"hint_id": "H3", "level": 3, "verification_status": "verified"}]
    result = evaluate(debugging_challenge, hint_history=hints, submitted_code="x", user_id="U1", session_id="S1")
    assert "used_hint_level_3" in {item["event"] for item in result["evidence_candidates"]}


def test_possible_copy_is_only_a_flag(debugging_challenge):
    result = evaluate(debugging_challenge, submitted_code=debugging_challenge["reference_solution"], code_versions=[{"version": 1}], user_id="U1", session_id="S1")
    assert "possible_direct_copy" in result["flags"]
    assert not result["evidence_candidates"]


def test_testing_outcome_materializes_to_testing_skill():
    challenge = generate_challenge({"target_skill": "testing", "difficulty": "medium"})
    evaluation = evaluate(
        challenge, test_results=[hidden_result()], submitted_code="fixed",
        user_id="U1", session_id="S1", verification_provenance_secret=TEST_A_SECRET,
    )
    materialized = materialize_evidence(
        evaluation["evidence_candidates"],
        context={
            "user_id": "U1", "session_id": "S1", "challenge_id": challenge["challenge_id"],
            "challenge_digest": challenge["content_hash"],
            "challenge_type": challenge["challenge_type"], "target_skill": "testing",
            "target_subskill": challenge["target_subskill"], "difficulty": challenge["difficulty"],
        },
        verification_records=evaluation["verification_records"],
        provenance_secret=TEST_A_SECRET,
    )
    assert materialized["accepted"][0]["skill"] == "testing"


def test_llm_can_refine_text_but_not_locked_evidence(debugging_challenge):
    model = {
        "problem_solving_analysis": "refined problem text",
        "debugging_analysis": "refined debugging text",
        "testing_analysis": "refined testing text",
        "reasoning_summary": "refined summary",
    }
    result = evaluate(
        debugging_challenge,
        test_results=[hidden_result()],
        submitted_code="fixed",
        user_id="U1",
        session_id="S1",
        llm=lambda _p: json.dumps(model),
    )
    assert result["analysis_source"] == "llm_text_refinement_over_locked_facts"
    assert {item["event"] for item in result["evidence_candidates"]} == {"challenge_tests_passed"}


def test_evaluator_result_matches_schema(debugging_challenge):
    result = evaluate(debugging_challenge, submitted_code="x", user_id="U1", session_id="S1")
    validate_payload(result, "evaluator_output.schema.json")
