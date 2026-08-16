"""Reproducible A-side demo with explicit simulation disclosure."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.challenge_generator import generate_challenge, public_challenge
from agents.coach import coach
from agents.examiner import examine
from skill_engine.challenge_validation import canonical_digest, run_code_tests
from skill_engine.pipeline import complete_assessment
from skill_engine.provenance import content_digest, sign_b_record, sign_challenge


def run_demo():
    """Run a simulated learner sequence; actual tests execute in a subprocess.

    Per-run ephemeral keys demonstrate the production signing flow without
    embedding a reusable service secret in source or requiring deployment
    environment variables for this local demo.
    """
    now = datetime(2026, 8, 14, 3, 0, tzinfo=timezone.utc)
    b_demo_secret = secrets.token_urlsafe(48)
    a_demo_secret = secrets.token_urlsafe(48)
    skill_mirror = {"user_id": "U-DEMO", "skills": [
        {"skill_id": "coding", "score": 78, "confidence": 0.81},
        {"skill_id": "debugging", "score": None, "confidence": 0.0, "subskills": [{"id": "boundary_awareness", "score": None, "confidence": 0.0}]},
        {"skill_id": "testing", "score": 61, "confidence": 0.42},
        {"skill_id": "problem_solving", "score": 70, "confidence": 0.68},
        {"skill_id": "code_reading", "score": 74, "confidence": 0.76},
    ]}
    examiner = examine(skill_mirror)
    challenge = sign_challenge(generate_challenge(examiner), a_demo_secret)
    hint = coach(
        challenge,
        challenge["starter_code"],
        {"passed": 3, "total": 4},
        [],
        failed_attempts=2,
        asked_for_hint=True,
    )
    simulated_submission = (
        "def average_price(values):\n"
        "    if len(values) == 0:\n"
        "        return 0\n"
        "    return sum(values) / len(values)\n\n"
        "def discounted_total(prices, threshold=100):\n"
        "    if len(prices) == 0:\n"
        "        return 0\n"
        "    total = sum(prices)\n"
        "    if average_price(prices) > threshold:\n"
        "        return total * 0.9\n"
        "    return total\n"
    )
    actual_run = run_code_tests(simulated_submission, challenge["entry_point"], challenge["test_cases"])
    identity = {
        "user_id": "U-DEMO",
        "session_id": "SESSION-DEMO-001",
        "challenge_id": challenge["challenge_id"],
    }

    def signed_record(record_type, **fields):
        return sign_b_record(
            {"record_type": record_type, **identity, **fields},
            b_demo_secret,
        )

    test_result_summary = {
        "run_id": "RUN-DEMO-002",
        "passed": actual_run["passed"],
        "total": actual_run["total"],
        "scope": "hidden_and_public",
        "runner": "a_side_demo_isolated_subprocess",
        "timestamp": "2026-08-14T02:10:00+00:00",
        "result_digest": canonical_digest(actual_run),
        "submission_digest": content_digest(simulated_submission),
        "challenge_digest": challenge["content_hash"],
    }
    payload = {
        "user_id": "U-DEMO",
        "session_id": "SESSION-DEMO-001",
        "skill_mirror": skill_mirror,
        "challenge": challenge,
        "action_logs": [
            signed_record("action_log", log_id="LOG-DEMO-001", event="code_executed", timestamp="2026-08-14T02:01:00+00:00"),
            signed_record("action_log", log_id="LOG-DEMO-002", event="reproduced_error", timestamp="2026-08-14T02:02:00+00:00"),
            signed_record("action_log", log_id="LOG-DEMO-003", event="boundary_input_tested", timestamp="2026-08-14T02:04:00+00:00"),
        ],
        "code_versions": [
            signed_record("code_version", version=1, code_digest=canonical_digest(challenge["starter_code"])),
            signed_record("code_version", version=2, code_digest=canonical_digest(simulated_submission)),
        ],
        "test_results": [signed_record("test_result", **test_result_summary)],
        "hint_history": [signed_record(
            "hint_record", hint_id="HINT-DEMO-001", level=1,
            timestamp="2026-08-14T02:03:00+00:00",
        )],
        "submitted_code": simulated_submission,
        "elapsed_seconds": 540,
        "evidence_history": [],
        "previous_challenges": [],
        "timestamp": "2026-08-14T02:11:00+00:00",
    }
    completed = complete_assessment(
        payload,
        b_provenance_secret=b_demo_secret,
        a_evidence_secret=a_demo_secret,
        now=now,
    )
    return {
        "demo_disclosure": "Simulated learner action sequence for engineering verification; not a real-user experiment. Test execution is an actual isolated local subprocess run.",
        "examiner": examiner,
        "challenge": public_challenge(challenge),
        "coach": hint,
        "actual_test_run": {
            "passed": actual_run["passed"],
            "total": actual_run["total"],
            "runner": test_result_summary["runner"],
            "result_digest": test_result_summary["result_digest"],
        },
        **completed,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
