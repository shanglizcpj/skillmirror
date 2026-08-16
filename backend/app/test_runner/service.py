from __future__ import annotations

from typing import Any
import json

from app.agent_orchestrator.store import challenge_store
from app.sandbox.executor import execute_python


RESULT_PREFIX = "__SKILLMIRROR_TEST_RESULT__:"


class TestRunnerError(RuntimeError):
    pass


def build_test_program(
    user_code: str,
    entry_point: str,
    test_cases: list[dict[str, Any]],
) -> str:
    cases_json = json.dumps(
        test_cases,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    harness = r'''
import json as _sm_json
import math as _sm_math

_sm_entry = __ENTRY_POINT__
_sm_cases = _sm_json.loads(__TEST_CASES__)
_sm_results = []
_sm_function = globals().get(_sm_entry)

for _sm_case in _sm_cases:
    _sm_visibility = str(
        _sm_case.get("visibility", "hidden")
    )

    _sm_result = {
        "case_id": str(
            _sm_case.get("case_id", "unknown")
        ),
        "visibility": _sm_visibility,
        "passed": False,
        "message": "",
    }

    if not callable(_sm_function):
        _sm_result["message"] = (
            "Required function was not found"
        )
        _sm_results.append(_sm_result)
        continue

    try:
        _sm_actual = _sm_function(
            *_sm_case.get("args", []),
            **_sm_case.get("kwargs", {}),
        )

        _sm_expected_exception = _sm_case.get(
            "expected_exception"
        )

        if _sm_expected_exception:
            _sm_result["message"] = (
                "Expected exception was not raised"
            )
        else:
            _sm_expected = _sm_case.get("expected")

            if isinstance(_sm_actual, float) or isinstance(
                _sm_expected,
                float,
            ):
                _sm_result["passed"] = _sm_math.isclose(
                    float(_sm_actual),
                    float(_sm_expected),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
            else:
                _sm_result["passed"] = (
                    _sm_actual == _sm_expected
                )

            if not _sm_result["passed"]:
                _sm_result["message"] = "Wrong result"

    except Exception as _sm_exception:
        _sm_expected_exception = _sm_case.get(
            "expected_exception"
        )

        _sm_actual_exception = type(
            _sm_exception
        ).__name__

        if (
            _sm_expected_exception
            and _sm_actual_exception
            == _sm_expected_exception
        ):
            _sm_result["passed"] = True
        else:
            _sm_result["message"] = (
                "Raised " + _sm_actual_exception
            )

    _sm_results.append(_sm_result)

_sm_public = [
    item for item in _sm_results
    if item["visibility"] == "public"
]

_sm_hidden = [
    item for item in _sm_results
    if item["visibility"] != "public"
]

_sm_summary = {
    "passed": sum(
        1 for item in _sm_results
        if item["passed"]
    ),
    "total": len(_sm_results),
    "public_passed": sum(
        1 for item in _sm_public
        if item["passed"]
    ),
    "public_total": len(_sm_public),
    "hidden_passed": sum(
        1 for item in _sm_hidden
        if item["passed"]
    ),
    "hidden_total": len(_sm_hidden),
    "results": _sm_results,
}

print(
    "__SKILLMIRROR_TEST_RESULT__:"
    + _sm_json.dumps(
        _sm_summary,
        ensure_ascii=False,
        separators=(",", ":"),
    )
)
'''

    harness = harness.replace(
        "__ENTRY_POINT__",
        repr(entry_point),
    )

    harness = harness.replace(
        "__TEST_CASES__",
        repr(cases_json),
    )

    return user_code.rstrip() + "\n\n" + harness


def extract_summary(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith(RESULT_PREFIX):
            content = line[len(RESULT_PREFIX):]

            try:
                summary = json.loads(content)
            except json.JSONDecodeError as exc:
                raise TestRunnerError(
                    "Sandbox returned invalid test JSON"
                ) from exc

            if not isinstance(summary, dict):
                raise TestRunnerError(
                    "Test result is not an object"
                )

            return summary

    raise TestRunnerError(
        "Sandbox did not return test results"
    )


def sanitize_failures(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failures = []

    for item in results:
        if item.get("passed"):
            continue

        if item.get("visibility") == "public":
            failures.append({
                "visibility": "public",
                "case_id": item.get("case_id"),
                "message": str(
                    item.get("message")
                    or "Public test failed"
                )[:300],
            })
        else:
            failures.append({
                "visibility": "hidden",
                "message": "A hidden test failed",
            })

    return failures


def run_session_tests(
    *,
    user_id: str,
    session_id: str,
    code: str,
    timeout_seconds: int = 3,
) -> dict[str, Any]:
    record = challenge_store.get(session_id)

    if record is None:
        raise TestRunnerError(
            "Challenge session not found"
        )

    if record["user_id"] != user_id:
        raise TestRunnerError(
            "Challenge does not belong to this user"
        )

    if record["status"] != "active":
        raise TestRunnerError(
            "Challenge is not active"
        )

    server_challenge = record["server_challenge"]
    entry_point = server_challenge.get("entry_point")
    test_cases = server_challenge.get("test_cases")

    if not isinstance(entry_point, str):
        raise TestRunnerError(
            "Stored entry_point is invalid"
        )

    if not isinstance(test_cases, list):
        raise TestRunnerError(
            "Stored test_cases are invalid"
        )

    program = build_test_program(
        code,
        entry_point,
        test_cases,
    )

    execution = execute_python(
        program,
        timeout_seconds=timeout_seconds,
    )

    public_total = sum(
        1 for case in test_cases
        if case.get("visibility") == "public"
    )

    hidden_total = len(test_cases) - public_total

    if execution.get("status") == "timeout":
        return {
            "status": "timeout",
            "challenge_id": record["challenge_id"],
            "challenge_digest": record["challenge_digest"],
            "passed": 0,
            "total": len(test_cases),
            "public_passed": 0,
            "public_total": public_total,
            "hidden_passed": 0,
            "hidden_total": hidden_total,
            "failed_cases": [],
            "runtime": float(
                execution.get("runtime", 0)
            ),
            "sandbox_mode": str(
                execution.get("sandbox_mode", "unknown")
            ),
        }

    try:
        summary = extract_summary(
            str(execution.get("stdout", ""))
        )
    except TestRunnerError:
        return {
            "status": "error",
            "challenge_id": record["challenge_id"],
            "challenge_digest": record["challenge_digest"],
            "passed": 0,
            "total": len(test_cases),
            "public_passed": 0,
            "public_total": public_total,
            "hidden_passed": 0,
            "hidden_total": hidden_total,
            "failed_cases": [{
                "visibility": "public",
                "case_id": "execution",
                "message": str(
                    execution.get("stderr")
                    or "Execution failed"
                )[:300],
            }],
            "runtime": float(
                execution.get("runtime", 0)
            ),
            "sandbox_mode": str(
                execution.get("sandbox_mode", "unknown")
            ),
        }

    passed = int(summary.get("passed", 0))
    total = int(summary.get("total", 0))

    return {
        "status": (
            "passed"
            if total > 0 and passed == total
            else "failed"
        ),
        "challenge_id": record["challenge_id"],
        "challenge_digest": record["challenge_digest"],
        "passed": passed,
        "total": total,
        "public_passed": int(
            summary.get("public_passed", 0)
        ),
        "public_total": int(
            summary.get("public_total", 0)
        ),
        "hidden_passed": int(
            summary.get("hidden_passed", 0)
        ),
        "hidden_total": int(
            summary.get("hidden_total", 0)
        ),
        "failed_cases": sanitize_failures(
            summary.get("results", [])
        ),
        "runtime": float(
            execution.get("runtime", 0)
        ),
        "sandbox_mode": str(
            execution.get("sandbox_mode", "unknown")
        ),
    }