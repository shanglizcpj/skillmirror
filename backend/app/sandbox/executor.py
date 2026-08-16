from __future__ import annotations

from typing import Any
from uuid import uuid4
import json
import os
import shutil
import subprocess
import time

from app.core.config import get_settings


class SandboxUnavailableError(RuntimeError):
    pass


def normalize_timeout_output(
    output: Any,
) -> str:
    if output is None:
        return ""

    if isinstance(output, bytes):
        return output.decode(
            "utf-8",
            errors="replace",
        )

    return str(output)


def remove_container(
    container_name: str,
) -> None:
    try:
        subprocess.run(
            [
                "docker",
                "rm",
                "-f",
                container_name,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        pass


def check_sandbox_available() -> None:
    settings = get_settings()

    if shutil.which("docker") is None:
        raise SandboxUnavailableError(
            "Docker command was not found."
        )

    result = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            settings.sandbox_image,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )

    if result.returncode != 0:
        raise SandboxUnavailableError(
            "Sandbox image was not found. "
            "Build skillmirror-python-sandbox first."
        )


def execute_test_suite(
    *,
    code: str,
    entry_point: str,
    test_cases: list[dict[str, Any]],
    timeout_seconds: int = 3,
) -> dict[str, Any]:
    settings = get_settings()

    check_sandbox_available()

    container_name = (
        "skillmirror-test-"
        + uuid4().hex[:12]
    )

    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--network",
        "none",
        "--memory",
        settings.sandbox_memory,
        "--memory-swap",
        settings.sandbox_memory,
        "--cpus",
        settings.sandbox_cpus,
        "--pids-limit",
        str(settings.sandbox_pids_limit),
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "10001:10001",
        "-i",
        settings.sandbox_image,
    ]

    payload = json.dumps(
        {
            "code": code,
            "entry_point": entry_point,
            "test_cases": test_cases,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    creation_flags = 0

    if os.name == "nt":
        creation_flags = (
            subprocess.CREATE_NO_WINDOW
        )

    started_at = time.perf_counter()

    try:
        completed = subprocess.run(
            command,
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds + 1,
            check=False,
            creationflags=creation_flags,
        )

        runtime = round(
            time.perf_counter() - started_at,
            4,
        )

        exit_code = completed.returncode

        if exit_code != 0:
            return {
                "status": (
                    "resource_limit"
                    if exit_code in {137, 143}
                    else "error"
                ),
                "controller_result": None,
                "stderr": completed.stderr[:500],
                "exit_code": exit_code,
                "runtime": runtime,
                "sandbox_mode":
                    "docker-isolated-controller",
            }

        # 必须是唯一、完整的JSON对象。
        # 多余的学习者输出会导致解析失败，而不是被信任。
        try:
            controller_result = json.loads(
                completed.stdout.strip()
            )
        except json.JSONDecodeError:
            return {
                "status": "error",
                "controller_result": None,
                "stderr": (
                    "Sandbox controller returned "
                    "invalid or contaminated JSON."
                ),
                "exit_code": exit_code,
                "runtime": runtime,
                "sandbox_mode":
                    "docker-isolated-controller",
            }

        if (
            not isinstance(controller_result, dict)
            or controller_result.get(
                "protocol_version"
            ) != 2
        ):
            return {
                "status": "error",
                "controller_result": None,
                "stderr": (
                    "Sandbox controller protocol "
                    "validation failed."
                ),
                "exit_code": exit_code,
                "runtime": runtime,
                "sandbox_mode":
                    "docker-isolated-controller",
            }

        return {
            "status": "success",
            "controller_result":
                controller_result,
            "stderr": "",
            "exit_code": exit_code,
            "runtime": runtime,
            "sandbox_mode":
                "docker-isolated-controller",
        }

    except subprocess.TimeoutExpired as error:
        remove_container(container_name)

        runtime = round(
            time.perf_counter() - started_at,
            4,
        )

        return {
            "status": "timeout",
            "controller_result": None,
            "stderr": (
                "Execution timed out. "
                f"Maximum time: {timeout_seconds} seconds."
            ),
            "exit_code": None,
            "runtime": runtime,
            "sandbox_mode":
                "docker-isolated-controller",
        }

    except OSError as error:
        remove_container(container_name)

        raise SandboxUnavailableError(
            f"Unable to start Docker: {error}"
        ) from error


def execute_python(
    code: str,
    timeout_seconds: int = 3,
) -> dict[str, Any]:
    del code
    del timeout_seconds

    raise SandboxUnavailableError(
        "Direct untrusted code execution is disabled. "
        "Use the isolated test controller."
    )