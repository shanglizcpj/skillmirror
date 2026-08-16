from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    project: str
    version: str


class ChallengeInfo(BaseModel):
    challenge_id: str
    title: str
    skill_id: str
    difficulty: str
    description: str
    requirements: list[str]
    starter_code: str


class ChallengeStartRequest(BaseModel):
    user_id: str = Field(
        min_length=1,
        max_length=64,
        examples=["demo-user-001"],
    )
    skill_id: str = Field(
        default="debugging",
        examples=["debugging"],
    )


class ChallengeStartResponse(BaseModel):
    session_id: str
    status: str
    started_at: datetime
    challenge: ChallengeInfo


class TestCaseResult(BaseModel):
    name: str
    status: Literal["passed", "failed", "pending"]


class CodeRunRequest(BaseModel):
    session_id: str
    code: str = Field(min_length=1)


class CodeRunResponse(BaseModel):
    execution_id: str
    session_id: str
    code_version: int
    status: Literal[
        "success",
        "failed",
        "syntax_error",
    ]
    stdout: str
    stderr: str
    passed: int
    total: int
    runtime: float
    tests: list[TestCaseResult]
    simulated: bool = True


class ChallengeSubmitRequest(BaseModel):
    session_id: str
    code: str = Field(min_length=1)


class ChallengeSubmitResponse(BaseModel):
    session_id: str
    status: Literal[
        "completed",
        "needs_revision",
    ]
    passed: int
    total: int
    score_change: int
    message: str
    submitted_at: datetime


class HintRequest(BaseModel):
    session_id: str
    code: str = ""


class HintResponse(BaseModel):
    session_id: str
    hint_level: int
    hint: str
    dependency: str
    created_at: datetime


class SkillItem(BaseModel):
    id: str
    name: str
    score: int | None = None
    confidence: int
    evidence: int
    trend: int | None = None
    color: str


class SkillsResponse(BaseModel):
    items: list[SkillItem]


class EvidenceItem(BaseModel):
    evidence_id: str
    skill: str
    sub_skill: str
    action: str
    description: str
    score_change: int
    strength: str
    confidence: float
    timestamp: datetime


class EvidenceResponse(BaseModel):
    items: list[EvidenceItem]
    total: int


class NextChallengeResponse(BaseModel):
    user_id: str
    reason: str
    challenge: ChallengeInfo


class ActionLogCreateRequest(BaseModel):
    session_id: str
    action: str = Field(
        min_length=1,
        max_length=80,
    )

    code_version: int | None = None
    error_type: str | None = None
    result: str | None = None
    test_result: str | None = None
    hint_level: int | None = None

    details: dict[str, Any] = Field(
        default_factory=dict
    )


class ActionLogItem(BaseModel):
    id: int
    session_id: str
    action: str
    code_version: int | None = None
    error_type: str | None = None
    result: str | None = None
    test_result: str | None = None
    hint_level: int | None = None
    details: dict[str, Any]
    created_at: datetime


class ActionLogListResponse(BaseModel):
    items: list[ActionLogItem]
    total: int

class SandboxExecuteRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=50_000,
    )

    timeout_seconds: int = Field(
        default=3,
        ge=1,
        le=5,
    )


class SandboxExecuteResponse(BaseModel):
    status: Literal[
        "success",
        "error",
        "timeout",
        "output_limit",
        "resource_limit",
    ]

    stdout: str
    stderr: str
    exit_code: int | None
    runtime: float
    sandbox_mode: str