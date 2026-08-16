from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Skill(Base):
    __tablename__ = "skills"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "skill_key",
            name="uq_user_skill",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    skill_key: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    confidence: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    evidence_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    trend: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    color: Mapped[str] = mapped_column(
        String(20),
        default="#3b82f6",
    )


class SubSkill(Base):
    __tablename__ = "sub_skills"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    skill_id: Mapped[str] = mapped_column(
        ForeignKey("skills.id"),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    confidence: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
    )

    skill_key: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )

    difficulty: Mapped[str] = mapped_column(
        String(30),
    )

    description: Mapped[str] = mapped_column(
        Text,
    )

    requirements_json: Mapped[str] = mapped_column(
        Text,
    )

    starter_code: Mapped[str] = mapped_column(
        Text,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class ChallengeSession(Base):
    __tablename__ = "challenge_sessions"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    challenge_id: Mapped[str] = mapped_column(
        ForeignKey("challenges.id"),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
    )

    code_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    hint_level: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("challenge_sessions.id"),
        index=True,
    )

    code: Mapped[str] = mapped_column(
        Text,
    )

    version: Mapped[int] = mapped_column(
        Integer,
    )

    submission_type: Mapped[str] = mapped_column(
        String(30),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("challenge_sessions.id"),
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(80),
        index=True,
    )

    detail_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    submission_id: Mapped[int] = mapped_column(
        ForeignKey("code_submissions.id"),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
    )

    passed: Mapped[int] = mapped_column(
        Integer,
    )

    total: Mapped[int] = mapped_column(
        Integer,
    )

    runtime: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    stdout: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    stderr: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tests_json: Mapped[str] = mapped_column(
        Text,
        default="[]",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("challenge_sessions.id"),
        nullable=True,
        index=True,
    )

    skill_key: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )

    sub_skill: Mapped[str] = mapped_column(
        String(100),
    )

    action: Mapped[str] = mapped_column(
        String(100),
    )

    description: Mapped[str] = mapped_column(
        Text,
    )

    score_change: Mapped[int] = mapped_column(
        Integer,
    )

    strength: Mapped[str] = mapped_column(
        String(30),
    )

    confidence: Mapped[float] = mapped_column(
        Float,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class HintRecord(Base):
    __tablename__ = "hint_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("challenge_sessions.id"),
        index=True,
    )

    hint_level: Mapped[int] = mapped_column(
        Integer,
    )

    hint: Mapped[str] = mapped_column(
        Text,
    )

    dependency: Mapped[str] = mapped_column(
        String(30),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )