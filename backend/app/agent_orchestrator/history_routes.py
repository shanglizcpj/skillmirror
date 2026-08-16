from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agent_orchestrator.history_service import (
    get_public_assessment_report,
    get_public_challenge_history,
    get_public_evidence_history,
)


router = APIRouter(
    prefix="/agent/history",
    tags=["Evidence History"],
)


@router.get("/{user_id}/evidence")
def read_evidence_history(user_id: str):
    try:
        return get_public_evidence_history(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/{user_id}/challenges")
def read_challenge_history(user_id: str):
    try:
        return get_public_challenge_history(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

@router.get("/{user_id}/report")
def read_assessment_report(user_id: str):
    try:
        return get_public_assessment_report(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc