from pathlib import Path
import json

from jsonschema import Draft202012Validator

from agents.challenge_generator import TEMPLATES, generate_challenge, public_challenge
from skill_engine.challenge_validation import validate_challenge
from skill_engine.schema_validation import load_schema, validate_payload
from skill_engine.skill_tree import get_subskills, load_skill_tree, validate_skill_pair


ROOT = Path(__file__).resolve().parents[1]


def test_required_top_level_structure_exists():
    for name in ["agents", "skill_engine", "prompts", "schemas", "tests", "examples", "docs", "demo"]:
        assert (ROOT / name).is_dir()
    for name in ["API_CONTRACT_A.md", "README.md", "requirements.txt"]:
        assert (ROOT / name).is_file()


def test_every_json_file_parses():
    for path in ROOT.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_every_schema_is_draft_2020_valid():
    for path in (ROOT / "schemas").glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_skill_tree_has_required_five_skills():
    tree = load_skill_tree()
    assert [item["id"] for item in tree["root_skill"]["children"]] == [
        "coding", "debugging", "testing", "problem_solving", "code_reading"
    ]


def test_skill_tree_pairs_are_validated():
    assert validate_skill_pair("debugging", "boundary_awareness")
    assert not validate_skill_pair("coding", "boundary_awareness")
    assert "fix_verification" in get_subskills("debugging")


def test_all_fixed_templates_pass_executable_oracle_gate():
    for skill in TEMPLATES:
        report = validate_challenge(generate_challenge({"target_skill": skill, "difficulty": "medium"}))
        assert report["valid"], (skill, report["errors"])
        assert report["reference_test_summary"]["passed"] == report["reference_test_summary"]["total"]
        assert report["starter_test_summary"]["passed"] < report["starter_test_summary"]["total"]


def test_public_challenge_removes_oracle_and_hidden_tests():
    internal = generate_challenge({"target_skill": "debugging", "difficulty": "easy"})
    public = public_challenge(internal)
    assert "reference_solution" not in public
    assert "hidden_bugs" not in public
    assert "test_cases" not in public
    assert all(case["visibility"] == "public" for case in public["public_tests"])


def test_prompt_files_are_runtime_templates():
    for name in ["examiner", "challenge_generator", "coach", "evaluator"]:
        text = (ROOT / "prompts" / f"{name}.txt").read_text(encoding="utf-8")
        assert "{{INPUT_JSON}}" in text
        assert "{{OUTPUT_SCHEMA}}" in text
        assert "untrusted" in text.lower()


def test_committed_evidence_examples_match_runtime_schema():
    items = json.loads((ROOT / "examples" / "evidence_examples.json").read_text(encoding="utf-8"))
    assert items
    for item in items:
        validate_payload(item, "evidence.schema.json")


def test_committed_demo_output_carries_simulation_disclosure():
    result = json.loads((ROOT / "examples" / "full_a_demo_output.json").read_text(encoding="utf-8"))
    assert result["demo_disclosure"].startswith("Simulated learner")
