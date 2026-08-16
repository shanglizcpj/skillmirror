from __future__ import annotations

from typing import Any

from app.agent_orchestrator.store import (
    challenge_store,
)
from app.sandbox.executor import (
    execute_test_suite,
)


class TestRunnerError(RuntimeError):
    pass


def sanitize_failures(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    for result in results:
        if result["passed"]:
            continue

        if result["visibility"] == "public":
            failures.append(
                {
                    "visibility": "public",
                    "case_id":
                        result["case_id"],
                    "message": str(
                        result.get("message")
                        or "Public test failed"
                    )[:300],
                }
            )
        else:
            failures.append(
                {
                    "visibility": "hidden",
                    "message":
                        "A hidden test failed",
                }
            )

    return failures


def error_response(
    *,
    record: dict[str, Any],
    test_cases: list[dict[str, Any]],
    execution: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    public_total = sum(
        1
        for case in test_cases
        if case.get("visibility") == "public"
    )

    hidden_total = (
        len(test_cases) - public_total
    )

    return {
        "status": status,
        "challenge_id":
            record["challenge_id"],
        "challenge_digest":
            record["challenge_digest"],
        "passed": 0,
        "total": len(test_cases),
        "public_passed": 0,
        "public_total": public_total,
        "hidden_passed": 0,
        "hidden_total": hidden_total,
        "failed_cases": [
            {
                "visibility": (
                    "public"
                    if public_total > 0
                    else "hidden"
                ),
                "case_id": "execution",
                "message": str(
                    execution.get("stderr")
                    or "Trusted execution failed"
                )[:300],
            }
        ],
        "runtime": float(
            execution.get("runtime", 0)
        ),
        "sandbox_mode": str(
            execution.get(
                "sandbox_mode",
                "unknown",
            )
        ),
    }


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

    server_challenge = (
        record["server_challenge"]
    )

    entry_point = server_challenge.get(
        "entry_point"
    )

    test_cases = server_challenge.get(
        "test_cases"
    )

    if not isinstance(entry_point, str):
        raise TestRunnerError(
            "Stored entry_point is invalid"
        )

    if (
        not isinstance(test_cases, list)
        or not test_cases
    ):
        raise TestRunnerError(
            "Stored test_cases are invalid"
        )

    if not all(
        isinstance(case, dict)
        for case in test_cases
    ):
        raise TestRunnerError(
            "Stored test case is invalid"
        )

    execution = execute_test_suite(
        code=code,
        entry_point=entry_point,
        test_cases=test_cases,
        timeout_seconds=timeout_seconds,
    )

    if execution.get("status") == "timeout":
        return error_response(
            record=record,
            test_cases=test_cases,
            execution=execution,
            status="timeout",
        )

    if execution.get("status") != "success":
        return error_response(
            record=record,
            test_cases=test_cases,
            execution=execution,
            status="error",
        )

    controller_result = execution.get(
        "controller_result"
    )

    if not isinstance(
        controller_result,
        dict,
    ):
        return error_response(
            record=record,
            test_cases=test_cases,
            execution={
                **execution,
                "stderr":
                    "Controller result is missing.",
            },
            status="error",
        )

    raw_results = controller_result.get(
        "results"
    )

    if (
        not isinstance(raw_results, list)
        or len(raw_results)
        != len(test_cases)
    ):
        return error_response(
            record=record,
            test_cases=test_cases,
            execution={
                **execution,
                "stderr": (
                    "Controller result count "
                    "does not match stored tests."
                ),
            },
            status="error",
        )

    # case_id、visibility和测试总数始终取自
    # B后端保存的server challenge。
    normalized_results: list[
        dict[str, Any]
    ] = []

    for test_case, raw_result in zip(
        test_cases,
        raw_results,
        strict=True,
    ):
        if not isinstance(raw_result, dict):
            return error_response(
                record=record,
                test_cases=test_cases,
                execution={
                    **execution,
                    "stderr":
                        "Invalid controller case result.",
                },
                status="error",
            )

        normalized_results.append(
            {
                "case_id": str(
                    test_case.get(
                        "case_id",
                        "unknown",
                    )
                ),
                "visibility": str(
                    test_case.get(
                        "visibility",
                        "hidden",
                    )
                ),
                "passed": (
                    raw_result.get("passed")
                    is True
                ),
                "message": str(
                    raw_result.get("message")
                    or ""
                )[:300],
            }
        )

    public_results = [
        result
        for result in normalized_results
        if result["visibility"] == "public"
    ]

    hidden_results = [
        result
        for result in normalized_results
        if result["visibility"] != "public"
    ]

    passed = sum(
        1
        for result in normalized_results
        if result["passed"]
    )

    total = len(test_cases)

    public_passed = sum(
        1
        for result in public_results
        if result["passed"]
    )

    hidden_passed = sum(
        1
        for result in hidden_results
        if result["passed"]
    )

    return {
        "status": (
            "passed"
            if passed == total
            else "failed"
        ),
        "challenge_id":
            record["challenge_id"],
        "challenge_digest":
            record["challenge_digest"],
        "passed": passed,
        "total": total,
        "public_passed":
            public_passed,
        "public_total":
            len(public_results),
        "hidden_passed":
            hidden_passed,
        "hidden_total":
            len(hidden_results),
        "failed_cases":
            sanitize_failures(
                normalized_results
            ),
        "runtime": float(
            execution.get("runtime", 0)
        ),
        "sandbox_mode": str(
            execution.get(
                "sandbox_mode",
                "docker-isolated-controller",
            )
        ),
    }