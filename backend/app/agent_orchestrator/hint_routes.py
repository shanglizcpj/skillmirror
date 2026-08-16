import logging

from fastapi import APIRouter, HTTPException

from .client import AServiceError
from .hint_service import HintError, hint_service
from .schemas import HintRequest


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/agent",
    tags=["Agent Coach"],
)


@router.post("/hints/request")
async def request_hint(
    payload: HintRequest,
):
    try:
        return await hint_service.request_hint(
            user_id=payload.user_id,
            session_id=payload.session_id,
            user_code=payload.user_code,
            failed_attempts=payload.failed_attempts,
            asked_for_hint=payload.asked_for_hint,
        )

    except HintError as exc:
        logger.exception(
            "Hint request validation failed"
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AServiceError as exc:
        logger.exception(
            "A Coach API rejected request"
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message":
                    "A Coach API rejected request",
                "a_status_code": exc.status_code,
                "a_path": exc.path,
                "a_response": exc.response_body,
            },
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected Hint error"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        ) from exc