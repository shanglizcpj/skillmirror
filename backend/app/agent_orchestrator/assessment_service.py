from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .assessment_store import assessment_store
from .client import AClient
from .provenance import content_digest
from .runtime_records import runtime_record_store
from .store import challenge_store


class AssessmentError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_last_record(
    records: list[dict[str, Any]],
    *,
    record_type: str,
    predicate=None,
) -> dict[str, Any] | None:
    for record in reversed(records):
        if record.get("record_type") != record_type:
            continue

        if predicate is not None and not predicate(record):
            continue

        return record

    return None


class AssessmentService:
    async def complete(
        self,
        *,
        user_id: str,
        session_id: str,
        submitted_code: str,
        elapsed_seconds: float | None,
    ) -> dict[str, Any]:
        challenge_record = challenge_store.get(
            session_id
        )

        if challenge_record is None:
            raise AssessmentError(
                "Challenge session not found"
            )

        if challenge_record["user_id"] != user_id:
            raise AssessmentError(
                "Challenge does not belong to this user"
            )

        if challenge_record["status"] != "active":
            raise AssessmentError(
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

        if not runtime_records:
            raise AssessmentError(
                "No signed runtime records were found"
            )

        submitted_digest = content_digest(
            submitted_code
        )

        # 只选择与最终提交代码摘要一致的测试结果。
        final_test_result = find_last_record(
            runtime_records,
            record_type="test_result",
            predicate=lambda record: (
                record.get("submission_digest")
                == submitted_digest
            ),
        )

        if final_test_result is None:
            raise AssessmentError(
                "No test result matches submitted_code. "
                "Run tests using the exact submitted code first."
            )

        passed = int(
            final_test_result.get("passed", 0)
        )

        total = int(
            final_test_result.get("total", 0)
        )

        if total <= 0 or passed != total:
            raise AssessmentError(
                "Final submitted code has not passed all tests"
            )

        final_action_log = find_last_record(
            runtime_records,
            record_type="action_log",
        )

        final_code_version = find_last_record(
            runtime_records,
            record_type="code_version",
            predicate=lambda record: (
                record.get("code_digest")
                == submitted_digest
            ),
        )

        if final_code_version is None:
            raise AssessmentError(
                "No signed code version matches submitted_code"
            )

        action_logs = (
            [final_action_log]
            if final_action_log is not None
            else []
        )

        code_versions = [final_code_version]
        test_results = [final_test_result]

        # 当前还未接Hint持久化，所以通常为空。
        final_hint = find_last_record(
            runtime_records,
            record_type="hint_record",
        )

        hint_history = (
            [final_hint]
            if final_hint is not None
            else []
        )

        evidence_history = (
            assessment_store.get_evidence_history(
                user_id
            )
        )

        previous_challenges = (
            assessment_store.get_previous_challenges(
                user_id
            )
        )

        payload = {
            "user_id": user_id,
            "session_id": session_id,

            # 必须使用B数据库中的服务端权威数据。
            "skill_mirror":
                challenge_record["skill_mirror"],

            # 必须原样发送A签名的内部Challenge。
            "challenge": server_challenge,

            # 必须发送B签名的记录。
            "action_logs": action_logs,
            "code_versions": code_versions,
            "test_results": test_results,
            "hint_history": hint_history,

            "submitted_code": submitted_code,
            "elapsed_seconds": elapsed_seconds,

            # 完整可信Evidence History。
            "evidence_history": evidence_history,
            "previous_challenges":
                previous_challenges,

            "timestamp": utc_now(),
        }

        client = AClient()

        response = await client.complete_assessment(
            payload
        )

        trust_report = response.get(
            "trust_report",
            {},
        )

        rejected_records = trust_report.get(
            "rejected_b_records",
            [],
        )

        if rejected_records:
            raise AssessmentError(
                "A rejected one or more B records: "
                f"{rejected_records}"
            )

        accepted_evidence = response.get(
            "evidence_materialization",
            {},
        ).get(
            "accepted",
            [],
        )

        if not accepted_evidence:
            raise AssessmentError(
                "A did not materialize any trusted evidence"
            )

        assessment_store.save_completed_assessment(
            user_id=user_id,
            session_id=session_id,
            challenge=server_challenge,
            response=response,
        )

        challenge_store.mark_completed(session_id)

        # 只返回前端展示需要的安全字段。
        return {
            "schema_version":
                response.get("schema_version"),

            "session_id": session_id,
            "challenge_id":
                server_challenge["challenge_id"],

            "trust_report": trust_report,

            "evidence":
                response["evidence_materialization"],

            "score": response.get("score"),
            "confidence": response.get("confidence"),

            "updated_skill_mirror":
                response.get("updated_skill_mirror"),

            "next_examiner":
                response.get("next_examiner"),
        }


assessment_service = AssessmentService()