from __future__ import annotations

from typing import Any

from app.agent_orchestrator.assessment_store import assessment_store


SAFE_EVIDENCE_FIELDS = {
    "evidence_id",
    "user_id",
    "session_id",
    "challenge_id",
    "challenge_digest",
    "challenge_type",
    "skill",
    "sub_skill",
    "subskill",
    "performance_score",
    "score_delta",
    "strength",
    "difficulty",
    "reliability",
    "direction",
    "reason",
    "rule_id",
    "rule_version",
    "timestamp",
    "created_at",
}


SAFE_CHALLENGE_FIELDS = {
    "session_id",
    "challenge_id",
    "challenge_digest",
    "challenge_type",
    "target_skill",
    "target_subskill",
    "difficulty",
    "score",
    "confidence",
    "completed_at",
    "timestamp",
}


def _safe_item(
    item: dict[str, Any],
    allowed_fields: set[str],
) -> dict[str, Any]:
    """
    删除内部签名、provenance 和其他不应该发送给浏览器的数据。
    """

    return {
        key: value
        for key, value in item.items()
        if key in allowed_fields
    }


def get_public_evidence_history(
    user_id: str,
) -> dict[str, Any]:
    cleaned_user_id = user_id.strip()

    if not cleaned_user_id:
        raise ValueError("user_id cannot be empty")

    evidence_history = assessment_store.get_evidence_history(
        cleaned_user_id,
    )

    public_items = [
        _safe_item(item, SAFE_EVIDENCE_FIELDS)
        for item in evidence_history
    ]

    return {
        "user_id": cleaned_user_id,
        "total": len(public_items),
        "items": public_items,
    }


def get_public_challenge_history(
    user_id: str,
) -> dict[str, Any]:
    cleaned_user_id = user_id.strip()

    if not cleaned_user_id:
        raise ValueError("user_id cannot be empty")

    challenge_history = assessment_store.get_previous_challenges(
        cleaned_user_id,
    )

    public_items = [
        _safe_item(item, SAFE_CHALLENGE_FIELDS)
        for item in challenge_history
    ]

    return {
        "user_id": cleaned_user_id,
        "total": len(public_items),
        "items": public_items,
    }

def _list_count(
    value: Any,
) -> int:
    if isinstance(value, list):
        return len(value)

    return 0


def get_public_assessment_report(
    user_id: str,
) -> dict[str, Any]:
    cleaned_user_id = user_id.strip()

    if not cleaned_user_id:
        raise ValueError("user_id cannot be empty")

    records = assessment_store.get_assessment_history(
        cleaned_user_id,
    )

    if not records:
        return {
            "user_id": cleaned_user_id,
            "total_assessments": 0,
            "latest": None,
            "history": [],
        }

    public_history: list[dict[str, Any]] = []

    for record in records:
        response = record.get("response", {})
        challenge_summary = record.get(
            "challenge_summary",
            {},
        )

        score_result = response.get("score", {})
        confidence_result = response.get(
            "confidence",
            {},
        )

        score_value = score_result.get("new_score")

        confidence_percent = confidence_result.get(
            "confidence_percent"
        )

        if confidence_percent is None:
            confidence_value = confidence_result.get(
                "confidence"
            )

            if isinstance(
                confidence_value,
                (int, float),
            ):
                confidence_percent = round(
                    float(confidence_value) * 100,
                    1,
                )

        public_history.append(
            {
                "session_id": record["session_id"],
                "challenge_id": record["challenge_id"],
                "target_skill": challenge_summary.get(
                    "target_skill"
                ),
                "target_subskill":
                    challenge_summary.get(
                        "target_subskill"
                    ),
                "difficulty": challenge_summary.get(
                    "difficulty"
                ),
                "score": score_value,
                "confidence_percent":
                    confidence_percent,
                "score_status": score_result.get(
                    "score_status"
                ),
                "created_at": record["created_at"],
            }
        )

    latest_record = records[-1]
    latest_response = latest_record.get(
        "response",
        {},
    )

    latest_materialization = latest_response.get(
        "evidence_materialization",
        {},
    )

    latest_trust_report = latest_response.get(
        "trust_report",
        {},
    )

    latest_public = {
        "session_id": latest_record["session_id"],
        "challenge_id": latest_record["challenge_id"],
        "created_at": latest_record["created_at"],
        "score": latest_response.get("score", {}),
        "confidence": latest_response.get(
            "confidence",
            {},
        ),
        "skill_mirror": latest_record.get(
            "skill_mirror",
            {},
        ),
        "next_examiner": latest_record.get(
            "next_examiner",
            {},
        ),
        "evidence_summary": {
            "accepted_count": _list_count(
                latest_materialization.get(
                    "accepted"
                )
            ),
            "rejected_count": _list_count(
                latest_materialization.get(
                    "rejected"
                )
            ),
        },
        "trust_summary": {
            "rejected_b_records_count": _list_count(
                latest_trust_report.get(
                    "rejected_b_records"
                )
            ),
            "rejected_history_count": _list_count(
                latest_trust_report.get(
                    "rejected_history"
                )
            ),
            "replayed_evidence_count": _list_count(
                latest_trust_report.get(
                    "replayed_evidence"
                )
            ),
            "caller_verification_status_trusted":
                latest_trust_report.get(
                    "caller_verification_status_trusted",
                    False,
                ),
        },
    }

    return {
        "user_id": cleaned_user_id,
        "total_assessments": len(public_history),
        "latest": latest_public,
        "history": public_history,
    }