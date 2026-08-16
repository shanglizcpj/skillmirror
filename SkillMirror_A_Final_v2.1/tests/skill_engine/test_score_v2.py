import math
import pytest

from conftest import TEST_A_SECRET, evidence_item
from skill_engine.schema_validation import validate_payload
from skill_engine.skill_engine import calculate_skill_update


def update(previous_score, evidence, *, skill_id):
    return calculate_skill_update(
        previous_score, evidence, skill_id=skill_id, evidence_secret=TEST_A_SECRET
    )


def test_ab_plan_reference_example_70_to_76():
    result = update(70, [evidence_item()], skill_id="debugging")
    assert result["new_score"] == 76.0
    assert result["evidence_weight"] == 0.3


def test_unknown_without_evidence_stays_unknown():
    result = update(None, [], skill_id="debugging")
    assert result["new_score"] is None
    assert result["score_status"] == "unknown"


def test_cold_start_is_explicitly_provisional():
    result = update(None, [evidence_item()], skill_id="debugging")
    assert result["new_score"] == 90
    assert result["score_status"] == "provisional"


def test_hint_reduces_independent_performance():
    no_hint = update(70, [evidence_item()], skill_id="debugging")
    level3 = update(70, [evidence_item(hint_level="level_3")], skill_id="debugging")
    assert level3["new_score"] < no_hint["new_score"]


def test_same_session_is_correlation_capped():
    items = [
        evidence_item("EV-0000000000000001"),
        evidence_item("EV-0000000000000002", score=80),
    ]
    result = update(70, items, skill_id="debugging")
    assert result["evidence_weight"] == 0.4
    assert result["session_breakdown"][0]["correlation_cap_applied"]


def test_two_independent_sessions_can_reach_total_cap():
    items = [
        evidence_item("EV-0000000000000001", session_id="S1"),
        evidence_item("EV-0000000000000002", session_id="S2", challenge_id="DBG002"),
    ]
    result = update(70, items, skill_id="debugging")
    assert result["evidence_weight"] == 0.6


def test_duplicate_evidence_id_is_excluded():
    item = evidence_item()
    result = update(70, [item, dict(item)], skill_id="debugging")
    assert result["evidence_weight"] == 0.3
    assert result["excluded_evidence"][0]["reason"] == "duplicate_evidence_id"


def test_cross_skill_evidence_is_excluded():
    result = update(70, [evidence_item(skill="testing")], skill_id="debugging")
    assert result["new_score"] == 70
    assert result["excluded_evidence"][0]["reason"] == "different_skill"


def test_multi_skill_input_requires_explicit_target():
    with pytest.raises(ValueError):
        calculate_skill_update(70, [
            evidence_item("EV-0000000000000001", skill="debugging"),
            evidence_item("EV-0000000000000002", skill="testing"),
        ], evidence_secret=TEST_A_SECRET)


def test_negative_verified_evidence_can_lower_score():
    negative = evidence_item(score=30, direction="negative")
    result = update(70, [negative], skill_id="debugging")
    assert result["new_score"] < 70


def test_dependency_evidence_does_not_directly_change_score():
    dependency = evidence_item(score=None, direction="dependency", skill="problem_solving")
    result = update(70, [dependency], skill_id="problem_solving")
    assert result["new_score"] == 70


def test_first_failed_fix_neutral_context_does_not_change_score():
    neutral = evidence_item(score=50, direction="neutral")
    result = update(70, [neutral], skill_id="debugging")
    assert result["new_score"] == 70
    assert result["excluded_evidence"][0]["reason"] == "non_score_bearing_direction"


def test_non_finite_input_is_rejected():
    with pytest.raises(ValueError):
        update(float("nan"), [], skill_id="debugging")
    result = update(70, [evidence_item(score=float("inf"))], skill_id="debugging")
    assert result["new_score"] == 70
    assert result["excluded_evidence"][0]["reason"] == "invalid_trusted_evidence_schema"


def test_score_result_matches_schema():
    validate_payload(update(70, [evidence_item()], skill_id="debugging"), "skill_update.schema.json")


def test_forged_unsigned_100_strong_expert_cannot_change_score():
    forged = dict(evidence_item(score=100, strength="strong", difficulty="expert"))
    forged.pop("provenance")
    result = update(70, [forged], skill_id="debugging")
    assert result["new_score"] == 70
    assert result["evidence_weight"] == 0
    assert result["excluded_evidence"][0]["reason"] == "invalid_trusted_evidence_schema"


def test_tampering_signed_score_invalidates_provenance():
    forged = evidence_item(score=90)
    forged["performance_score"] = 100
    forged["difficulty"] = "expert"
    forged["reliability"] = 1.0
    result = update(70, [forged], skill_id="debugging")
    assert result["new_score"] == 70
    assert result["excluded_evidence"][0]["reason"] == "invalid_evidence_provenance"
