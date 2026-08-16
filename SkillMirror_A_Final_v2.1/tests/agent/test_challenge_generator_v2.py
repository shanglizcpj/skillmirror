from copy import deepcopy
import json
import time

from agents.challenge_generator import TEMPLATES, generate_challenge
from skill_engine.challenge_validation import inspect_safe_python, run_code_tests, validate_challenge


def _llm_payload(skill="debugging"):
    return json.dumps(deepcopy(TEMPLATES[skill]), ensure_ascii=False)


def test_valid_model_challenge_is_oracle_validated():
    challenge = generate_challenge(
        {"target_skill": "debugging", "difficulty": "medium"},
        llm=lambda _prompt: _llm_payload("debugging"),
    )
    assert challenge["generation_source"] == "llm_oracle_validated"


def test_malformed_model_json_falls_back():
    result = generate_challenge({"target_skill": "debugging", "difficulty": "medium"}, llm=lambda _p: "bad")
    assert result["generation_source"] == "fixed_verified_template"


def test_wrong_target_model_falls_back():
    result = generate_challenge({"target_skill": "debugging", "difficulty": "medium"}, llm=lambda _p: _llm_payload("coding"))
    assert result["target_skill"] == "debugging"
    assert result["generation_source"] == "fixed_verified_template"


def test_broken_reference_oracle_falls_back():
    payload = deepcopy(TEMPLATES["debugging"])
    payload["reference_solution"] = "def discounted_total(prices, threshold=100):\n    return -1\n"
    result = generate_challenge({"target_skill": "debugging", "difficulty": "medium"}, llm=lambda _p: json.dumps(payload))
    assert result["generation_source"] == "fixed_verified_template"


def test_unsafe_import_falls_back():
    payload = deepcopy(TEMPLATES["debugging"])
    payload["reference_solution"] = "import os\ndef discounted_total(prices, threshold=100):\n    return 0\n"
    result = generate_challenge({"target_skill": "debugging", "difficulty": "medium"}, llm=lambda _p: json.dumps(payload))
    assert result["generation_source"] == "fixed_verified_template"


def test_llm_timeout_falls_back():
    def slow(_prompt):
        time.sleep(0.05)
        return _llm_payload("debugging")
    result = generate_challenge(
        {"target_skill": "debugging", "difficulty": "medium"},
        llm=slow,
        llm_timeout_seconds=0.001,
    )
    assert result["generation_source"] == "fixed_verified_template"


def test_dangerous_calls_are_statically_refused():
    errors = inspect_safe_python("def f():\n    return open('x')\n")
    assert any("open" in error for error in errors)


def test_attribute_access_is_statically_refused():
    errors = inspect_safe_python("def f(x):\n    return x.__class__\n")
    assert any("attribute access" in error for error in errors)


def test_test_runner_never_executes_unsafe_code():
    result = run_code_tests("import os\ndef f():\n    return 1\n", "f", [{"case_id": "x", "args": [], "kwargs": {}, "expected": 1}])
    assert result["passed"] == 0
    assert result["safety_errors"]


def test_challenge_requires_exactly_three_hints():
    payload = deepcopy(TEMPLATES["debugging"])
    payload["hints"] = payload["hints"][:2]
    report = validate_challenge(payload)
    assert not report["valid"]
    assert any("three" in error for error in report["errors"])


def test_invalid_target_skill_is_rejected_instead_of_silently_remapped():
    import pytest
    with pytest.raises(ValueError):
        generate_challenge({"target_skill": "imaginary", "difficulty": "medium"})


def test_subskill_must_belong_to_target_skill():
    import pytest
    with pytest.raises(ValueError):
        generate_challenge({
            "target_skill": "coding", "target_subskill": "boundary_awareness", "difficulty": "medium"
        })


def test_llm_challenge_with_cross_skill_subskill_falls_back():
    payload = deepcopy(TEMPLATES["debugging"])
    payload["target_subskill"] = "function_design"
    result = generate_challenge(
        {"target_skill": "debugging", "target_subskill": "boundary_awareness", "difficulty": "medium"},
        llm=lambda _p: json.dumps(payload),
    )
    assert result["generation_source"] == "fixed_verified_template"
