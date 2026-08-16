from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import hmac
import json
import sqlite3
import tempfile
import unittest

import httpx
from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    BACKEND_ROOT / ".env",
    override=False,
)


from app.agent_orchestrator.assessment_store import (
    SQLiteAssessmentStore,
)
from app.agent_orchestrator.provenance import (
    canonical_json,
    sign_b_record,
)
from app.agent_orchestrator.store import (
    challenge_store,
)
from tests.test_b16_live_security import (
    B_BASE_URL,
    SOLUTIONS,
)


def verify_b_record_locally(
    record: dict,
    secret: str,
) -> bool:
    provenance = record.get("provenance")

    if not isinstance(provenance, dict):
        return False

    signature = provenance.get("signature", "")

    envelope = {
        key: value
        for key, value in provenance.items()
        if key != "signature"
    }

    payload = {
        key: deepcopy(value)
        for key, value in record.items()
        if key not in {
            "provenance",
            "verification_status",
        }
    }

    signature_input = canonical_json({
        "envelope": envelope,
        "payload": payload,
    }).encode("utf-8")

    expected = hmac.new(
        secret.encode("utf-8"),
        signature_input,
        sha256,
    ).hexdigest()

    return hmac.compare_digest(
        signature,
        f"hmac-sha256:{expected}",
    )


class B16PersistenceSecurityTests(
    unittest.TestCase,
):
    def test_01_tampering_invalidates_b_signature(self):
        secret = (
            "b16-local-signature-test-secret-"
            "at-least-32-bytes"
        )

        record = {
            "record_type": "test_result",
            "user_id": "U-B16-SIGNATURE",
            "session_id": "S-B16-SIGNATURE",
            "challenge_id": "DBG001",
            "run_id": "RUN-B16",
            "passed": 0,
            "total": 4,
            "scope": "hidden_and_public",
            "submission_digest":
                "sha256:" + "1" * 64,
            "challenge_digest":
                "sha256:" + "2" * 64,
        }

        signed = sign_b_record(
            record,
            secret,
        )

        self.assertTrue(
            verify_b_record_locally(
                signed,
                secret,
            )
        )

        tampered = deepcopy(signed)
        tampered["passed"] = 4

        self.assertFalse(
            verify_b_record_locally(
                tampered,
                secret,
            ),
            msg=(
                "修改签名后的测试结果，"
                "签名验证却仍然成功"
            ),
        )

    def test_02_duplicate_evidence_is_stored_once(
        self,
    ):
        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp:
            database_path = (
                Path(temp) / "b16-security.db"
            )

            with patch.object(
                challenge_store,
                "db_path",
                database_path,
            ):
                store = SQLiteAssessmentStore()

            evidence = {
                "evidence_id": "EV-B16-DUPLICATE",
                "user_id": "U-B16-DUPLICATE",
                "session_id": "S-B16-ONE",
                "challenge_id": "DBG001",
                "skill": "debugging",
                "performance_score": 92,
            }

            challenge = {
                "challenge_id": "DBG001",
                "target_skill": "debugging",
                "target_subskill":
                    "boundary_awareness",
                "difficulty": "easy",
            }

            response = {
                "updated_skill_mirror": {
                    "user_id":
                        "U-B16-DUPLICATE",
                },
                "next_examiner": {
                    "target_skill": "testing",
                },
                "evidence_materialization": {
                    "accepted": [evidence],
                },
            }

            store.save_completed_assessment(
                user_id="U-B16-DUPLICATE",
                session_id="S-B16-ONE",
                challenge=challenge,
                response=response,
            )

            duplicate_evidence = deepcopy(
                evidence
            )

            duplicate_evidence["session_id"] = (
                "S-B16-TWO"
            )

            duplicate_response = deepcopy(
                response
            )

            duplicate_response[
                "evidence_materialization"
            ]["accepted"] = [
                duplicate_evidence
            ]

            store.save_completed_assessment(
                user_id="U-B16-DUPLICATE",
                session_id="S-B16-TWO",
                challenge=challenge,
                response=duplicate_response,
            )

            history = store.get_evidence_history(
                "U-B16-DUPLICATE"
            )

            self.assertEqual(
                len(history),
                1,
                msg=(
                    "相同 evidence_id "
                    "被重复保存到历史记录"
                ),
            )

            self.assertEqual(
                history[0]["evidence_id"],
                "EV-B16-DUPLICATE",
            )

    def test_03_a_rejects_tampered_b_record(
        self,
    ):
        client = httpx.Client(
            base_url=B_BASE_URL,
            timeout=90.0,
            trust_env=False,
        )

        suffix = uuid4().hex[:12].upper()
        user_id = f"U-B16-FORGE-{suffix}"
        session_id = f"S-B16-FORGE-{suffix}"

        try:
            start_response = client.post(
                "/agent/challenges/start",
                json={
                    "user_id": user_id,
                    "session_id": session_id,
                },
            )

            self.assertEqual(
                start_response.status_code,
                200,
                msg=start_response.text,
            )

            challenge = start_response.json()[
                "challenge"
            ]

            challenge_id = challenge[
                "challenge_id"
            ]

            self.assertIn(
                challenge_id,
                SOLUTIONS,
            )

            solution = SOLUTIONS[challenge_id]

            run_response = client.post(
                "/tests/run",
                json={
                    "user_id": user_id,
                    "session_id": session_id,
                    "code": solution,
                    "timeout_seconds": 3,
                },
            )

            self.assertEqual(
                run_response.status_code,
                200,
                msg=run_response.text,
            )

            self.assertEqual(
                run_response.json().get("status"),
                "passed",
            )

            database_path = challenge_store.db_path

            with sqlite3.connect(
                str(database_path),
                timeout=10,
            ) as connection:
                row = connection.execute(
                    """
                    SELECT
                        record_id,
                        payload_json
                    FROM b_runtime_records
                    WHERE session_id = ?
                    AND record_type = 'test_result'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (session_id,),
                ).fetchone()

                self.assertIsNotNone(
                    row,
                    msg=(
                        "没有找到B签名的测试记录。"
                        "本测试需要使用本地B后端。"
                    ),
                )

                record_id = row[0]
                original_json = row[1]
                tampered = json.loads(
                    original_json
                )

                # 修改签名覆盖的字段，
                # 但故意不重新生成签名。
                tampered["runner"] = (
                    "forged-browser-runner"
                )

                connection.execute(
                    """
                    UPDATE b_runtime_records
                    SET payload_json = ?
                    WHERE record_id = ?
                    """,
                    (
                        json.dumps(
                            tampered,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        record_id,
                    ),
                )

            try:
                assessment_response = client.post(
                    "/agent/assessments/complete",
                    json={
                        "user_id": user_id,
                        "session_id": session_id,
                        "submitted_code": solution,
                        "elapsed_seconds": 10,
                    },
                )
            finally:
                # 恢复原始记录，避免测试数据一直被篡改。
                with sqlite3.connect(
                    str(database_path),
                    timeout=10,
                ) as connection:
                    connection.execute(
                        """
                        UPDATE b_runtime_records
                        SET payload_json = ?
                        WHERE record_id = ?
                        """,
                        (
                            original_json,
                            record_id,
                        ),
                    )

            self.assertNotEqual(
                assessment_response.status_code,
                200,
                msg=(
                    "严重安全问题：A接受了被篡改的"
                    "B侧测试记录"
                ),
            )

            response_text = (
                assessment_response.text.lower()
            )

            rejection_markers = {
                "reject",
                "signature",
                "provenance",
                "hmac",
                "record",
            }

            self.assertTrue(
                any(
                    marker in response_text
                    for marker in rejection_markers
                ),
                msg=assessment_response.text,
            )

            history_response = client.get(
                f"/agent/history/"
                f"{user_id}/evidence"
            )

            self.assertEqual(
                history_response.status_code,
                200,
            )

            self.assertEqual(
                history_response.json().get(
                    "total"
                ),
                0,
                msg=(
                    "篡改记录被拒绝后，"
                    "不应产生可信Evidence"
                ),
            )

        finally:
            client.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)