from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartChallengeRequest(StrictModel):
    user_id: str = Field(
        min_length=1,
        max_length=128,
    )

    session_id: str = Field(
        min_length=1,
        max_length=128,
    )

class CompleteAssessmentRequest(StrictModel):
    user_id: str = Field(
        min_length=1,
        max_length=128,
    )

    session_id: str = Field(
        min_length=1,
        max_length=128,
    )

    submitted_code: str = Field(
        min_length=1,
        max_length=40_000,
    )

    elapsed_seconds: float | None = Field(
        default=None,
        ge=0,
    )

class HintRequest(StrictModel):
    user_id: str = Field(
        min_length=1,
        max_length=128,
    )

    session_id: str = Field(
        min_length=1,
        max_length=128,
    )

    user_code: str = Field(
        min_length=1,
        max_length=40_000,
    )

    failed_attempts: int = Field(
        default=0,
        ge=0,
    )

    asked_for_hint: bool = True