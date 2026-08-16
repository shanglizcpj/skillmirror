from datetime import datetime, timezone
from uuid import uuid4


STARTER_CODE = """def find_max(nums):
    max_num = 0

    for i in range(len(nums) + 1):
        if nums[i] > max_num:
            max_num = nums[i]

    return max_num"""


FIXED_CODE = """def find_max(nums):
    max_num = nums[0]

    for i in range(len(nums)):
        if nums[i] > max_num:
            max_num = nums[i]

    return max_num"""


MAIN_CHALLENGE = {
    "challenge_id": "debugging_001",
    "title": "Fix the Maximum Finder",
    "skill_id": "debugging",
    "difficulty": "beginner",
    "description": (
        "Fix the function so that it returns "
        "the largest number from a non-empty list."
    ),
    "requirements": [
        "Do not access an invalid list index.",
        "Support lists containing only negative numbers.",
        "Keep the function name unchanged.",
    ],
    "starter_code": STARTER_CODE,
}


NEXT_CHALLENGE = {
    "challenge_id": "debugging_002",
    "title": "Fix the Duplicate Remover",
    "skill_id": "debugging",
    "difficulty": "beginner",
    "description": (
        "Fix the function so that it removes duplicates "
        "while preserving the original order."
    ),
    "requirements": [
        "Preserve the original order.",
        "Return a new list.",
        "Support an empty input list.",
    ],
    "starter_code": """def remove_duplicates(items):
    result = []

    for item in items:
        if item in result:
            result.append(item)

    return result""",
}


SKILLS = [
    {
        "id": "coding",
        "name": "Coding",
        "score": 78,
        "confidence": 82,
        "evidence": 12,
        "trend": 6,
        "color": "#3b82f6",
    },
    {
        "id": "debugging",
        "name": "Debugging",
        "score": None,
        "confidence": 0,
        "evidence": 0,
        "trend": None,
        "color": "#8b5cf6",
    },
    {
        "id": "testing",
        "name": "Testing",
        "score": 46,
        "confidence": 53,
        "evidence": 5,
        "trend": 3,
        "color": "#14b8a6",
    },
    {
        "id": "problem-solving",
        "name": "Problem Solving",
        "score": 63,
        "confidence": 71,
        "evidence": 9,
        "trend": 5,
        "color": "#f59e0b",
    },
    {
        "id": "code-reading",
        "name": "Code Reading",
        "score": 71,
        "confidence": 76,
        "evidence": 8,
        "trend": 4,
        "color": "#ec4899",
    },
]


EVIDENCE = [
    {
        "evidence_id": "EV001",
        "skill": "Debugging",
        "sub_skill": "Error Identification",
        "action": "identified_index_error",
        "description": "Identified an invalid list index.",
        "score_change": 8,
        "strength": "strong",
        "confidence": 0.91,
        "timestamp": datetime.now(timezone.utc),
    },
    {
        "evidence_id": "EV002",
        "skill": "Debugging",
        "sub_skill": "Boundary Awareness",
        "action": "fixed_boundary_condition",
        "description": "Corrected the loop boundary.",
        "score_change": 7,
        "strength": "strong",
        "confidence": 0.94,
        "timestamp": datetime.now(timezone.utc),
    },
]


SESSIONS: dict[str, dict] = {}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(
    user_id: str,
    skill_id: str,
) -> dict:
    session_id = f"SES-{uuid4().hex[:10].upper()}"

    session = {
        "session_id": session_id,
        "user_id": user_id,
        "skill_id": skill_id,
        "status": "active",
        "started_at": utc_now(),
        "code_version": 0,
        "hint_level": 0,
        "last_code": STARTER_CODE,
        "last_result": None,
    }

    SESSIONS[session_id] = session

    return {
        "session_id": session_id,
        "status": "active",
        "started_at": session["started_at"],
        "challenge": MAIN_CHALLENGE,
    }


def get_session(session_id: str) -> dict | None:
    return SESSIONS.get(session_id)


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

        return {
            "status": "syntax_error",
            "stdout": "",
            "stderr": (
                'SyntaxError: expected function "find_max".'
            ),
            "passed": 0,
            "total": 5,
            "runtime": 0.01,
            "tests": [
                {
                    "name": name,
                    "status": status,
                }
                for name, status in zip(
                    test_names,
                    statuses,
                )
            ],
        }

    boundary_bug = (
        "range(len(nums) + 1)" in stripped_code
        or "range(len(nums)+1)" in stripped_code
    )

    negative_bug = (
        "max_num = 0" in stripped_code
        or "max_num=0" in stripped_code
    )

    if boundary_bug:
        statuses = ["failed"] * 5

        return {
            "status": "failed",
            "stdout": "",
            "stderr": (
                "IndexError: list index out of range"
            ),
            "passed": 0,
            "total": 5,
            "runtime": 0.02,
            "tests": [
                {
                    "name": name,
                    "status": status,
                }
                for name, status in zip(
                    test_names,
                    statuses,
                )
            ],
        }

    if negative_bug:
        statuses = [
            "passed",
            "passed",
            "failed",
            "passed",
            "passed",
        ]

        return {
            "status": "failed",
            "stdout": "Execution completed.",
            "stderr": (
                "AssertionError: expected -3, "
                "but received 0."
            ),
            "passed": 4,
            "total": 5,
            "runtime": 0.02,
            "tests": [
                {
                    "name": name,
                    "status": status,
                }
                for name, status in zip(
                    test_names,
                    statuses,
                )
            ],
        }

    statuses = ["passed"] * 5

    return {
        "status": "success",
        "stdout": "All tests passed.",
        "stderr": "",
        "passed": 5,
        "total": 5,
        "runtime": 0.03,
        "tests": [
            {
                "name": name,
                "status": status,
            }
            for name, status in zip(
                test_names,
                statuses,
            )
        ],
    }


def run_code(
    session_id: str,
    code: str,
) -> dict | None:
    session = get_session(session_id)

    if session is None:
        return None

    session["code_version"] += 1
    session["last_code"] = code

    result = evaluate_code(code)
    session["last_result"] = result

    return {
        "execution_id": (
            f"EXE-{uuid4().hex[:10].upper()}"
        ),
        "session_id": session_id,
        "code_version": session["code_version"],
        **result,
        "simulated": True,
    }


def submit_challenge(
    session_id: str,
    code: str,
) -> dict | None:
    session = get_session(session_id)

    if session is None:
        return None

    result = evaluate_code(code)
    completed = result["passed"] == result["total"]

    session["last_code"] = code
    session["last_result"] = result
    session["status"] = (
        "completed" if completed else "needs_revision"
    )

    if completed:
        debugging_skill = next(
            skill
            for skill in SKILLS
            if skill["id"] == "debugging"
        )

        debugging_skill["score"] = 74
        debugging_skill["confidence"] = 87
        debugging_skill["evidence"] = 4
        debugging_skill["trend"] = 11

    return {
        "session_id": session_id,
        "status": session["status"],
        "passed": result["passed"],
        "total": result["total"],
        "score_change": 11 if completed else 0,
        "message": (
            "Challenge completed successfully."
            if completed
            else "Please fix the remaining problems."
        ),
        "submitted_at": utc_now(),
    }


def create_hint(
    session_id: str,
    code: str,
) -> dict | None:
    session = get_session(session_id)

    if session is None:
        return None

    session["hint_level"] += 1
    hint_level = min(session["hint_level"], 3)

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
                "Try initializing the maximum from "
                "the first list element."
            ),
        ]

    return {
        "session_id": session_id,
        "hint_level": hint_level,
        "hint": hints[hint_level - 1],
        "dependency": (
            "low"
            if hint_level == 1
            else "medium"
            if hint_level == 2
            else "high"
        ),
        "created_at": utc_now(),
    }


def get_skills() -> list[dict]:
    return SKILLS


def get_evidence() -> list[dict]:
    return EVIDENCE


def get_next_challenge(
    user_id: str,
) -> dict:
    return {
        "user_id": user_id,
        "reason": (
            "Boundary Awareness still has limited "
            "verified evidence."
        ),
        "challenge": NEXT_CHALLENGE,
    }