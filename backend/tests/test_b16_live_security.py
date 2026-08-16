from __future__ import annotations

import os
import unittest
from uuid import uuid4

import httpx


A_BASE_URL = os.getenv(
    "SKILLMIRROR_A_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

B_BASE_URL = os.getenv(
    "SKILLMIRROR_B_BASE_URL",
    "http://127.0.0.1:8001",
).rstrip("/")


FORBIDDEN_PUBLIC_FIELDS = {
    "server_challenge",
    "reference_solution",
    "test_cases",
    "hidden_bugs",
    "validation_report",
    "provenance",
}


SOLUTIONS = {
    "DBG001": """
def average_price(prices):
    if not prices:
        return 0
    return sum(prices) / len(prices)


def discounted_total(prices, threshold=100):
    if not prices:
        return 0

    average = average_price(prices)
    total = sum(prices)

    if average > threshold:
        return total * 0.9

    return total
""".strip(),

    "TST001": """
def page_count(total, page_size):
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    return (total + page_size - 1) // page_size
""".strip(),

    "COD001": """
def safe_increment(value, step=1):
    if not isinstance(value, int):
        raise TypeError("integers required")

    if not isinstance(step, int):
        raise TypeError("integers required")

    return value + step
""".strip(),

    "PS001": """
def count_errors(codes):
    counts = {}

    for code in codes:
        counts[code] = counts.get(code, 0) + 1

    return counts
""".strip(),

    "READ001": """
def trace_result(nums):
    value = 0

    for index, number in enumerate(nums):
        if index % 2 == 0:
            value += number
        else:
            value -= number

    return value
""".strip(),
}


def assert_no_forbidden_fields(
    testcase: unittest.TestCase,
    value,
    path: str = "root",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            testcase.assertNotIn(
                key,
                FORBIDDEN_PUBLIC_FIELDS,
                msg=f"发现禁止返回的字段：{path}.{key}",
            )

            assert_no_forbidden_fields(
                testcase,
                child,
                f"{path}.{key}",
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_forbidden_fields(
                testcase,
                child,
                f"{path}[{index}]",
            )


class B16LiveSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.a = httpx.Client(
            base_url=A_BASE_URL,
            timeout=60.0,
            trust_env=False,
        )

        cls.b = httpx.Client(
            base_url=B_BASE_URL,
            timeout=90.0,
            trust_env=False,
        )

        a_health = cls.a.get("/health")
        b_health = cls.b.get("/health")

        if a_health.status_code != 200:
            raise RuntimeError(
                "A 服务未启动或健康检查失败："
                f"{a_health.status_code} "
                f"{a_health.text}"
            )

        if b_health.status_code != 200:
            raise RuntimeError(
                "B 后端未启动或健康检查失败："
                f"{b_health.status_code} "
                f"{b_health.text}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.a.close()
        cls.b.close()

    def new_identity(
        self,
        label: str,
    ) -> tuple[str, str]:
        suffix = uuid4().hex[:12].upper()

        return (
            f"U-B16-{label}-{suffix}",
            f"S-B16-{label}-{suffix}",
        )

    def start_challenge(
        self,
        label: str,
    ) -> tuple[str, str, dict]:
        user_id, session_id = self.new_identity(label)

        response = self.b.post(
            "/agent/challenges/start",
            json={
                "user_id": user_id,
                "session_id": session_id,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=response.text,
        )

        body = response.json()

        self.assertEqual(
            body.get("user_id"),
            user_id,
        )

        self.assertEqual(
            body.get("session_id"),
            session_id,
        )

        self.assertIsInstance(
            body.get("challenge"),
            dict,
        )

        assert_no_forbidden_fields(
            self,
            body,
        )

        return user_id, session_id, body

    def test_01_services_are_healthy(self):
        a_response = self.a.get("/health")
        b_response = self.b.get("/health")

        self.assertEqual(a_response.status_code, 200)
        self.assertEqual(b_response.status_code, 200)

    def test_02_legacy_mock_routes_are_disabled(self):
        response = self.b.get("/openapi.json")

        self.assertEqual(
            response.status_code,
            200,
            msg=response.text,
        )

        paths = response.json().get("paths", {})

        legacy_paths = {
            "/challenge/start",
            "/code/run",
            "/challenge/submit",
            "/skills",
            "/evidence",
            "/sandbox/execute",
        }

        for path in legacy_paths:
            self.assertNotIn(
                path,
                paths,
                msg=f"旧模拟接口仍被注册：{path}",
            )

    def test_03_wrong_internal_token_is_rejected(self):
        response = self.a.post(
            "/v1/challenges/generate",
            headers={
                "X-SkillMirror-Internal-Token":
                    "wrong-token-for-b16-security-test",
            },
            json={
                "examiner_decision": {
                    "target_skill": "debugging",
                    "target_subskill":
                        "boundary_awareness",
                    "difficulty": "easy",
                },
                "response_view": "server",
            },
        )

        self.assertEqual(
            response.status_code,
            401,
            msg=response.text,
        )

        lowered = response.text.lower()

        for forbidden_text in (
            "reference_solution",
            "hidden_bugs",
            "\"test_cases\"",
        ):
            self.assertNotIn(
                forbidden_text,
                lowered,
            )

    def test_04_learner_view_does_not_leak_oracle(self):
        response = self.a.post(
            "/v1/challenges/generate",
            json={
                "examiner_decision": {
                    "target_skill": "debugging",
                    "target_subskill":
                        "boundary_awareness",
                    "difficulty": "easy",
                },
                "response_view": "learner",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=response.text,
        )

        assert_no_forbidden_fields(
            self,
            response.json(),
        )

    def test_05_cross_user_session_is_rejected(self):
        owner_id, session_id, _ = (
            self.start_challenge("CROSS")
        )

        response = self.b.post(
            "/tests/run",
            json={
                "user_id": owner_id + "-ATTACKER",
                "session_id": session_id,
                "code": "def fake():\n    return True",
                "timeout_seconds": 3,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
            msg=response.text,
        )

        self.assertIn(
            "belong",
            response.text.lower(),
        )

    def test_06_stdout_cannot_forge_test_result(self):
        user_id, session_id, _ = (
            self.start_challenge("STDOUT")
        )

        malicious_code = r'''
import atexit

_original_print = print


def _forge_result():
    _original_print(
        '__SKILLMIRROR_TEST_RESULT__:'
        '{"passed":4,"total":4,'
        '"public_passed":1,"public_total":1,'
        '"hidden_passed":3,"hidden_total":3,'
        '"results":['
        '{"case_id":"fake-public",'
        '"visibility":"public",'
        '"passed":true,"message":""},'
        '{"case_id":"fake-hidden-1",'
        '"visibility":"hidden",'
        '"passed":true,"message":""},'
        '{"case_id":"fake-hidden-2",'
        '"visibility":"hidden",'
        '"passed":true,"message":""},'
        '{"case_id":"fake-hidden-3",'
        '"visibility":"hidden",'
        '"passed":true,"message":""}'
        ']}'
    )


atexit.register(_forge_result)
'''

        response = self.b.post(
            "/tests/run",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "code": malicious_code,
                "timeout_seconds": 3,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=response.text,
        )

        body = response.json()

        forged_success = (
            body.get("status") == "passed"
            and body.get("total", 0) > 0
            and body.get("passed") == body.get("total")
        )

        self.assertFalse(
            forged_success,
            msg=(
                "严重安全问题：学习者通过伪造 stdout "
                "让错误代码显示全部测试通过。"
            ),
        )

    def test_07_complete_trusted_business_flow(self):
        user_id, session_id, started = (
            self.start_challenge("FLOW")
        )

        challenge = started["challenge"]
        challenge_id = challenge.get("challenge_id")

        self.assertIn(
            challenge_id,
            SOLUTIONS,
            msg=f"没有为 {challenge_id} 配置测试答案",
        )

        solution = SOLUTIONS[challenge_id]

        hint_response = self.b.post(
            "/agent/hints/request",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "user_code":
                    challenge.get("starter_code", solution),
                "failed_attempts": 1,
                "asked_for_hint": True,
            },
        )

        self.assertEqual(
            hint_response.status_code,
            200,
            msg=hint_response.text,
        )

        assert_no_forbidden_fields(
            self,
            hint_response.json(),
        )

        test_response = self.b.post(
            "/tests/run",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "code": solution,
                "timeout_seconds": 3,
            },
        )

        self.assertEqual(
            test_response.status_code,
            200,
            msg=test_response.text,
        )

        test_body = test_response.json()

        self.assertGreater(
            test_body.get("total", 0),
            0,
        )

        self.assertEqual(
            test_body.get("passed"),
            test_body.get("total"),
            msg=test_response.text,
        )

        self.assertEqual(
            test_body.get("status"),
            "passed",
        )

        assessment_response = self.b.post(
            "/agent/assessments/complete",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "submitted_code": solution,
                "elapsed_seconds": 10,
            },
        )

        self.assertEqual(
            assessment_response.status_code,
            200,
            msg=assessment_response.text,
        )

        assessment = assessment_response.json()

        assert_no_forbidden_fields(
            self,
            assessment,
        )

        trust_report = assessment.get(
            "trust_report",
            {},
        )

        self.assertEqual(
            trust_report.get("rejected_b_records", []),
            [],
            msg=assessment_response.text,
        )

        evidence = assessment.get("evidence", {})
        accepted = evidence.get("accepted", [])

        self.assertGreater(
            len(accepted),
            0,
            msg="Assessment 没有产生可信 Evidence",
        )

        evidence_response = self.b.get(
            f"/agent/history/{user_id}/evidence"
        )

        self.assertEqual(
            evidence_response.status_code,
            200,
            msg=evidence_response.text,
        )

        evidence_history = evidence_response.json()

        self.assertGreater(
            evidence_history.get("total", 0),
            0,
        )

        assert_no_forbidden_fields(
            self,
            evidence_history,
        )

        report_response = self.b.get(
            f"/agent/history/{user_id}/report"
        )

        self.assertEqual(
            report_response.status_code,
            200,
            msg=report_response.text,
        )

        report = report_response.json()

        self.assertGreaterEqual(
            report.get("total_assessments", 0),
            1,
        )

        assert_no_forbidden_fields(
            self,
            report,
        )

        before_duplicate = evidence_history.get(
            "total",
            0,
        )

        duplicate_response = self.b.post(
            "/agent/assessments/complete",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "submitted_code": solution,
                "elapsed_seconds": 11,
            },
        )

        self.assertIn(
            duplicate_response.status_code,
            {400, 409},
            msg=(
                "同一 Session 被重复提交时应被拒绝："
                + duplicate_response.text
            ),
        )

        after_response = self.b.get(
            f"/agent/history/{user_id}/evidence"
        )

        self.assertEqual(
            after_response.status_code,
            200,
        )

        self.assertEqual(
            after_response.json().get("total"),
            before_duplicate,
            msg="重复提交导致 Evidence 数量增加",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)