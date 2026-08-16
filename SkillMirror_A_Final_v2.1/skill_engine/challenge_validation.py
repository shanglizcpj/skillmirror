"""Fail-closed validation for generated Python challenges.

This is not the learner-code sandbox owned by member B.  It is an A-side quality
gate that statically restricts generated code and executes only the challenge
starter/reference solution in an isolated subprocess to prove the test oracle is
self-consistent.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict, Iterable, List
import ast
import json
import math
import subprocess
import sys

from .schema_validation import validate_payload
from .skill_tree import validate_skill_pair

SAFE_CALLS = {
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int",
    "isinstance", "len", "list", "max", "min", "range", "reversed",
    "round", "set", "sorted", "str", "sum", "tuple", "zip",
    "TypeError", "ValueError", "ZeroDivisionError",
}
FORBIDDEN_NODES = (
    ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef, ast.Await,
    ast.Global, ast.Nonlocal, ast.With, ast.AsyncWith, ast.Delete, ast.Lambda,
    ast.While, ast.Yield, ast.YieldFrom,
)


def canonical_digest(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()


def inspect_safe_python(code: str) -> List[str]:
    errors: List[str] = []
    if not isinstance(code, str) or not code.strip():
        return ["code must be a non-empty string"]
    if len(code) > 20_000:
        return ["code exceeds 20 KB validation limit"]
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error at line {exc.lineno}: {exc.msg}"]
    local_functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            errors.append(f"forbidden syntax: {type(node).__name__}")
        elif isinstance(node, ast.Attribute):
            errors.append("attribute access is not allowed in generated validation code")
        elif isinstance(node, ast.Name) and node.id.startswith("__"):
            errors.append(f"dunder name is not allowed: {node.id}")
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_CALLS | local_functions:
                called = getattr(node.func, "id", type(node.func).__name__)
                errors.append(f"call is not allow-listed: {called}")
    return sorted(set(errors))


_RUNNER = r'''
import json, math, sys
try:
    import resource
except ImportError:
    resource = None
if resource is not None:
    if hasattr(resource, "RLIMIT_CPU"):
        resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
    if hasattr(resource, "RLIMIT_AS"):
        resource.setrlimit(resource.RLIMIT_AS, (192 * 1024 * 1024, 192 * 1024 * 1024))
payload = json.loads(sys.stdin.read())
safe_builtins = {name: getattr(__builtins__, name) for name in payload["safe_calls"] if hasattr(__builtins__, name)}
namespace = {"__builtins__": safe_builtins}
results = []
try:
    exec(payload["code"], namespace, namespace)
    fn = namespace[payload["entry_point"]]
    for case in payload["test_cases"]:
        item = {"case_id": case["case_id"], "passed": False}
        try:
            actual = fn(*case.get("args", []), **case.get("kwargs", {}))
            if case.get("expected_exception"):
                item["detail"] = "expected exception was not raised"
            else:
                expected = case.get("expected")
                if isinstance(actual, float) or isinstance(expected, float):
                    ok = math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-9)
                else:
                    ok = actual == expected
                item.update({"passed": ok, "actual": actual, "expected": expected})
        except Exception as exc:
            expected_exc = case.get("expected_exception")
            item.update({"passed": type(exc).__name__ == expected_exc, "exception": type(exc).__name__})
        results.append(item)
except Exception as exc:
    print(json.dumps({"runner_error": type(exc).__name__, "message": str(exc), "results": results}))
    raise SystemExit(0)
print(json.dumps({"results": results}))
'''


def run_code_tests(
    code: str,
    entry_point: str,
    test_cases: Iterable[Dict[str, Any]],
    *,
    timeout_seconds: float = 2.0,
) -> Dict[str, Any]:
    safety_errors = inspect_safe_python(code)
    cases = list(test_cases)
    if safety_errors:
        return {"passed": 0, "total": len(cases), "results": [], "safety_errors": safety_errors}
    payload = {
        "code": code,
        "entry_point": entry_point,
        "test_cases": cases,
        "safe_calls": sorted(SAFE_CALLS),
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-S", "-c", _RUNNER],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=max(0.1, timeout_seconds),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": len(cases), "results": [], "timeout": True}
    try:
        output = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "passed": 0,
            "total": len(cases),
            "results": [],
            "runner_error": "invalid_runner_output",
        }
    results = output.get("results", [])
    return {
        "passed": sum(1 for item in results if item.get("passed")),
        "total": len(cases),
        "results": results,
        **({"runner_error": output["runner_error"]} if output.get("runner_error") else {}),
    }


def _validate_cases(cases: Any) -> List[str]:
    if not isinstance(cases, list) or len(cases) < 2:
        return ["test_cases must contain at least two cases"]
    errors: List[str] = []
    ids = set()
    hidden = 0
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"test_cases[{index}] must be an object")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"test_cases[{index}].case_id is required")
        elif case_id in ids:
            errors.append(f"duplicate case_id: {case_id}")
        ids.add(case_id)
        if case.get("visibility") == "hidden":
            hidden += 1
        if "expected" not in case and "expected_exception" not in case:
            errors.append(f"{case_id or index}: expected or expected_exception is required")
        if not isinstance(case.get("args", []), list) or not isinstance(case.get("kwargs", {}), dict):
            errors.append(f"{case_id or index}: args/kwargs have invalid types")
    if hidden == 0:
        errors.append("at least one hidden test is required")
    return errors


def validate_challenge(challenge: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    # Generation provenance is attached only after the challenge itself has
    # passed this gate.  Strip it before re-validation so callers can safely
    # validate either the raw challenge or the enriched internal record.
    challenge_core = {
        key: value for key, value in challenge.items()
        if key not in {"generation_source", "content_hash", "validation_report", "provenance"}
    }
    try:
        validate_payload(challenge_core, "challenge.schema.json")
    except ValueError as exc:
        errors.append(str(exc))
    target_skill = challenge.get("target_skill")
    target_subskill = challenge.get("target_subskill")
    if isinstance(target_skill, str) and isinstance(target_subskill, str):
        if not validate_skill_pair(target_skill, target_subskill):
            errors.append("target_subskill does not belong to target_skill")
    errors.extend(_validate_cases(challenge.get("test_cases")))
    hints = challenge.get("hints")
    if not isinstance(hints, list) or len(hints) != 3 or not all(isinstance(h, str) and h.strip() for h in hints):
        errors.append("exactly three non-empty progressive hints are required")
    starter_errors = inspect_safe_python(challenge.get("starter_code", ""))
    reference_errors = inspect_safe_python(challenge.get("reference_solution", ""))
    errors.extend(f"starter_code: {msg}" for msg in starter_errors)
    errors.extend(f"reference_solution: {msg}" for msg in reference_errors)

    cases = challenge.get("test_cases") if isinstance(challenge.get("test_cases"), list) else []
    reference_summary: Dict[str, Any] = {"passed": 0, "total": len(cases)}
    starter_summary: Dict[str, Any] = {"passed": 0, "total": len(cases)}
    if not starter_errors and not reference_errors and not _validate_cases(cases):
        reference_summary = run_code_tests(challenge["reference_solution"], challenge["entry_point"], cases)
        starter_summary = run_code_tests(challenge["starter_code"], challenge["entry_point"], cases)
        if reference_summary.get("passed") != reference_summary.get("total"):
            errors.append("reference_solution does not pass every declared test")
        if starter_summary.get("total", 0) and starter_summary.get("passed") == starter_summary.get("total"):
            errors.append("starter_code already passes every test; challenge has no observable gap")

    public = {
        k: v for k, v in challenge_core.items()
        if k != "reference_solution"
    }
    content_hash = canonical_digest(public)
    return {
        "valid": not errors,
        "errors": errors,
        "reference_test_summary": {k: v for k, v in reference_summary.items() if k != "results"},
        "starter_test_summary": {k: v for k, v in starter_summary.items() if k != "results"},
        "content_hash": content_hash,
        "validator_version": "challenge-validator/2.0",
    }
