from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExaminerRequest(StrictModel):
    skill_mirror: Dict[str, Any]
    evidence_history: List[Dict[str, Any]] = Field(default_factory=list, max_length=5000)
    previous_challenges: List[Dict[str, Any]] = Field(default_factory=list, max_length=1000)


class ChallengeRequest(StrictModel):
    examiner_decision: Dict[str, Any]
    response_view: Literal["learner", "server"] = "learner"


class CoachRequest(StrictModel):
    challenge: Dict[str, Any]
    user_code: str = Field(max_length=100_000)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    hint_history: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    failed_attempts: int = Field(default=0, ge=0)
    asked_for_hint: bool = True


class EvidenceRequest(StrictModel):
    candidates: List[Dict[str, Any]] = Field(max_length=1000)
    context: Dict[str, Any]
    verification_records: List[Dict[str, Any]] = Field(max_length=5000)


class SkillUpdateRequest(StrictModel):
    skill_id: str
    previous_score: Optional[float] = Field(default=None, ge=0, le=100)
    trusted_evidence: List[Dict[str, Any]] = Field(max_length=1000)
    trusted_evidence_history: List[Dict[str, Any]] = Field(default_factory=list, max_length=5000)


class CompleteAssessmentRequest(StrictModel):
    user_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    skill_mirror: Dict[str, Any]
    challenge: Dict[str, Any]
    action_logs: List[Dict[str, Any]] = Field(default_factory=list, max_length=5000)
    code_versions: List[Dict[str, Any]] = Field(default_factory=list, max_length=1000)
    test_results: List[Dict[str, Any]] = Field(default_factory=list, max_length=1000)
    hint_history: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    submitted_code: str = Field(max_length=100_000)
    elapsed_seconds: Optional[float] = Field(default=None, ge=0)
    evidence_history: List[Dict[str, Any]] = Field(default_factory=list, max_length=5000)
    previous_challenges: List[Dict[str, Any]] = Field(default_factory=list, max_length=1000)
    timestamp: Optional[str] = None
