from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any
import json
import sqlite3

from .store import challenge_store


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


class SQLiteAssessmentStore:
    def __init__(self):
        self.db_path = challenge_store.db_path
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.db_path),
            timeout=10,
        )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")

        return connection

    def _initialize(self) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assessment_results (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        challenge_id TEXT NOT NULL,
                        challenge_summary_json TEXT NOT NULL,
                        response_json TEXT NOT NULL,
                        skill_mirror_json TEXT NOT NULL,
                        next_examiner_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trusted_evidence_history (
                        evidence_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        challenge_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_evidence_history_user
                    ON trusted_evidence_history(user_id)
                    """
                )

    def get_evidence_history(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT payload_json
                    FROM trusted_evidence_history
                    WHERE user_id = ?
                    ORDER BY created_at ASC
                    """,
                    (user_id,),
                ).fetchall()

        return [
            json.loads(row["payload_json"])
            for row in rows
        ]

    def get_previous_challenges(
            self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT challenge_summary_json
                    FROM assessment_results
                    WHERE user_id = ?
                    ORDER BY created_at ASC
                    """,
                    (user_id,),
                ).fetchall()

        return [
            json.loads(row["challenge_summary_json"])
            for row in rows
        ]

    def get_assessment_history(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        session_id,
                        user_id,
                        challenge_id,
                        challenge_summary_json,
                        response_json,
                        skill_mirror_json,
                        next_examiner_json,
                        created_at
                    FROM assessment_results
                    WHERE user_id = ?
                    ORDER BY created_at ASC
                    """,
                    (user_id,),
                ).fetchall()

        return [
            {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "challenge_id": row["challenge_id"],
                "challenge_summary": json.loads(
                    row["challenge_summary_json"]
                ),
                "response": json.loads(
                    row["response_json"]
                ),
                "skill_mirror": json.loads(
                    row["skill_mirror_json"]
                ),
                "next_examiner": json.loads(
                    row["next_examiner_json"]
                ),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def save_completed_assessment(
        self,
        *,
        user_id: str,
        session_id: str,
        challenge: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        updated_mirror = response.get(
            "updated_skill_mirror"
        )

        next_examiner = response.get("next_examiner")

        if not isinstance(updated_mirror, dict):
            raise ValueError(
                "A response is missing updated_skill_mirror"
            )

        if not isinstance(next_examiner, dict):
            raise ValueError(
                "A response is missing next_examiner"
            )

        challenge_summary = {
            "challenge_id": challenge["challenge_id"],
            "target_skill": challenge["target_skill"],
            "target_subskill":
                challenge["target_subskill"],
            "difficulty": challenge["difficulty"],
        }

        materialization = response.get(
            "evidence_materialization",
            {},
        )

        accepted_evidence = materialization.get(
            "accepted",
            [],
        )

        now = utc_now()

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO assessment_results (
                        session_id,
                        user_id,
                        challenge_id,
                        challenge_summary_json,
                        response_json,
                        skill_mirror_json,
                        next_examiner_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_id,
                        challenge["challenge_id"],
                        encode_json(challenge_summary),
                        encode_json(response),
                        encode_json(updated_mirror),
                        encode_json(next_examiner),
                        now,
                    ),
                )

                for evidence in accepted_evidence:
                    evidence_id = evidence.get(
                        "evidence_id"
                    )

                    if not evidence_id:
                        continue

                    connection.execute(
                        """
                        INSERT OR IGNORE INTO
                        trusted_evidence_history (
                            evidence_id,
                            user_id,
                            session_id,
                            challenge_id,
                            payload_json,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            evidence_id,
                            user_id,
                            session_id,
                            challenge["challenge_id"],
                            encode_json(evidence),
                            now,
                        ),
                    )


assessment_store = SQLiteAssessmentStore()