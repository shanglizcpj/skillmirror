import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ActionLog


class ActionType:
    CHALLENGE_STARTED = "CHALLENGE_STARTED"
    CODE_MODIFIED = "CODE_MODIFIED"
    CODE_EXECUTED = "CODE_EXECUTED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    HINT_REQUESTED = "HINT_REQUESTED"
    HINT_RECEIVED = "HINT_RECEIVED"
    TEST_FAILED = "TEST_FAILED"
    TEST_PASSED = "TEST_PASSED"
    CHALLENGE_SUBMITTED = "CHALLENGE_SUBMITTED"


def detect_error_type(
    stderr: str,
) -> str | None:
    known_errors = [
        "IndexError",
        "SyntaxError",
        "TypeError",
        "ValueError",
        "NameError",
        "KeyError",
        "AttributeError",
        "AssertionError",
        "TimeoutError",
    ]

    for error_name in known_errors:
        if error_name in stderr:
            return error_name

    return None


def record_action(
    database: Session,
    session_id: str,
    action: str,
    code_version: int | None = None,
    error_type: str | None = None,
    result: str | None = None,
    test_result: str | None = None,
    hint_level: int | None = None,
    details: dict[str, Any] | None = None,
    commit: bool = False,
) -> ActionLog:
    payload = {
        "code_version": code_version,
        "error_type": error_type,
        "result": result,
        "test_result": test_result,
        "hint_level": hint_level,
        "details": details or {},
    }

    action_log = ActionLog(
        session_id=session_id,
        action=action,
        detail_json=json.dumps(
            payload,
            ensure_ascii=False,
        ),
    )

    database.add(action_log)

    if commit:
        database.commit()
        database.refresh(action_log)
    else:
        database.flush()

    return action_log


def serialize_action(
    action_log: ActionLog,
) -> dict:
    try:
        payload = json.loads(
            action_log.detail_json or "{}"
        )
    except json.JSONDecodeError:
        payload = {}

    return {
        "id": action_log.id,
        "session_id": action_log.session_id,
        "action": action_log.action,
        "code_version": payload.get(
            "code_version"
        ),
        "error_type": payload.get(
            "error_type"
        ),
        "result": payload.get("result"),
        "test_result": payload.get(
            "test_result"
        ),
        "hint_level": payload.get(
            "hint_level"
        ),
        "details": payload.get(
            "details",
            {},
        ),
        "created_at": action_log.created_at,
    }


def get_session_actions(
    database: Session,
    session_id: str,
) -> list[dict]:
    action_logs = database.scalars(
        select(ActionLog)
        .where(
            ActionLog.session_id == session_id
        )
        .order_by(ActionLog.created_at)
    ).all()

    return [
        serialize_action(action_log)
        for action_log in action_logs
    ]