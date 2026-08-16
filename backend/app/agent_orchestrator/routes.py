import logging

from fastapi import APIRouter, HTTPException

from .client import AServiceError
from .schemas import StartChallengeRequest
from .service import agent_orchestrator_service
from .store import challenge_store


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/agent",
    tags=["Agent Orchestrator"],
)


@router.post("/challenges/start")
async def start_challenge(
    payload: StartChallengeRequest,
):
    try:
        return await agent_orchestrator_service.start_fixed_challenge(
            user_id=payload.user_id,
            session_id=payload.session_id,
        )

    except AServiceError as exc:
        logger.exception("A service rejected start challenge")

        raise HTTPException(
            status_code=502,
            detail={
                "message": "A service rejected the request",
                "a_status_code": exc.status_code,
                "a_path": exc.path,
                "a_response": exc.response_body,
            },
        ) from exc

    except RuntimeError as exc:
        logger.exception("Agent orchestrator runtime error")

        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "error_type": type(exc).__name__,
            },
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected agent orchestrator error")

        raise HTTPException(
            status_code=500,
            detail={
                "message": str(exc),
                "error_type": type(exc).__name__,
            },
        ) from exc


@router.get("/challenges/{session_id}/status")
def challenge_status(
    session_id: str,
):
    record = challenge_store.get(session_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Challenge session not found",
        )

    # 这里只返回安全状态，不能返回server_challenge。
    return {
        "found": True,
        "user_id": record["user_id"],
        "session_id": record["session_id"],
        "challenge_id": record["challenge_id"],
        "challenge_digest": record["challenge_digest"],
        "status": record["status"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
    }