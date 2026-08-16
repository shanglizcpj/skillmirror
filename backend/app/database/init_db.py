import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Challenge,
    Evidence,
    Skill,
    SubSkill,
    User,
)


STARTER_CODE = """def find_max(nums):
    max_num = 0

    for i in range(len(nums) + 1):
        if nums[i] > max_num:
            max_num = nums[i]

    return max_num"""


NEXT_STARTER_CODE = """def remove_duplicates(items):
    result = []

    for item in items:
        if item in result:
            result.append(item)

    return result"""


def seed_database(database: Session) -> None:
    user_id = "demo-user-001"

    # 第一阶段：先独立保存用户
    user = database.get(User, user_id)

    if user is None:
        user = User(
            id=user_id,
            display_name="Chenpeiji Zhang",
        )

        database.add(user)
        database.commit()

    # 第二阶段：用户成功保存后，再保存Skills
    existing_skill = database.scalar(
        select(Skill.id).limit(1)
    )

    if existing_skill is None:
        skills = [
            Skill(
                id=f"{user_id}:coding",
                user_id=user_id,
                skill_key="coding",
                name="Coding",
                score=78,
                confidence=82,
                evidence_count=12,
                trend=6,
                color="#3b82f6",
            ),
            Skill(
                id=f"{user_id}:debugging",
                user_id=user_id,
                skill_key="debugging",
                name="Debugging",
                score=None,
                confidence=0,
                evidence_count=0,
                trend=None,
                color="#8b5cf6",
            ),
            Skill(
                id=f"{user_id}:testing",
                user_id=user_id,
                skill_key="testing",
                name="Testing",
                score=46,
                confidence=53,
                evidence_count=5,
                trend=3,
                color="#14b8a6",
            ),
            Skill(
                id=f"{user_id}:problem-solving",
                user_id=user_id,
                skill_key="problem-solving",
                name="Problem Solving",
                score=63,
                confidence=71,
                evidence_count=9,
                trend=5,
                color="#f59e0b",
            ),
            Skill(
                id=f"{user_id}:code-reading",
                user_id=user_id,
                skill_key="code-reading",
                name="Code Reading",
                score=71,
                confidence=76,
                evidence_count=8,
                trend=4,
                color="#ec4899",
            ),
        ]

        database.add_all(skills)
        database.commit()

    # 第三阶段：Skills保存后，再保存SubSkills
    existing_sub_skill = database.scalar(
        select(SubSkill.id).limit(1)
    )

    if existing_sub_skill is None:
        debugging_sub_skills = [
            SubSkill(
                skill_id=f"{user_id}:debugging",
                name="Error Identification",
                score=None,
                confidence=0,
            ),
            SubSkill(
                skill_id=f"{user_id}:debugging",
                name="Root Cause Analysis",
                score=None,
                confidence=0,
            ),
            SubSkill(
                skill_id=f"{user_id}:debugging",
                name="Boundary Awareness",
                score=None,
                confidence=0,
            ),
            SubSkill(
                skill_id=f"{user_id}:debugging",
                name="Fix Strategy",
                score=None,
                confidence=0,
            ),
            SubSkill(
                skill_id=f"{user_id}:debugging",
                name="Fix Verification",
                score=None,
                confidence=0,
            ),
        ]

        database.add_all(debugging_sub_skills)
        database.commit()

    # 第四阶段：保存Challenges
    existing_challenge = database.scalar(
        select(Challenge.id).limit(1)
    )

    if existing_challenge is None:
        challenges = [
            Challenge(
                id="debugging_001",
                title="Fix the Maximum Finder",
                skill_key="debugging",
                difficulty="beginner",
                description=(
                    "Fix the function so that it returns "
                    "the largest number from a non-empty list."
                ),
                requirements_json=json.dumps(
                    [
                        "Do not access an invalid list index.",
                        (
                            "Support lists containing only "
                            "negative numbers."
                        ),
                        "Keep the function name unchanged.",
                    ]
                ),
                starter_code=STARTER_CODE,
                is_active=True,
            ),
            Challenge(
                id="debugging_002",
                title="Fix the Duplicate Remover",
                skill_key="debugging",
                difficulty="beginner",
                description=(
                    "Remove duplicates while preserving "
                    "the original order."
                ),
                requirements_json=json.dumps(
                    [
                        "Preserve the original order.",
                        "Return a new list.",
                        "Support an empty input list.",
                    ]
                ),
                starter_code=NEXT_STARTER_CODE,
                is_active=True,
            ),
        ]

        database.add_all(challenges)
        database.commit()

    # 第五阶段：保存初始Evidence
    existing_evidence = database.scalar(
        select(Evidence.id).limit(1)
    )

    if existing_evidence is None:
        baseline_evidence = [
            Evidence(
                id="EV001",
                user_id=user_id,
                session_id=None,
                skill_key="debugging",
                sub_skill="Error Identification",
                action="identified_index_error",
                description=(
                    "Identified an invalid list index."
                ),
                score_change=8,
                strength="strong",
                confidence=0.91,
            ),
            Evidence(
                id="EV002",
                user_id=user_id,
                session_id=None,
                skill_key="debugging",
                sub_skill="Boundary Awareness",
                action="fixed_boundary_condition",
                description=(
                    "Corrected the loop boundary."
                ),
                score_change=7,
                strength="strong",
                confidence=0.94,
            ),
        ]

        database.add_all(baseline_evidence)
        database.commit()
    existing_user = database.scalar(
        select(User).limit(1)
    )

    if existing_user is not None:
        return

    user = User(
        id="demo-user-001",
        display_name="Chenpeiji Zhang",
    )

    database.add(user)

    database.flush()

    skills = [
        Skill(
            id="demo-user-001:coding",
            user_id=user.id,
            skill_key="coding",
            name="Coding",
            score=78,
            confidence=82,
            evidence_count=12,
            trend=6,
            color="#3b82f6",
        ),
        Skill(
            id="demo-user-001:debugging",
            user_id=user.id,
            skill_key="debugging",
            name="Debugging",
            score=None,
            confidence=0,
            evidence_count=0,
            trend=None,
            color="#8b5cf6",
        ),
        Skill(
            id="demo-user-001:testing",
            user_id=user.id,
            skill_key="testing",
            name="Testing",
            score=46,
            confidence=53,
            evidence_count=5,
            trend=3,
            color="#14b8a6",
        ),
        Skill(
            id="demo-user-001:problem-solving",
            user_id=user.id,
            skill_key="problem-solving",
            name="Problem Solving",
            score=63,
            confidence=71,
            evidence_count=9,
            trend=5,
            color="#f59e0b",
        ),
        Skill(
            id="demo-user-001:code-reading",
            user_id=user.id,
            skill_key="code-reading",
            name="Code Reading",
            score=71,
            confidence=76,
            evidence_count=8,
            trend=4,
            color="#ec4899",
        ),
    ]

    database.add_all(skills)
    database.flush()

    debugging_sub_skills = [
        SubSkill(
            skill_id="demo-user-001:debugging",
            name="Error Identification",
            score=None,
            confidence=0,
        ),
        SubSkill(
            skill_id="demo-user-001:debugging",
            name="Root Cause Analysis",
            score=None,
            confidence=0,
        ),
        SubSkill(
            skill_id="demo-user-001:debugging",
            name="Boundary Awareness",
            score=None,
            confidence=0,
        ),
        SubSkill(
            skill_id="demo-user-001:debugging",
            name="Fix Strategy",
            score=None,
            confidence=0,
        ),
        SubSkill(
            skill_id="demo-user-001:debugging",
            name="Fix Verification",
            score=None,
            confidence=0,
        ),
    ]

    database.add_all(debugging_sub_skills)

    challenges = [
        Challenge(
            id="debugging_001",
            title="Fix the Maximum Finder",
            skill_key="debugging",
            difficulty="beginner",
            description=(
                "Fix the function so that it returns "
                "the largest number from a non-empty list."
            ),
            requirements_json=json.dumps(
                [
                    "Do not access an invalid list index.",
                    (
                        "Support lists containing only "
                        "negative numbers."
                    ),
                    "Keep the function name unchanged.",
                ]
            ),
            starter_code=STARTER_CODE,
            is_active=True,
        ),
        Challenge(
            id="debugging_002",
            title="Fix the Duplicate Remover",
            skill_key="debugging",
            difficulty="beginner",
            description=(
                "Remove duplicates while preserving "
                "the original order."
            ),
            requirements_json=json.dumps(
                [
                    "Preserve the original order.",
                    "Return a new list.",
                    "Support an empty input list.",
                ]
            ),
            starter_code=NEXT_STARTER_CODE,
            is_active=True,
        ),
    ]

    database.add_all(challenges)

    baseline_evidence = [
        Evidence(
            id="EV001",
            user_id=user.id,
            session_id=None,
            skill_key="debugging",
            sub_skill="Error Identification",
            action="identified_index_error",
            description=(
                "Identified an invalid list index."
            ),
            score_change=8,
            strength="strong",
            confidence=0.91,
        ),
        Evidence(
            id="EV002",
            user_id=user.id,
            session_id=None,
            skill_key="debugging",
            sub_skill="Boundary Awareness",
            action="fixed_boundary_condition",
            description=(
                "Corrected the loop boundary."
            ),
            score_change=7,
            strength="strong",
            confidence=0.94,
        ),
    ]

    database.add_all(baseline_evidence)
    database.commit()