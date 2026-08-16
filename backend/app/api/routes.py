from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.api_models import (
    ChallengeStartRequest,
    ChallengeStartResponse,
    ChallengeSubmitRequest,
    ChallengeSubmitResponse,
    CodeRunRequest,
    CodeRunResponse,
    EvidenceResponse,
    HealthResponse,
    HintRequest,
    HintResponse,
    NextChallengeResponse,
    SkillsResponse,
    ActionLogCreateRequest,
    ActionLogItem,
    ActionLogListResponse,
    SandboxExecuteRequest,
    SandboxExecuteResponse,
)
from app.services import database_service
from app.models.entities import ChallengeSession
from app.services import action_logger
from app.sandbox.executor import (
    SandboxUnavailableError,
    execute_python,
)


router = APIRouter()

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        project="SkillMirror",
        version="0.2.0",
    )


@router.post(
    "/challenge/start",
    response_model=ChallengeStartResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Challenge"],
)
def start_challenge(
    request: ChallengeStartRequest,
    database: DatabaseSession,
) -> dict:
    result = database_service.create_session(
        database=database,
        user_id=request.user_id,
        skill_id=request.skill_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No matching challenge found.",
        )

    return result


@router.post(
    "/code/run",
    response_model=CodeRunResponse,
    tags=["Code"],
)
def run_code(
    request: CodeRunRequest,
    database: DatabaseSession,
) -> dict:
    result = database_service.run_code(
        database=database,
        session_id=request.session_id,
        code=request.code,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Challenge session not found.",
        )

    return result


@router.post(
    "/challenge/submit",
    response_model=ChallengeSubmitResponse,
    tags=["Challenge"],
)
def submit_challenge(
    request: ChallengeSubmitRequest,
    database: DatabaseSession,
) -> dict:
    result = database_service.submit_challenge(
        database=database,
        session_id=request.session_id,
        code=request.code,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Challenge session not found.",
        )

    return result


@router.post(
    "/hint",
    response_model=HintResponse,
    tags=["Coach"],
)
def request_hint(
    request: HintRequest,
    database: DatabaseSession,
) -> dict:
    result = database_service.create_hint(
        database=database,
        session_id=request.session_id,
        code=request.code,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Challenge session not found.",
        )

    return result


@router.get(
    "/skills",
    response_model=SkillsResponse,
    tags=["Skills"],
)
def get_skills(
    database: DatabaseSession,
    user_id: str = Query(
        default="demo-user-001",
    ),
) -> dict:
    return {
        "items": database_service.get_skills(
            database=database,
            user_id=user_id,
        )
    }


@router.get(
    "/evidence",
    response_model=EvidenceResponse,
    tags=["Evidence"],
)
def get_evidence(
    database: DatabaseSession,
    user_id: str = Query(
        default="demo-user-001",
    ),
) -> dict:
    items = database_service.get_evidence(
        database=database,
        user_id=user_id,
    )

    return {
        "items": items,
        "total": len(items),
    }


@router.get(
    "/challenge/next",
    response_model=NextChallengeResponse,
    tags=["Challenge"],
)
def get_next_challenge(
    database: DatabaseSession,
    user_id: str = Query(
        default="demo-user-001",
    ),
) -> dict:
    result = database_service.get_next_challenge(
        database=database,
        user_id=user_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Next challenge not found.",
        )

    return result
@router.post(
    "/actions/log",
    response_model=ActionLogItem,
    status_code=status.HTTP_201_CREATED,
    tags=["Actions"],
)
def create_action_log(
    request: ActionLogCreateRequest,
    database: DatabaseSession,
) -> dict:
    challenge_session = database.get(
        ChallengeSession,
        request.session_id,
    )

    if challenge_session is None:
        raise HTTPException(
            status_code=404,
            detail="Challenge session not found.",
        )

    action = action_logger.record_action(
        database=database,
        session_id=request.session_id,
        action=request.action,
        code_version=request.code_version,
        error_type=request.error_type,
        result=request.result,
        test_result=request.test_result,
        hint_level=request.hint_level,
        details=request.details,
        commit=True,
    )

    return action_logger.serialize_action(
        action
    )


@router.get(
    "/sessions/{session_id}/actions",
    response_model=ActionLogListResponse,
    tags=["Actions"],
)
def get_session_actions(
    session_id: str,
    database: DatabaseSession,
) -> dict:
    challenge_session = database.get(
        ChallengeSession,
        session_id,
    )

    if challenge_session is None:
        raise HTTPException(
            status_code=404,
            detail="Challenge session not found.",
        )

    items = action_logger.get_session_actions(
        database=database,
        session_id=session_id,
    )

    return {
        "items": items,
        "total": len(items),
    }

@router.post(
    "/sandbox/execute",
    response_model=SandboxExecuteResponse,
    tags=["Sandbox"],
)
def execute_sandbox_code(
    request: SandboxExecuteRequest,
) -> dict:
    try:
        return execute_python(
            code=request.code,
            timeout_seconds=(
                request.timeout_seconds
            ),
        )

    except SandboxUnavailableError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error