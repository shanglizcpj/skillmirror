import unittest

from app.agent_orchestrator.assessment_store import (
    assessment_store,
)
from app.agent_orchestrator.history_service import (
    get_public_assessment_report,
)


class HistoryServiceTests(unittest.TestCase):
    def test_rejected_evidence_history_count(self):
        original_method = (
            assessment_store.get_assessment_history
        )

        assessment_store.get_assessment_history = (
            lambda user_id: [
                {
                    "session_id": "S-TEST-001",
                    "user_id": user_id,
                    "challenge_id": "DBG001",
                    "created_at":
                        "2026-08-16T12:00:00+00:00",
                    "challenge_summary": {
                        "target_skill": "debugging",
                        "target_subskill":
                            "boundary_awareness",
                        "difficulty": "easy",
                    },
                    "response": {
                        "score": {
                            "new_score": 80,
                        },
                        "confidence": {
                            "confidence_percent": 50,
                        },
                        "evidence_materialization": {
                            "accepted": [],
                            "rejected": [],
                        },
                        "trust_report": {
                            "rejected_b_records": [],
                            "rejected_evidence_history": [
                                {
                                    "reason":
                                        "invalid_evidence_signature",
                                }
                            ],
                            "replayed_evidence": [],
                            (
                                "caller_verification_"
                                "status_trusted"
                            ): False,
                        },
                    },
                    "skill_mirror": {
                        "skills": [],
                    },
                    "next_examiner": {},
                }
            ]
        )

        try:
            report = get_public_assessment_report(
                "U-TEST"
            )
        finally:
            (
                assessment_store
                .get_assessment_history
            ) = original_method

        self.assertEqual(
            report["latest"]["trust_summary"][
                "rejected_history_count"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()