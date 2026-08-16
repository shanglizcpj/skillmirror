from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .client import AClient
from .config import get_agent_settings
from .provenance import (
    content_digest,
    sign_b_record,
)
from .runtime_records import runtime_record_store
from .store import challenge_store


class HintError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_latest_test_result(
    records: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for record in reversed(records):
        if record.get("record_type") == "test_result":
            return record

    return None


def find_hint_history(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("record_type") == "hint_record"
    ]


class HintService:
    async def request_hint(
        self,
        *,
        user_id: str,
        session_id: str,
        user_code: str,
        failed_attempts: int,
        asked_for_hint: bool,
    ) -> dict[str, Any]:
        challenge_record = challenge_store.get(
            session_id
        )

        if challenge_record is None:
            raise HintError(
                "Challenge session not found"
            )

        if challenge_record["user_id"] != user_id:
            raise HintError(
                "Challenge does not belong to this user"
            )

        if challenge_record["status"] != "active":
            raise HintError(
                "Challenge session is not active"
            )

        server_challenge = challenge_record[
            "server_challenge"
        ]

        runtime_records = (
            runtime_record_store.list_by_session(
                session_id
            )
        )

        previous_hints = find_hint_history(
            runtime_records
        )

        latest_test = find_latest_test_result(
            runtime_records
        )

        if latest_test is None:
            test_summary = {}
        else:
            test_summary = {
                "status": latest_test.get("status"),
                "passed": latest_test.get("passed"),
                "total": latest_test.get("total"),
                "scope": latest_test.get("scope"),
                "runtime": latest_test.get("runtime"),
            }

        client = AClient()

        coach_response = await client.coach_hint({
            # 使用B数据库中的server challenge，
            # 不能使用浏览器自己提交的challenge。
            "challenge": server_challenge,

            "user_code": user_code,

            "test_results": test_summary,

            "hint_history": previous_hints,

            "failed_attempts": failed_attempts,

            "asked_for_hint": asked_for_hint,
        })

        action = coach_response.get("action")
        hint_level = int(
            coach_response.get("hint_level", 0)
            or 0
        )

        # 只有A真正给出1—3级Hint时才生成记录。
        if (
            action == "give_hint"
            and hint_level in {1, 2, 3}
        ):
            settings = get_agent_settings()
            hint_id = f"HINT-{uuid4().hex}"
            timestamp = utc_now()

            hint_record = sign_b_record(
                {
                    "record_type": "hint_record",

                    "user_id": user_id,
                    "session_id": session_id,

                    "challenge_id":
                        challenge_record[
                            "challenge_id"
                        ],

                    "hint_id": hint_id,
                    "level": hint_level,

                    "hint_key": coach_response.get(
                        "hint_key",
                        f"level_{hint_level}",
                    ),

                    "message_digest": content_digest(
                        coach_response.get(
                            "message",
                            "",
                        )
                    ),

                    "source": coach_response.get(
                        "source",
                        "unknown",
                    ),

                    "timestamp": timestamp,
                },
                settings.b_provenance_secret,
            )

            runtime_record_store.save(
                record_id=hint_id,
                record=hint_record,
            )

        # 仅返回A Coach提供的安全提示内容。
        return {
            "action": coach_response.get("action"),
            "hint_level": coach_response.get(
                "hint_level"
            ),
            "hint_key": coach_response.get(
                "hint_key"
            ),
            "message": coach_response.get("message"),
            "source": coach_response.get("source"),
            "reason": coach_response.get("reason"),
        }


hint_service = HintService()