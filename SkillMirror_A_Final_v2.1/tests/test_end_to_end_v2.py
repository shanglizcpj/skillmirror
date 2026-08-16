from demo.run_a_demo import run_demo
from skill_engine.schema_validation import validate_payload


def test_reproducible_demo_runs_verified_full_closed_loop():
    result = run_demo()
    assert result["demo_disclosure"].startswith("Simulated learner")
    assert result["actual_test_run"]["passed"] == result["actual_test_run"]["total"] == 4
    assert result["evidence_materialization"]["accepted"]
    assert result["score"]["new_score"] == 84.75
    assert result["score"]["score_status"] == "provisional"
    assert result["confidence"]["confidence_percent"] == 28.7
    assert result["confidence"]["counts"]["independent_sessions"] == 1
    assert result["next_examiner"]["target_skill"] == "testing"
    validate_payload(result["score"], "skill_update.schema.json")
    validate_payload(result["confidence"], "confidence.schema.json")
    validate_payload(result["next_examiner"], "examiner_output.schema.json")
