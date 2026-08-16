from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TestRunRequest(StrictModel):
    user_id: str = Field(
        min_length=1,
        max_length=128,
    )

    session_id: str = Field(
        min_length=1,
        max_length=128,
    )

    code: str = Field(
        min_length=1,
        max_length=40_000,
    )

    timeout_seconds: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class TestRunResponse(StrictModel):
    status: str
    challenge_id: str
    challenge_digest: str

    passed: int
    total: int

    public_passed: int
    public_total: int

    hidden_passed: int
    hidden_total: int

    failed_cases: list[dict[str, Any]]

    runtime: float
    sandbox_mode: str