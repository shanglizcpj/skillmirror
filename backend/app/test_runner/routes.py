from fastapi import APIRouter, HTTPException

from app.agent_orchestrator.runtime_records import (
    persist_test_run,
)

from .schemas import TestRunRequest, TestRunResponse
from .service import TestRunnerError, run_session_tests


router = APIRouter(
    prefix="/tests",
    tags=["Test Runner"],
)


@router.post(
    "/run",
    response_model=TestRunResponse,
)
def run_tests(
    payload: TestRunRequest,
):
    try:
        result = run_session_tests(
            user_id=payload.user_id,
            session_id=payload.session_id,
            code=payload.code,
            timeout_seconds=payload.timeout_seconds,
        )

        # 测试完成后，由B后端签名并保存记录。
        persist_test_run(
            user_id=payload.user_id,
            session_id=payload.session_id,
            submitted_code=payload.code,
            test_result=result,
        )

        return result

    except TestRunnerError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc