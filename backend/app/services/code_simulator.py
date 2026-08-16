def evaluate_code(code: str) -> dict:
    test_names = [
        "Positive numbers",
        "Mixed numbers",
        "Negative numbers",
        "Boundary index",
        "Single element",
    ]

    stripped_code = code.strip()

    if (
        not stripped_code
        or "def find_max" not in stripped_code
    ):
        statuses = ["failed"] * 5

        return build_result(
            test_names=test_names,
            statuses=statuses,
            status="syntax_error",
            stdout="",
            stderr='SyntaxError: expected "find_max".',
            runtime=0.01,
        )

    boundary_bug = (
        "range(len(nums) + 1)" in stripped_code
        or "range(len(nums)+1)" in stripped_code
    )

    negative_bug = (
        "max_num = 0" in stripped_code
        or "max_num=0" in stripped_code
    )

    if boundary_bug:
        return build_result(
            test_names=test_names,
            statuses=["failed"] * 5,
            status="failed",
            stdout="",
            stderr="IndexError: list index out of range",
            runtime=0.02,
        )

    if negative_bug:
        return build_result(
            test_names=test_names,
            statuses=[
                "passed",
                "passed",
                "failed",
                "passed",
                "passed",
            ],
            status="failed",
            stdout="Execution completed.",
            stderr=(
                "AssertionError: expected -3, "
                "but received 0."
            ),
            runtime=0.02,
        )

    return build_result(
        test_names=test_names,
        statuses=["passed"] * 5,
        status="success",
        stdout="All tests passed.",
        stderr="",
        runtime=0.03,
    )


def build_result(
    test_names: list[str],
    statuses: list[str],
    status: str,
    stdout: str,
    stderr: str,
    runtime: float,
) -> dict:
    tests = [
        {
            "name": name,
            "status": test_status,
        }
        for name, test_status in zip(
            test_names,
            statuses,
        )
    ]

    passed = sum(
        1
        for test_status in statuses
        if test_status == "passed"
    )

    return {
        "status": status,
        "stdout": stdout,
        "stderr": stderr,
        "passed": passed,
        "total": len(statuses),
        "runtime": runtime,
        "tests": tests,
    }