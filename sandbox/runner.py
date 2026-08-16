from __future__ import annotations

from typing import Any
import json
import math
import os
import signal
import sys


PROTOCOL_VERSION = 2
MAX_REQUEST_LENGTH = 200_000
MAX_CHILD_RESULT_LENGTH = 65_536


def write_all(
    file_descriptor: int,
    data: bytes,
) -> None:
    position = 0

    while position < len(data):
        written = os.write(
            file_descriptor,
            data[position:],
        )

        if written <= 0:
            raise RuntimeError(
                "Unable to write child result"
            )

        position += written


def child_execute(
    *,
    write_descriptor: int,
    code: str,
    entry_point: str,
    args: list[Any],
    kwargs: dict[str, Any],
) -> None:
    trusted_compile = compile
    trusted_exec = exec
    trusted_json_dumps = json.dumps
    trusted_write_all = write_all
    trusted_exit = os._exit

    # 学习者 stdout/stderr 不进入可信控制器输出。
    null_descriptor = os.open(
        os.devnull,
        os.O_WRONLY,
    )

    os.dup2(null_descriptor, 1)
    os.dup2(null_descriptor, 2)

    if null_descriptor not in {1, 2}:
        os.close(null_descriptor)

    namespace: dict[str, Any] = {
        "__name__": "solution",
        "__file__": "solution.py",
    }

    result: dict[str, Any]

    try:
        compiled = trusted_compile(
            code,
            "solution.py",
            "exec",
        )

        trusted_exec(
            compiled,
            namespace,
            namespace,
        )

        function = namespace.get(entry_point)

        if not callable(function):
            result = {
                "kind": "missing_function",
            }
        else:
            try:
                actual = function(
                    *args,
                    **kwargs,
                )

                result = {
                    "kind": "return",
                    "value": actual,
                }

            except BaseException as exception:
                result = {
                    "kind": "exception",
                    "exception_type":
                        type(exception).__name__,
                }

    except BaseException as exception:
        result = {
            "kind": "load_error",
            "exception_type":
                type(exception).__name__,
        }

    try:
        encoded = trusted_json_dumps(
            result,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    except BaseException:
        encoded = trusted_json_dumps(
            {
                "kind": "invalid_return",
            },
            separators=(",", ":"),
        ).encode("utf-8")

    if len(encoded) > MAX_CHILD_RESULT_LENGTH:
        encoded = b'{"kind":"result_too_large"}'

    try:
        trusted_write_all(
            write_descriptor,
            encoded,
        )
    except BaseException:
        pass

    try:
        os.close(write_descriptor)
    except OSError:
        pass

    trusted_exit(0)


def compare_result(
    *,
    child_result: dict[str, Any],
    test_case: dict[str, Any],
) -> tuple[bool, str]:
    expected_exception = test_case.get(
        "expected_exception"
    )

    kind = child_result.get("kind")

    if expected_exception:
        if (
            kind == "exception"
            and child_result.get("exception_type")
            == expected_exception
        ):
            return True, ""

        if kind == "exception":
            return (
                False,
                "Raised "
                + str(
                    child_result.get(
                        "exception_type",
                        "unknown exception",
                    )
                ),
            )

        return False, "Expected exception was not raised"

    if kind == "missing_function":
        return False, "Required function was not found"

    if kind == "load_error":
        return (
            False,
            "Code loading failed: "
            + str(
                child_result.get(
                    "exception_type",
                    "unknown error",
                )
            ),
        )

    if kind == "exception":
        return (
            False,
            "Raised "
            + str(
                child_result.get(
                    "exception_type",
                    "unknown exception",
                )
            ),
        )

    if kind != "return":
        return False, "Execution did not return a trusted result"

    actual = child_result.get("value")
    expected = test_case.get("expected")

    if (
        isinstance(actual, float)
        or isinstance(expected, float)
    ):
        try:
            passed = math.isclose(
                float(actual),
                float(expected),
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
        except (TypeError, ValueError):
            passed = False
    else:
        passed = actual == expected

    if passed:
        return True, ""

    return False, "Wrong result"


def run_case(
    *,
    code: str,
    entry_point: str,
    test_case: dict[str, Any],
) -> dict[str, Any]:
    read_descriptor, write_descriptor = os.pipe()

    process_id = os.fork()

    if process_id == 0:
        os.close(read_descriptor)

        child_execute(
            write_descriptor=write_descriptor,
            code=code,
            entry_point=entry_point,
            args=list(
                test_case.get("args", [])
            ),
            kwargs=dict(
                test_case.get("kwargs", {})
            ),
        )

        os._exit(125)

    os.close(write_descriptor)

    chunks: list[bytes] = []
    total_length = 0
    oversized = False

    try:
        while True:
            chunk = os.read(
                read_descriptor,
                8192,
            )

            if not chunk:
                break

            total_length += len(chunk)

            if total_length > MAX_CHILD_RESULT_LENGTH:
                oversized = True

                try:
                    os.kill(
                        process_id,
                        signal.SIGKILL,
                    )
                except ProcessLookupError:
                    pass

                break

            chunks.append(chunk)

    finally:
        os.close(read_descriptor)

    _, process_status = os.waitpid(
        process_id,
        0,
    )

    if oversized:
        child_result = {
            "kind": "result_too_large",
        }

    elif (
        not os.WIFEXITED(process_status)
        or os.WEXITSTATUS(process_status) != 0
    ):
        child_result = {
            "kind": "child_terminated",
        }

    else:
        raw_result = b"".join(chunks)

        try:
            decoded = json.loads(
                raw_result.decode("utf-8")
            )

            if not isinstance(decoded, dict):
                raise ValueError(
                    "Child result must be an object"
                )

            child_result = decoded

        except (UnicodeDecodeError, ValueError):
            child_result = {
                "kind": "invalid_child_result",
            }

    passed, message = compare_result(
        child_result=child_result,
        test_case=test_case,
    )

    return {
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
        "passed": passed,
        "message": message,
    }


def main() -> None:
    request_text = sys.stdin.read(
        MAX_REQUEST_LENGTH + 1
    )

    if len(request_text) > MAX_REQUEST_LENGTH:
        print(
            "Sandbox request is too large.",
            file=sys.stderr,
        )
        raise SystemExit(121)

    try:
        request = json.loads(request_text)
    except json.JSONDecodeError:
        print(
            "Sandbox request is not valid JSON.",
            file=sys.stderr,
        )
        raise SystemExit(122)

    if not isinstance(request, dict):
        raise SystemExit(122)

    code = request.get("code")
    entry_point = request.get("entry_point")
    test_cases = request.get("test_cases")

    if not isinstance(code, str):
        raise SystemExit(122)

    if not isinstance(entry_point, str):
        raise SystemExit(122)

    if not isinstance(test_cases, list):
        raise SystemExit(122)

    if not test_cases or len(test_cases) > 100:
        raise SystemExit(122)

    results: list[dict[str, Any]] = []

    for test_case in test_cases:
        if not isinstance(test_case, dict):
            raise SystemExit(122)

        results.append(
            run_case(
                code=code,
                entry_point=entry_point,
                test_case=test_case,
            )
        )

    response = {
        "protocol_version": PROTOCOL_VERSION,
        "results": results,
    }

    # 只有可信父进程可以产生最终控制器响应。
    sys.stdout.write(
        json.dumps(
            response,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )

    sys.stdout.flush()


if __name__ == "__main__":
    main()