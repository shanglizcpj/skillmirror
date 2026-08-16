from conftest import TEST_A_SECRET, TEST_CHALLENGE_DIGEST, verification_record

from skill_engine.evidence import materialize_evidence
from skill_engine.schema_validation import validate_payload


def context(**overrides):
    value = {
        "user_id": "U1",
        "session_id": "S1",
        "challenge_id": "DBG001",
        "challenge_digest": TEST_CHALLENGE_DIGEST,
        "challenge_type": "debugging_runtime",
        "target_skill": "debugging",
        "target_subskill": "boundary_awareness",
        "difficulty": "medium",
        "timestamp": "2026-08-14T01:00:00+00:00",
    }
    value.update(overrides)
    return value


def materialize(candidates, *, context, verification_records):
    return materialize_evidence(
        candidates,
        context=context,
        verification_records=verification_records,
        provenance_secret=TEST_A_SECRET,
    )


def test_unknown_event_is_rejected():
    result = materialize([{"event": "invented", "verification_refs": ["RUN1"]}], context=context(), verification_records=[verification_record()])
    assert result["accepted"] == []
    assert result["rejected"][0]["reason"] == "unknown_event"


def test_missing_verification_refs_is_rejected():
    result = materialize([{"event": "challenge_tests_passed"}], context=context(), verification_records=[])
    assert result["accepted"] == []
    assert result["rejected"][0]["reason"] == "verification_refs_required"


def test_unverified_record_is_rejected():
    record = verification_record(status="unverified")
    result = materialize([{"event": "challenge_tests_passed", "verification_refs": ["RUN1"]}], context=context(), verification_records=[record])
    assert result["accepted"] == []


def test_caller_declared_verified_without_a_provenance_is_rejected():
    record = verification_record()
    record.pop("provenance")
    record["status"] = "verified"
    result = materialize(
        [{"event": "challenge_tests_passed", "verification_refs": ["RUN1"]}],
        context=context(), verification_records=[record],
    )
    assert result["accepted"] == []


def test_cross_session_record_is_rejected():
    record = verification_record(session_id="OTHER")
    result = materialize([{"event": "challenge_tests_passed", "verification_refs": ["RUN1"]}], context=context(), verification_records=[record])
    assert result["accepted"] == []


def test_malformed_verification_digest_is_rejected():
    record = verification_record()
    record["payload_digest"] = "sha256:" + "z" * 64
    result = materialize(
        [{"event": "challenge_tests_passed", "verification_refs": ["RUN1"]}],
        context=context(), verification_records=[record],
    )
    assert result["accepted"] == []


def test_invalid_evidence_timestamp_fails_schema_materialization():
    result = materialize(
        [{"event": "challenge_tests_passed", "verification_refs": ["RUN1"]}],
        context=context(timestamp="not-a-date"),
        verification_records=[verification_record()],
    )
    assert result["accepted"] == []
    assert "date-time" in result["rejected"][0]["reason"]


def test_candidate_cannot_override_rule_owned_score_or_skill():
    candidate = {
        "event": "challenge_tests_passed",
        "verification_refs": ["RUN1"],
        "skill": "coding",
        "sub_skill": "syntax_fluency",
        "strength": "weak",
        "performance_score": 0,
        "confidence": 0,
    }
    item = materialize([candidate], context=context(), verification_records=[verification_record()])["accepted"][0]
    assert item["skill"] == "debugging"
    assert item["sub_skill"] == "boundary_awareness"
    assert item["strength"] == "strong"
    assert item["performance_score"] == 92
    assert item["reliability"] == 0.98


def test_duplicate_candidate_has_stable_id_and_no_double_count():
    candidate = {"event": "challenge_tests_passed", "verification_refs": ["RUN1"]}
    result = materialize([candidate, candidate], context=context(), verification_records=[verification_record()])
    assert len(result["accepted"]) == 1
    assert result["accepted"][0]["evidence_id"].startswith("EV-")
    assert result["rejected"][0]["reason"] == "duplicate_candidate"


def test_hint_level_is_derived_from_verified_hint_record():
    records = [verification_record(), verification_record("H3", "hint_record", hint_level="level_3")]
    candidate = {"event": "challenge_tests_passed", "verification_refs": ["RUN1", "H3"], "hint_level": "none"}
    item = materialize([candidate], context=context(), verification_records=records)["accepted"][0]
    assert item["hint_level"] == "level_3"


def test_dynamic_outcome_rule_maps_to_testing_target():
    ctx = context(
        challenge_id="TST001",
        challenge_type="testing_edge_cases",
        target_skill="testing",
        target_subskill="boundary_testing",
    )
    record = verification_record(
        challenge_id="TST001", target_skill="testing", target_subskill="boundary_testing"
    )
    item = materialize(
        [{"event": "challenge_tests_passed", "verification_refs": ["RUN1"]}],
        context=ctx,
        verification_records=[record],
    )["accepted"][0]
    assert (item["skill"], item["sub_skill"]) == ("testing", "boundary_testing")


def test_materialized_evidence_matches_schema():
    item = materialize(
        [{"event": "challenge_tests_passed", "verification_refs": ["RUN1"], "reason": "verified"}],
        context=context(),
        verification_records=[verification_record()],
    )["accepted"][0]
    validate_payload(item, "evidence.schema.json")
