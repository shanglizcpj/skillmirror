import logging

from fastapi import APIRouter, HTTPException

from .assessment_service import (
    AssessmentError,
    assessment_service,
)
from .client import AServiceError
from .schemas import CompleteAssessmentRequest


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/agent",
    tags=["Agent Assessment"],
)


@router.post("/assessments/complete")
async def complete_assessment(
    payload: CompleteAssessmentRequest,
):
    try:
        return await assessment_service.complete(
            user_id=payload.user_id,
            session_id=payload.session_id,
            submitted_code=payload.submitted_code,
            elapsed_seconds=payload.elapsed_seconds,
        )

    except AssessmentError as exc:
        logger.exception(
            "Assessment validation failed"
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AServiceError as exc:
        logger.exception(
            "A assessment API rejected request"
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message":
                    "A assessment API rejected request",
                "a_status_code": exc.status_code,
                "a_path": exc.path,
                "a_response": exc.response_body,
            },
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected assessment error"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        ) from exc