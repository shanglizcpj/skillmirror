from __future__ import annotations

from typing import Any

from .assessment_store import assessment_store
from .client import AClient
from .store import challenge_store


FORBIDDEN_LEARNER_FIELDS = {
    "test_cases",
    "hidden_bugs",
    "reference_solution",
    "validation_report",
    "provenance",
}


def build_demo_skill_mirror(
    user_id: str,
) -> dict[str, Any]:
    """
    为首次进入系统的演示用户创建初始能力画像。

    这里只初始化Skill Mirror，不生成或伪造可信Evidence。
    Evidence仍然必须通过真实Challenge闭环产生。
    """
    normalized_user_id = user_id.strip().upper()

    # 演示用户A：初级学习者
    # Debugging尚未测量，引导A Examiner选择DBG001。
    if normalized_user_id.startswith(
        "U-DEMO-BEGINNER"
    ):
        return {
            "user_id": user_id,
            "skills": [
                {
                    "skill_id": "coding",
                    "score": 38,
                    "confidence": 0.28,
                },
                {
                    "skill_id": "debugging",
                    "score": None,
                    "confidence": 0.0,
                    "subskills": [
                        {
                            "id": "boundary_awareness",
                            "score": None,
                            "confidence": 0.0,
                        }
                    ],
                },
                {
                    "skill_id": "testing",
                    "score": 30,
                    "confidence": 0.22,
                },
                {
                    "skill_id": "problem_solving",
                    "score": 34,
                    "confidence": 0.25,
                },
                {
                    "skill_id": "code_reading",
                    "score": 42,
                    "confidence": 0.32,
                },
            ],
        }

    # 演示用户B：中级学习者
    # Testing尚未测量，引导A Examiner选择TST001。
    if normalized_user_id.startswith(
        "U-DEMO-INTERMEDIATE"
    ):
        return {
            "user_id": user_id,
            "skills": [
                {
                    "skill_id": "coding",
                    "score": 68,
                    "confidence": 0.66,
                },
                {
                    "skill_id": "debugging",
                    "score": 61,
                    "confidence": 0.59,
                    "subskills": [
                        {
                            "id": "boundary_awareness",
                            "score": 60,
                            "confidence": 0.58,
                        }
                    ],
                },
                {
                    "skill_id": "testing",
                    "score": None,
                    "confidence": 0.0,
                },
                {
                    "skill_id": "problem_solving",
                    "score": 64,
                    "confidence": 0.62,
                },
                {
                    "skill_id": "code_reading",
                    "score": 70,
                    "confidence": 0.68,
                },
            ],
        }

    # 演示用户C：较强学习者
    # 已测能力较高，但Code Reading尚未测量，
    # 引导A Examiner选择READ001。
    if normalized_user_id.startswith(
        "U-DEMO-ADVANCED"
    ):
        return {
            "user_id": user_id,
            "skills": [
                {
                    "skill_id": "coding",
                    "score": 91,
                    "confidence": 0.88,
                },
                {
                    "skill_id": "debugging",
                    "score": 87,
                    "confidence": 0.85,
                    "subskills": [
                        {
                            "id": "boundary_awareness",
                            "score": 89,
                            "confidence": 0.86,
                        }
                    ],
                },
                {
                    "skill_id": "testing",
                    "score": 86,
                    "confidence": 0.83,
                },
                {
                    "skill_id": "problem_solving",
                    "score": 90,
                    "confidence": 0.87,
                },
                {
                    "skill_id": "code_reading",
                    "score": None,
                    "confidence": 0.0,
                },
            ],
        }

    # 普通用户继续使用原来的联调画像。
    return {
        "user_id": user_id,
        "skills": [
            {
                "skill_id": "coding",
                "score": 78,
                "confidence": 0.82,
            },
            {
                "skill_id": "debugging",
                "score": None,
                "confidence": 0.0,
                "subskills": [
                    {
                        "id": "boundary_awareness",
                        "score": None,
                        "confidence": 0.0,
                    }
                ],
            },
            {
                "skill_id": "testing",
                "score": 46,
                "confidence": 0.53,
            },
            {
                "skill_id": "problem_solving",
                "score": 63,
                "confidence": 0.71,
            },
            {
                "skill_id": "code_reading",
                "score": 71,
                "confidence": 0.76,
            },
        ],
    }

def validate_examiner_decision(
    decision: dict[str, Any],
) -> None:
    required_fields = {
        "target_skill",
        "target_subskill",
        "difficulty",
        "challenge_type",
    }

    missing_fields = [
        field
        for field in required_fields
        if not decision.get(field)
    ]

    if missing_fields:
        raise RuntimeError(
            "Examiner decision is missing required fields: "
            + ", ".join(missing_fields)
        )


def validate_learner_safety(
    challenge: dict[str, Any],
) -> None:
    leaked_fields = sorted(
        field
        for field in FORBIDDEN_LEARNER_FIELDS
        if field in challenge
    )

    if leaked_fields:
        raise RuntimeError(
            "Learner challenge leaked protected fields: "
            + ", ".join(leaked_fields)
        )


class AgentOrchestratorService:
    async def _select_challenge_context(
        self,
        *,
        client: AClient,
        user_id: str,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        str,
    ]:
        """
        返回：
        1. 最新 Skill Mirror
        2. A Examiner 决策
        3. 决策来源
        """

        assessment_history = (
            assessment_store.get_assessment_history(
                user_id
            )
        )

        if assessment_history:
            latest_assessment = assessment_history[-1]

            skill_mirror = latest_assessment.get(
                "skill_mirror"
            )

            next_examiner = latest_assessment.get(
                "next_examiner"
            )

            if not isinstance(skill_mirror, dict):
                raise RuntimeError(
                    "Latest assessment is missing skill_mirror"
                )

            if not isinstance(next_examiner, dict):
                raise RuntimeError(
                    "Latest assessment is missing next_examiner"
                )

            validate_examiner_decision(next_examiner)

            return (
                skill_mirror,
                next_examiner,
                "persisted_next_examiner",
            )

        # 没有历史评估时，创建初始 Skill Mirror，
        # 并调用 A Examiner 选择第一题。
        skill_mirror = build_demo_skill_mirror(user_id)

        examiner_decision = (
            await client.examiner_decide(
                skill_mirror=skill_mirror,
                evidence_history=[],
                previous_challenges=[],
            )
        )

        if not isinstance(examiner_decision, dict):
            raise RuntimeError(
                "A Examiner returned an invalid decision"
            )

        validate_examiner_decision(examiner_decision)

        return (
            skill_mirror,
            examiner_decision,
            "initial_examiner",
        )

    async def start_fixed_challenge(
        self,
        *,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """
        保留旧方法名以兼容现有路由。

        实际行为：
        - 第一次挑战：初始 Skill Mirror -> A Examiner；
        - 后续挑战：使用上一轮 Assessment 返回的
          updated_skill_mirror 和 next_examiner。
        """

        client = AClient()

        (
            skill_mirror,
            examiner_decision,
            selection_source,
        ) = await self._select_challenge_context(
            client=client,
            user_id=user_id,
        )

        # 获取包含隐藏测试和 A 签名的内部版本。
        # 此对象只能存放在 B 后端。
        server_response = (
            await client.generate_challenge(
                examiner_decision,
                response_view="server",
            )
        )

        # 获取可以安全返回浏览器的学习者版本。
        learner_response = (
            await client.generate_challenge(
                examiner_decision,
                response_view="learner",
            )
        )

        if server_response.get("view") != "server":
            raise RuntimeError(
                "A service did not return server challenge view"
            )

        if learner_response.get("view") != "learner":
            raise RuntimeError(
                "A service did not return learner challenge view"
            )

        server_challenge = server_response.get(
            "challenge"
        )

        learner_challenge = learner_response.get(
            "challenge"
        )

        if not isinstance(server_challenge, dict):
            raise RuntimeError(
                "A server challenge is missing or invalid"
            )

        if not isinstance(learner_challenge, dict):
            raise RuntimeError(
                "A learner challenge is missing or invalid"
            )

        validate_learner_safety(learner_challenge)

        server_id = server_challenge.get(
            "challenge_id"
        )

        learner_id = learner_challenge.get(
            "challenge_id"
        )

        if not server_id or server_id != learner_id:
            raise RuntimeError(
                "Server and learner challenge_id do not match"
            )

        server_digest = server_challenge.get(
            "content_hash"
        )

        learner_digest = learner_challenge.get(
            "content_hash"
        )

        if (
            not server_digest
            or not learner_digest
            or server_digest != learner_digest
        ):
            raise RuntimeError(
                "Server and learner challenge digest "
                "do not match"
            )

        expected_skill = examiner_decision.get(
            "target_skill"
        )

        if (
            server_challenge.get("target_skill")
            != expected_skill
        ):
            raise RuntimeError(
                "Challenge target_skill does not match "
                "the Examiner decision"
            )

        expected_subskill = examiner_decision.get(
            "target_subskill"
        )

        if (
            server_challenge.get("target_subskill")
            != expected_subskill
        ):
            raise RuntimeError(
                "Challenge target_subskill does not match "
                "the Examiner decision"
            )

        entry_point = server_challenge.get(
            "entry_point"
        )

        if (
            not isinstance(entry_point, str)
            or not entry_point
        ):
            raise RuntimeError(
                "Challenge entry_point is missing"
            )

        test_cases = server_challenge.get(
            "test_cases"
        )

        if (
            not isinstance(test_cases, list)
            or not test_cases
        ):
            raise RuntimeError(
                "Server challenge has no trusted test cases"
            )

        provenance = server_challenge.get(
            "provenance"
        )

        if not isinstance(provenance, dict):
            raise RuntimeError(
                "Server challenge is missing A provenance"
            )

        challenge_store.save(
            session_id,
            {
                "user_id": user_id,
                "session_id": session_id,
                "skill_mirror": skill_mirror,
                "examiner_decision":
                    examiner_decision,
                "selection_source":
                    selection_source,
                "server_challenge":
                    server_challenge,
                "learner_challenge":
                    learner_challenge,
            },
        )

        # 只返回 learner challenge。
        return {
            "user_id": user_id,
            "session_id": session_id,
            "examiner_decision":
                examiner_decision,
            "challenge": learner_challenge,
        }


agent_orchestrator_service = (
    AgentOrchestratorService()
)