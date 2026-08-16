from fastapi import APIRouter


router = APIRouter(
    tags=["System"],
)


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "project": "SkillMirror",
        "version": "0.3.0",
        "assessment_mode": "trusted_agent_pipeline",
    }