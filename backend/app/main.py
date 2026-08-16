import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.system_routes import router as system_router
from app.test_runner.routes import (
    router as test_runner_router,
)
from app.agent_orchestrator.routes import (
    router as agent_orchestrator_router,
)
from app.agent_orchestrator.assessment_routes import (
    router as assessment_router,
)
from app.agent_orchestrator.hint_routes import (
    router as hint_router,
)
from app.agent_orchestrator.history_routes import (
    router as history_router,
)
from app.error_handlers import install_error_handlers


settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    description=(
        "SkillMirror trusted evidence-driven programming assessment backend. "
        "Competition demo identity notice: user_id and session_id are demo "
        "routing identifiers, not production authentication, authorization, "
        "or tenant-isolation credentials."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


install_error_handlers(app)


allowed_origins = list(
    {
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    }
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(system_router)
app.include_router(agent_orchestrator_router)
app.include_router(test_runner_router)
app.include_router(assessment_router)
app.include_router(hint_router)
app.include_router(history_router)


if os.getenv(
    "SKILLMIRROR_ENABLE_FAILURE_TESTS",
    "0",
) == "1":
    from app.debug_routes import router as debug_router

    app.include_router(debug_router)


@app.get("/", tags=["System"])
def root() -> dict:
    return {
        "message": "SkillMirror Trusted Assessment API",
        "version": "0.3.0",
        "docs": "/docs",
    }