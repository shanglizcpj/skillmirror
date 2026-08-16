import copy
import json
import time

import pytest

from agents.examiner import examine
from skill_engine.adaptive import choose_policy
from skill_engine.schema_validation import validate_payload


def test_selects_unknown_skill_first(mirror):
    assert examine(mirror)["target_skill"] == "debugging"


def test_recent_challenge_penalty_prevents_immediate_repeat(mirror):
    updated = copy.deepcopy(mirror)
    debugging = next(item for item in updated["skills"] if item["skill_id"] == "debugging")
    debugging.update({"score": 85, "confidence": 0.30})
    result = examine(updated, previous_challenges=[{"target_skill": "debugging"}])
    assert result["target_skill"] == "testing"
    assert result["priority_breakdown"]["debugging"]["recent_repeat_penalty"] > 0


def test_unknown_or_duplicate_skill_is_rejected(mirror):
    bad = copy.deepcopy(mirror)
    bad["skills"].append({"skill_id": "debugging", "score": 50, "confidence": 0.5})
    with pytest.raises(ValueError):
        examine(bad)


def test_invalid_confidence_is_rejected(mirror):
    bad = copy.deepcopy(mirror)
    bad["skills"][0]["confidence"] = 2
    with pytest.raises(ValueError):
        examine(bad)


def test_llm_cannot_change_locked_target(mirror):
    baseline = examine(mirror)
    malicious = dict(baseline)
    malicious["target_skill"] = "coding"
    result = examine(mirror, llm=lambda _p: json.dumps(malicious))
    assert result["target_skill"] == "debugging"
    assert result["reasoning_source"] == "deterministic"


def test_valid_llm_can_only_refine_reason(mirror):
    baseline = examine(mirror)
    refined = dict(baseline)
    refined["reason"] = "Locked decision explained without inventing evidence."
    result = examine(mirror, llm=lambda _p: json.dumps(refined))
    assert result["target_skill"] == baseline["target_skill"]
    assert result["reason"] == refined["reason"]
    assert result["reasoning_source"] == "llm_refined_locked_decision"


def test_llm_timeout_uses_deterministic_reason(mirror):
    def slow(_prompt):
        time.sleep(0.05)
        return "{}"
    result = examine(mirror, llm=slow, llm_timeout_seconds=0.001)
    assert result["reasoning_source"] == "deterministic"


def test_examiner_result_matches_schema(mirror):
    validate_payload(examine(mirror), "examiner_output.schema.json")


@pytest.mark.parametrize("score,confidence,mode", [
    (40, 0.9, "teaching"),
    (90, 0.4, "verification"),
    (90, 0.9, "stretch"),
    (40, 0.3, "diagnostic"),
    (None, 0.0, "diagnostic"),
])
def test_adaptive_quadrants(score, confidence, mode):
    assert choose_policy(score, confidence)["mode"] == mode


def test_adaptive_rejects_non_finite():
    with pytest.raises(ValueError):
        choose_policy(80, float("nan"))
