import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Challenge,
    ChallengeSession,
    CodeSubmission,
    Evidence,
    HintRecord,
    Skill,
    TestResult,
)
from app.services.action_logger import (
    ActionType,
    detect_error_type,
    record_action,
)
from app.services.code_simulator import evaluate_code


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def challenge_to_dict(
    challenge: Challenge,
) -> dict:
    return {
        "challenge_id": challenge.id,
        "title": challenge.title,
        "skill_id": challenge.skill_key,
        "difficulty": challenge.difficulty,
        "description": challenge.description,
        "requirements": json.loads(
            challenge.requirements_json
        ),
        "starter_code": challenge.starter_code,
    }


def create_session(
    database: Session,
    user_id: str,
    skill_id: str,
) -> dict | None:
    challenge = database.scalar(
        select(Challenge)
        .where(
            Challenge.skill_key == skill_id,
            Challenge.is_active.is_(True),
        )
        .order_by(Challenge.id)
    )

    if challenge is None:
        return None

    session_id = (
        f"SES-{uuid4().hex[:10].upper()}"
    )

    challenge_session = ChallengeSession(
        id=session_id,
        user_id=user_id,
        challenge_id=challenge.id,
        status="active",
    )

    database.add(challenge_session)
    database.flush()

    record_action(
        database=database,
        session_id=session_id,
        action=ActionType.CHALLENGE_STARTED,
        result="started",
        details={
            "challenge_id": challenge.id,
            "skill_id": skill_id,
            "user_id": user_id,
        },
    )

    database.commit()

    return {
        "session_id": session_id,
        "status": "active",
        "started_at": challenge_session.started_at,
        "challenge": challenge_to_dict(challenge),
    }


def run_code(
    database: Session,
    session_id: str,
    code: str,
) -> dict | None:
    challenge_session = database.get(
        ChallengeSession,
        session_id,
    )

    if challenge_session is None:
        return None

    challenge_session.code_version += 1

    submission = CodeSubmission(
        session_id=session_id,
        code=code,
        version=challenge_session.code_version,
        submission_type="run",
    )

    database.add(submission)
    database.flush()

    result = evaluate_code(code)

    test_result = TestResult(
        submission_id=submission.id,
        status=result["status"],
        passed=result["passed"],
        total=result["total"],
        runtime=result["runtime"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        tests_json=json.dumps(result["tests"]),
    )

    database.add(test_result)

    test_summary = (
        f"{result['passed']}/{result['total']}"
    )

    record_action(
        database=database,
        session_id=session_id,
        action=ActionType.CODE_EXECUTED,
        code_version=(
            challenge_session.code_version
        ),
        result=result["status"],
        test_result=test_summary,
        details={
            "runtime": result["runtime"],
        },
    )

    if result["status"] == "success":
        record_action(
            database=database,
            session_id=session_id,
            action=ActionType.TEST_PASSED,
            code_version=(
                challenge_session.code_version
            ),
            result="passed",
            test_result=test_summary,
            details={
                "passed": result["passed"],
                "total": result["total"],
            },
        )
    else:
        error_type = detect_error_type(
            result["stderr"]
        )

        record_action(
            database=database,
            session_id=session_id,
            action=ActionType.EXECUTION_FAILED,
            code_version=(
                challenge_session.code_version
            ),
            error_type=error_type,
            result="failed",
            test_result=test_summary,
            details={
                "stderr": result["stderr"],
            },
        )

        record_action(
            database=database,
            session_id=session_id,
            action=ActionType.TEST_FAILED,
            code_version=(
                challenge_session.code_version
            ),
            error_type=error_type,
            result="failed",
            test_result=test_summary,
            details={
                "passed": result["passed"],
                "total": result["total"],
            },
        )

    database.commit()

    return {
        "execution_id": (
            f"EXE-{uuid4().hex[:10].upper()}"
        ),
        "session_id": session_id,
        "code_version": (
            challenge_session.code_version
        ),
        **result,
        "simulated": True,
    }


def submit_challenge(
    database: Session,
    session_id: str,
    code: str,
) -> dict | None:
    challenge_session = database.get(
        ChallengeSession,
        session_id,
    )

    if challenge_session is None:
        return None

    previously_completed = (
        challenge_session.status == "completed"
    )

    challenge_session.code_version += 1

    submission = CodeSubmission(
        session_id=session_id,
        code=code,
        version=challenge_session.code_version,
        submission_type="submit",
    )

    database.add(submission)
    database.flush()

    result = evaluate_code(code)

    test_result = TestResult(
        submission_id=submission.id,
        status=result["status"],
        passed=result["passed"],
        total=result["total"],
        runtime=result["runtime"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        tests_json=json.dumps(result["tests"]),
    )

    database.add(test_result)

    completed = (
        result["passed"] == result["total"]
    )

    challenge_session.status = (
        "completed"
        if completed
        else "needs_revision"
    )

    challenge_session.submitted_at = utc_now()

    if completed:
        update_debugging_skill(
            database=database,
            user_id=challenge_session.user_id,
            session_id=session_id,
        )

    record_action(
        database=database,
        session_id=session_id,
        action=ActionType.CHALLENGE_SUBMITTED,
        code_version=(
            challenge_session.code_version
        ),
        result=challenge_session.status,
        test_result=(
            f"{result['passed']}/{result['total']}"
        ),
        details={
            "completed": completed,
            "passed": result["passed"],
            "total": result["total"],
        },
    )

    database.commit()

    return {
        "session_id": session_id,
        "status": challenge_session.status,
        "passed": result["passed"],
        "total": result["total"],
        "score_change": (
            11
            if completed and not previously_completed
            else 0
        ),
        "message": (
            "Challenge completed successfully."
            if completed
            else "Please fix the remaining problems."
        ),
        "submitted_at": (
            challenge_session.submitted_at
        ),
    }


def update_debugging_skill(
    database: Session,
    user_id: str,
    session_id: str,
) -> None:
    skill = database.scalar(
        select(Skill).where(
            Skill.user_id == user_id,
            Skill.skill_key == "debugging",
        )
    )

    if skill is not None:
        skill.score = 74
        skill.confidence = 87
        skill.evidence_count = 4
        skill.trend = 11

    existing_evidence = database.scalar(
        select(Evidence).where(
            Evidence.session_id == session_id
        )
    )

    if existing_evidence is not None:
        return

    evidence_data = [
        (
            "Error Identification",
            "identified_index_error",
            "Identified the IndexError.",
            4,
            0.91,
        ),
        (
            "Boundary Awareness",
            "fixed_loop_boundary",
            "Corrected the loop boundary.",
            5,
            0.94,
        ),
        (
            "Fix Verification",
            "passed_hidden_tests",
            "Passed all hidden tests.",
            4,
            0.96,
        ),
        (
            "Hint Dependency",
            "used_hint",
            "Used progressive assistance.",
            -2,
            0.82,
        ),
    ]

    for (
        sub_skill,
        action,
        description,
        score_change,
        confidence,
    ) in evidence_data:
        database.add(
            Evidence(
                id=(
                    f"EV-{uuid4().hex[:10].upper()}"
                ),
                user_id=user_id,
                session_id=session_id,
                skill_key="debugging",
                sub_skill=sub_skill,
                action=action,
                description=description,
                score_change=score_change,
                strength="strong",
                confidence=confidence,
            )
        )


def create_hint(
    database: Session,
    session_id: str,
    code: str,
) -> dict | None:
    challenge_session = database.get(
        ChallengeSession,
        session_id,
    )

    if challenge_session is None:
        return None

    challenge_session.hint_level = min(
        challenge_session.hint_level + 1,
        3,
    )

    level = challenge_session.hint_level

    if (
        "range(len(nums) + 1)" in code
        or "range(len(nums)+1)" in code
    ):
        hints = [
            (
                "Check how many valid indexes exist "
                "in a list of length n."
            ),
            (
                "Compare range(len(nums)) with "
                "range(len(nums) + 1)."
            ),
            (
                "The loop should not access "
                "nums[len(nums)]."
            ),
        ]
    else:
        hints = [
            (
                "Think about whether zero is always "
                "a safe initial maximum."
            ),
            (
                "Consider a list containing only "
                "negative numbers."
            ),
            (
                "Initialize the maximum from the "
                "first list element."
            ),
        ]

    dependency = (
        "low"
        if level == 1
        else "medium"
        if level == 2
        else "high"
    )

    hint_text = hints[level - 1]

    database.add(
        HintRecord(
            session_id=session_id,
            hint_level=level,
            hint=hint_text,
            dependency=dependency,
        )
    )

    record_action(
        database=database,
        session_id=session_id,
        action=ActionType.HINT_REQUESTED,
        code_version=(
            challenge_session.code_version
        ),
        hint_level=level,
        result="requested",
        details={
            "dependency": dependency,
        },
    )

    record_action(
        database=database,
        session_id=session_id,
        action=ActionType.HINT_RECEIVED,
        code_version=(
            challenge_session.code_version
        ),
        hint_level=level,
        result="received",
        details={
            "dependency": dependency,
            "hint": hint_text,
        },
    )

    database.commit()

    return {
        "session_id": session_id,
        "hint_level": level,
        "hint": hint_text,
        "dependency": dependency,
        "created_at": utc_now(),
    }


def get_skills(
    database: Session,
    user_id: str,
) -> list[dict]:
    skills = database.scalars(
        select(Skill)
        .where(Skill.user_id == user_id)
        .order_by(Skill.name)
    ).all()

    return [
        {
            "id": skill.skill_key,
            "name": skill.name,
            "score": skill.score,
            "confidence": skill.confidence,
            "evidence": skill.evidence_count,
            "trend": skill.trend,
            "color": skill.color,
        }
        for skill in skills
    ]


def get_evidence(
    database: Session,
    user_id: str,
) -> list[dict]:
    evidence_items = database.scalars(
        select(Evidence)
        .where(Evidence.user_id == user_id)
        .order_by(Evidence.timestamp.desc())
    ).all()

    return [
        {
            "evidence_id": item.id,
            "skill": item.skill_key.title(),
            "sub_skill": item.sub_skill,
            "action": item.action,
            "description": item.description,
            "score_change": item.score_change,
            "strength": item.strength,
            "confidence": item.confidence,
            "timestamp": item.timestamp,
        }
        for item in evidence_items
    ]


def get_next_challenge(
    database: Session,
    user_id: str,
) -> dict | None:
    challenge = database.get(
        Challenge,
        "debugging_002",
    )

    if challenge is None:
        return None

    return {
        "user_id": user_id,
        "reason": (
            "Boundary Awareness still has limited "
            "verified evidence."
        ),
        "challenge": challenge_to_dict(challenge),
    }