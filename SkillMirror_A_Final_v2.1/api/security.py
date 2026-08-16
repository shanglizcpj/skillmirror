"""Environment-backed internal API authentication and secret loading."""
from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request, status

from skill_engine.provenance import validate_secret


INTERNAL_TOKEN_ENV = "SKILLMIRROR_INTERNAL_TOKEN"
B_PROVENANCE_SECRET_ENV = "SKILLMIRROR_B_PROVENANCE_SECRET"
A_EVIDENCE_SECRET_ENV = "SKILLMIRROR_A_EVIDENCE_SECRET"
INTERNAL_TOKEN_HEADER = "X-SkillMirror-Internal-Token"


def _configured_secret(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"required internal security setting is not configured: {name}",
        )
    try:
        validate_secret(value, name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return value


def require_internal(request: Request) -> None:
    expected = _configured_secret(INTERNAL_TOKEN_ENV)
    supplied = request.headers.get(INTERNAL_TOKEN_HEADER)
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid internal service token",
            headers={"WWW-Authenticate": "SkillMirrorInternal"},
        )


def b_provenance_secret() -> str:
    return _configured_secret(B_PROVENANCE_SECRET_ENV)


def a_evidence_secret() -> str:
    return _configured_secret(A_EVIDENCE_SECRET_ENV)
