from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/debug",
    tags=["Failure Tests"],
)


@router.get("/database-error")
async def simulate_database_error():
    enabled = (
        os.getenv(
            "SKILLMIRROR_ENABLE_FAILURE_TESTS",
            "0",
        )
        == "1"
    )

    if not enabled:
        raise HTTPException(
            status_code=404,
            detail="Failure tests are disabled",
        )

    raise sqlite3.OperationalError(
        "Simulated database failure for B12.5"
    )