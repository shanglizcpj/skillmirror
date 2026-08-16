from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.database.base import Base
from app.database.init_db import seed_database
from app.database.session import (
    SessionLocal,
    engine,
)
from app.test_runner.routes import (
    router as test_runner_router,
)
from app.agent_orchestrator.routes import router as agent_orchestrator_router
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
from app.debug_routes import router as debug_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as database:
        seed_database(database)

    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for the SkillMirror "
        "evidence-driven programming assessment system."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

install_error_handlers(app)

app.include_router(agent_orchestrator_router)

allowed_origins = list(
    {
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
app.include_router(test_runner_router)
app.include_router(assessment_router)
app.include_router(hint_router)
app.include_router(history_router)
app.include_router(debug_router)


@app.get("/", tags=["System"])
def root() -> dict:
    return {
        "message": "Welcome to SkillMirror API",
        "version": settings.app_version,
        "database": "SQLite",
        "docs": "/docs",
    }