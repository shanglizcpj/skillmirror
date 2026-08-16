from __future__ import annotations

import logging
import sqlite3
import uuid
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response


logger = logging.getLogger("skillmirror.errors")


def get_request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)

    if existing:
        return str(existing)

    request_id = uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    return request_id


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = (
        request.headers.get("X-Request-ID")
        or uuid.uuid4().hex[:16]
    )

    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = get_request_id(request)

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "detail": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "请求数据格式不正确，请检查必填字段。",
                    "request_id": request_id,
                    "issues": exc.errors(),
                }
            }
        ),
        headers={
            "X-Request-ID": request_id,
        },
    )


async def database_exception_handler(
    request: Request,
    exc: sqlite3.Error,
) -> JSONResponse:
    request_id = get_request_id(request)

    logger.exception(
        "Database error. request_id=%s path=%s",
        request_id,
        request.url.path,
    )

    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "数据库暂时不可用，请稍后重试。",
                "request_id": request_id,
            }
        },
        headers={
            "X-Request-ID": request_id,
        },
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = get_request_id(request)

    logger.exception(
        "Unexpected server error. request_id=%s path=%s",
        request_id,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器发生异常，请稍后重试。",
                "request_id": request_id,
            }
        },
        headers={
            "X-Request-ID": request_id,
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    app.middleware("http")(request_id_middleware)

    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )

    app.add_exception_handler(
        sqlite3.Error,
        database_exception_handler,
    )

    app.add_exception_handler(
        Exception,
        unexpected_exception_handler,
    )