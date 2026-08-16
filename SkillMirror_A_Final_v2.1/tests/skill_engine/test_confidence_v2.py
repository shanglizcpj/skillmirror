from conftest import TEST_A_SECRET, evidence_item

from skill_engine.confidence_engine import calculate_confidence
from skill_engine.schema_validation import validate_payload


def confidence(evidence, *, skill_id, now):
    return calculate_confidence(
        evidence, skill_id=skill_id, now=now, evidence_secret=TEST_A_SECRET
    )


def test_zero_without_verified_score_evidence(now):
    result = confidence([], skill_id="debugging", now=now)
    assert result["confidence"] == 0
    assert result["counts"]["independent_sessions"] == 0


def test_many_events_from_one_task_still_have_low_confidence(now):
    items = [evidence_item(f"EV-{index:016x}", score=85 + index) for index in range(1, 5)]
    result = confidence(items, skill_id="debugging", now=now)
    assert result["confidence"] < 0.45
    assert result["counts"]["independent_sessions"] == 1


def test_more_independent_sessions_increase_confidence(now):
    one = [evidence_item()]
    many = [
        evidence_item("EV-0000000000000001", session_id="S1", challenge_id="C1", challenge_type="runtime", difficulty="easy", score=82),
        evidence_item("EV-0000000000000002", session_id="S2", challenge_id="C2", challenge_type="edge", difficulty="medium", score=84),
        evidence_item("EV-0000000000000003", session_id="S3", challenge_id="C3", challenge_type="trace", difficulty="hard", score=81),
        evidence_item("EV-0000000000000004", session_id="S4", challenge_id="C4", challenge_type="implementation", difficulty="expert", score=83),
    ]
    assert confidence(many, skill_id="debugging", now=now)["confidence"] > confidence(one, skill_id="debugging", now=now)["confidence"]


def test_duplicate_id_does_not_inflate_quantity(now):
    item = evidence_item()
    result = confidence([item, dict(item)], skill_id="debugging", now=now)
    assert result["counts"]["independent_sessions"] == 1
    assert result["counts"]["evidence_items"] == 1
    assert result["warnings"]


def test_diverse_contexts_raise_diversity_factor(now):
    same = [
        evidence_item("EV-0000000000000001", session_id="S1"),
        evidence_item("EV-0000000000000002", session_id="S2", challenge_id="C2"),
    ]
    diverse = [
        evidence_item("EV-0000000000000001", session_id="S1", challenge_type="a", difficulty="easy"),
        evidence_item("EV-0000000000000002", session_id="S2", challenge_id="C2", challenge_type="b", difficulty="hard"),
    ]
    assert confidence(diverse, skill_id="debugging", now=now)["factors"]["diversity"] > confidence(same, skill_id="debugging", now=now)["factors"]["diversity"]


def test_inconsistent_sessions_reduce_consistency(now):
    consistent = [
        evidence_item("EV-0000000000000001", session_id="S1", score=80),
        evidence_item("EV-0000000000000002", session_id="S2", challenge_id="C2", score=82),
    ]
    inconsistent = [
        evidence_item("EV-0000000000000001", session_id="S1", score=20),
        evidence_item("EV-0000000000000002", session_id="S2", challenge_id="C2", score=95),
    ]
    assert confidence(inconsistent, skill_id="debugging", now=now)["factors"]["consistency"] < confidence(consistent, skill_id="debugging", now=now)["factors"]["consistency"]


def test_stale_evidence_reduces_freshness(now):
    fresh = evidence_item(timestamp="2026-08-14T01:00:00+00:00")
    stale = evidence_item(timestamp="2025-08-14T01:00:00+00:00")
    assert confidence([stale], skill_id="debugging", now=now)["factors"]["freshness"] < confidence([fresh], skill_id="debugging", now=now)["factors"]["freshness"]


def test_future_timestamp_is_not_treated_as_fresh(now):
    item = evidence_item(timestamp="2027-08-14T01:00:00+00:00")
    result = confidence([item], skill_id="debugging", now=now)
    assert result["factors"]["freshness"] == 0
    assert any("future" in warning for warning in result["warnings"])


def test_dependency_only_evidence_is_ignored(now):
    item = evidence_item(skill="problem_solving", score=None, direction="dependency")
    result = confidence([item], skill_id="problem_solving", now=now)
    assert result["confidence"] == 0


def test_neutral_first_failure_does_not_inflate_confidence(now):
    item = evidence_item(score=50, direction="neutral")
    result = confidence([item], skill_id="debugging", now=now)
    assert result["confidence"] == 0


def test_confidence_result_matches_schema(now):
    validate_payload(confidence([evidence_item()], skill_id="debugging", now=now), "confidence.schema.json")


def test_forged_evidence_cannot_inflate_confidence(now):
    forged = evidence_item(score=100, strength="strong", difficulty="expert")
    forged["performance_score"] = 99
    result = confidence([forged], skill_id="debugging", now=now)
    assert result["confidence"] == 0
    assert any("provenance" in warning for warning in result["warnings"])
