"""FastAPI adapter for member-B server-to-server integration."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agents.challenge_generator import generate_challenge, public_challenge
from agents.coach import coach
from agents.examiner import examine
from skill_engine.confidence_engine import calculate_confidence
from skill_engine.evidence import load_rules, materialize_evidence
from skill_engine.pipeline import complete_assessment
from skill_engine.provenance import sign_challenge, verify_evidence
from skill_engine.schema_validation import validate_payload
from skill_engine.skill_engine import calculate_skill_update
from skill_engine.skill_tree import load_skill_tree
from .security import a_evidence_secret, b_provenance_secret, require_internal
from .models import (
    ChallengeRequest,
    CoachRequest,
    CompleteAssessmentRequest,
    EvidenceRequest,
    ExaminerRequest,
    SkillUpdateRequest,
)

app = FastAPI(
    title="SkillMirror Member-A API",
    version="2.1.0",
    description="Deterministic Agent/Evidence/Score/Confidence interface for member B.",
)


def configure_llm(provider) -> None:
    """Inject an optional callable ``provider(prompt) -> JSON string``.

    The default is None, so the complete service remains reproducible without a
    commercial model. Production composition can install a provider once during
    application startup; every Agent still validates and can fall back.
    """
    app.state.llm_provider = provider


def _llm(request: Request):
    return getattr(request.app.state, "llm_provider", None)


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok", "service": "skillmirror-a", "version": "2.1.0", "llm_required": False}


@app.get("/v1/skill-tree")
def skill_tree():
    return load_skill_tree()


@app.post("/v1/examiner/decide")
def examiner_decide(payload: ExaminerRequest, request: Request):
    require_internal(request)
    return examine(
        payload.skill_mirror,
        payload.evidence_history,
        payload.previous_challenges,
        llm=_llm(request),
    )


@app.post("/v1/challenges/generate")
def challenges_generate(payload: ChallengeRequest, request: Request):
    if payload.response_view == "server":
        require_internal(request)
    internal = generate_challenge(payload.examiner_decision, llm=_llm(request))
    if payload.response_view == "server":
        internal = sign_challenge(internal, a_evidence_secret())
        return {
            "view": "server",
            "challenge": internal,
            "security_note": "This response contains hidden oracle data. Keep it on the trusted B-side server.",
        }
    return {"view": "learner", "challenge": public_challenge(internal)}


@app.post("/v1/coach/hint")
def coach_hint(payload: CoachRequest, request: Request):
    return coach(
        payload.challenge,
        payload.user_code,
        payload.test_results,
        payload.hint_history,
        payload.failed_attempts,
        payload.asked_for_hint,
        llm=_llm(request),
    )


@app.post("/v1/evidence/materialize")
def evidence_materialize(payload: EvidenceRequest, request: Request):
    require_internal(request)
    return materialize_evidence(
        payload.candidates,
        context=payload.context,
        verification_records=payload.verification_records,
        provenance_secret=a_evidence_secret(),
    )


@app.post("/v1/skills/update")
def skills_update(payload: SkillUpdateRequest, request: Request):
    require_internal(request)
    secret = a_evidence_secret()
    expected_rule_version = load_rules()["version"]
    all_evidence = payload.trusted_evidence_history + payload.trusted_evidence
    seen_ids = set()
    history_ids = {
        item.get("evidence_id") for item in payload.trusted_evidence_history
        if isinstance(item, dict)
    }
    for index, item in enumerate(all_evidence):
        try:
            validate_payload(item, "evidence.schema.json")
        except ValueError as exc:
            raise ValueError(f"trusted evidence at index {index} has invalid schema") from exc
        if item.get("rule_version") != expected_rule_version or not verify_evidence(item, secret):
            raise ValueError(f"trusted evidence at index {index} has invalid provenance or rule version")
        evidence_id = item["evidence_id"]
        if evidence_id in seen_ids:
            if index >= len(payload.trusted_evidence_history) and evidence_id in history_ids:
                raise ValueError(f"trusted_evidence replays evidence already present in history: {evidence_id}")
            raise ValueError(f"trusted evidence at index {index} duplicates evidence_id: {evidence_id}")
        seen_ids.add(evidence_id)
    score = calculate_skill_update(
        payload.previous_score,
        payload.trusted_evidence,
        skill_id=payload.skill_id,
        evidence_secret=secret,
    )
    confidence = calculate_confidence(
        all_evidence,
        skill_id=payload.skill_id,
        evidence_secret=secret,
    )
    return {"score": score, "confidence": confidence}


@app.post("/v1/assessment/complete")
def assessment_complete(payload: CompleteAssessmentRequest, request: Request):
    require_internal(request)
    return complete_assessment(
        payload.model_dump(),
        b_provenance_secret=b_provenance_secret(),
        a_evidence_secret=a_evidence_secret(),
        llm=_llm(request),
    )
