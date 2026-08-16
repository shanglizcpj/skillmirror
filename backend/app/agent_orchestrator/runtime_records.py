from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4
import json
import sqlite3

from .config import get_agent_settings
from .provenance import content_digest, sign_b_record
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


class SQLiteRuntimeRecordStore:
    def __init__(self):
        # 与server challenge使用同一个SQLite数据库。
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

    @contextmanager
    def _connection(
        self,
    ) -> Iterator[sqlite3.Connection]:
        connection = self._connect()

        try:
            with connection:
                yield connection
        finally:
            connection.close()
            
    def _initialize(self) -> None:
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS b_runtime_records (
                        record_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        challenge_id TEXT NOT NULL,
                        record_type TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_runtime_record_session
                    ON b_runtime_records(session_id)
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_runtime_record_type
                    ON b_runtime_records(record_type)
                    """
                )

    def save(
        self,
        *,
        record_id: str,
        record: dict[str, Any],
    ) -> None:
        with self._lock:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO b_runtime_records (
                        record_id,
                        user_id,
                        session_id,
                        challenge_id,
                        record_type,
                        payload_json,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        record["user_id"],
                        record["session_id"],
                        record["challenge_id"],
                        record["record_type"],
                        encode_json(record),
                        utc_now(),
                    ),
                )

    def count(
        self,
        *,
        session_id: str,
        record_type: str | None = None,
    ) -> int:
        with self._lock:
            with self._connection() as connection:
                if record_type is None:
                    row = connection.execute(
                        """
                        SELECT COUNT(*) AS total
                        FROM b_runtime_records
                        WHERE session_id = ?
                        """,
                        (session_id,),
                    ).fetchone()
                else:
                    row = connection.execute(
                        """
                        SELECT COUNT(*) AS total
                        FROM b_runtime_records
                        WHERE session_id = ?
                        AND record_type = ?
                        """,
                        (
                            session_id,
                            record_type,
                        ),
                    ).fetchone()

        return int(row["total"])

    def list_by_session(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        with self._lock:
            with self._connection() as connection:
                rows = connection.execute(
                    """
                    SELECT payload_json
                    FROM b_runtime_records
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                    """,
                    (session_id,),
                ).fetchall()

        return [
            json.loads(row["payload_json"])
            for row in rows
        ]


runtime_record_store = SQLiteRuntimeRecordStore()


def persist_test_run(
    *,
    user_id: str,
    session_id: str,
    submitted_code: str,
    test_result: dict[str, Any],
) -> dict[str, str]:
    challenge_record = challenge_store.get(session_id)

    if challenge_record is None:
        raise RuntimeError(
            "Cannot persist run: challenge session not found"
        )

    if challenge_record["user_id"] != user_id:
        raise RuntimeError(
            "Cannot persist run: user identity mismatch"
        )

    settings = get_agent_settings()
    timestamp = utc_now()

    id_suffix = uuid4().hex
    log_id = f"LOG-{id_suffix}"
    code_record_id = f"CODE-{id_suffix}"
    run_id = f"RUN-{id_suffix}"

    common = {
        "user_id": user_id,
        "session_id": session_id,
        "challenge_id":
            challenge_record["challenge_id"],
    }

    # 1. Action Logger记录。
    action_log = sign_b_record(
        {
            "record_type": "action_log",
            **common,
            "log_id": log_id,
            "event": "code_executed",
            "timestamp": timestamp,
        },
        settings.b_provenance_secret,
    )

    # 2. Code Version记录。
    version = runtime_record_store.count(
        session_id=session_id,
        record_type="code_version",
    ) + 1

    code_version = sign_b_record(
        {
            "record_type": "code_version",
            **common,
            "version": version,
            "code_digest":
                content_digest(submitted_code),
            "timestamp": timestamp,
        },
        settings.b_provenance_secret,
    )

    # 3. Test Runner结果记录。
    test_record = sign_b_record(
        {
            "record_type": "test_result",
            **common,
            "run_id": run_id,
            "passed": int(
                test_result.get("passed", 0)
            ),
            "total": int(
                test_result.get("total", 0)
            ),
            "scope": "hidden_and_public",
            "runner": "skillmirror-b-docker-sandbox",
            "sandbox_mode": test_result.get(
                "sandbox_mode",
                "unknown",
            ),
            "status": test_result.get(
                "status",
                "unknown",
            ),
            "runtime": float(
                test_result.get("runtime", 0)
            ),
            "regressions": 0,
            "timestamp": timestamp,

            # A侧会严格验证这两个摘要。
            "submission_digest":
                content_digest(submitted_code),

            "challenge_digest":
                challenge_record["challenge_digest"],

            "result_digest": content_digest({
                "status": test_result.get("status"),
                "passed": test_result.get("passed"),
                "total": test_result.get("total"),
                "public_passed":
                    test_result.get("public_passed"),
                "public_total":
                    test_result.get("public_total"),
                "hidden_passed":
                    test_result.get("hidden_passed"),
                "hidden_total":
                    test_result.get("hidden_total"),
            }),
        },
        settings.b_provenance_secret,
    )

    runtime_record_store.save(
        record_id=log_id,
        record=action_log,
    )

    runtime_record_store.save(
        record_id=code_record_id,
        record=code_version,
    )

    runtime_record_store.save(
        record_id=run_id,
        record=test_record,
    )

    return {
        "log_id": log_id,
        "code_record_id": code_record_id,
        "run_id": run_id,
    }