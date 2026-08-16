from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
import json
import os
import sqlite3


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


def decode_json(value: str) -> Any:
    return json.loads(value)


class SQLiteChallengeStore:
    def __init__(self):
        backend_root = Path(__file__).resolve().parents[2]

        configured_path = os.getenv(
            "SKILLMIRROR_ORCHESTRATOR_DB_PATH"
        )

        if configured_path:
            self.db_path = Path(configured_path).resolve()
        else:
            self.db_path = (
                backend_root
                / "data"
                / "skillmirror_orchestrator.db"
            )

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.db_path),
            timeout=10,
        )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")

        return connection

    def _initialize(self) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_challenge_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        challenge_id TEXT NOT NULL,
                        challenge_digest TEXT NOT NULL,
                        status TEXT NOT NULL,
                        skill_mirror_json TEXT NOT NULL,
                        examiner_decision_json TEXT NOT NULL,
                        server_challenge_json TEXT NOT NULL,
                        learner_challenge_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_agent_challenge_user
                    ON agent_challenge_sessions(user_id)
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_agent_challenge_id
                    ON agent_challenge_sessions(challenge_id)
                    """
                )

    def save(
        self,
        session_id: str,
        value: dict[str, Any],
    ) -> None:
        server_challenge = value.get("server_challenge")
        learner_challenge = value.get("learner_challenge")

        if not isinstance(server_challenge, dict):
            raise ValueError(
                "server_challenge must be a dictionary"
            )

        if not isinstance(learner_challenge, dict):
            raise ValueError(
                "learner_challenge must be a dictionary"
            )

        challenge_id = server_challenge.get("challenge_id")
        challenge_digest = server_challenge.get("content_hash")

        if not challenge_id:
            raise ValueError(
                "server_challenge.challenge_id is missing"
            )

        if not challenge_digest:
            raise ValueError(
                "server_challenge.content_hash is missing"
            )

        now = utc_now()

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO agent_challenge_sessions (
                        session_id,
                        user_id,
                        challenge_id,
                        challenge_digest,
                        status,
                        skill_mirror_json,
                        examiner_decision_json,
                        server_challenge_json,
                        learner_challenge_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(session_id) DO UPDATE SET
                        user_id = excluded.user_id,
                        challenge_id = excluded.challenge_id,
                        challenge_digest = excluded.challenge_digest,
                        status = excluded.status,
                        skill_mirror_json =
                            excluded.skill_mirror_json,
                        examiner_decision_json =
                            excluded.examiner_decision_json,
                        server_challenge_json =
                            excluded.server_challenge_json,
                        learner_challenge_json =
                            excluded.learner_challenge_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        session_id,
                        value["user_id"],
                        challenge_id,
                        challenge_digest,
                        "active",
                        encode_json(value["skill_mirror"]),
                        encode_json(value["examiner_decision"]),
                        encode_json(server_challenge),
                        encode_json(learner_challenge),
                        now,
                        now,
                    ),
                )

    def get(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT *
                    FROM agent_challenge_sessions
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()

        if row is None:
            return None

        return {
            "user_id": row["user_id"],
            "session_id": row["session_id"],
            "challenge_id": row["challenge_id"],
            "challenge_digest": row["challenge_digest"],
            "status": row["status"],
            "skill_mirror": decode_json(
                row["skill_mirror_json"]
            ),
            "examiner_decision": decode_json(
                row["examiner_decision_json"]
            ),
            "server_challenge": decode_json(
                row["server_challenge_json"]
            ),
            "learner_challenge": decode_json(
                row["learner_challenge_json"]
            ),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def mark_completed(
        self,
        session_id: str,
    ) -> bool:
        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE agent_challenge_sessions
                    SET status = ?, updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        "completed",
                        utc_now(),
                        session_id,
                    ),
                )

                return cursor.rowcount > 0


challenge_store = SQLiteChallengeStore()