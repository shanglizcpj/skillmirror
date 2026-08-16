from dataclasses import dataclass
from functools import lru_cache
import os


def require_secret(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"{name} is not configured")

    if len(value.encode("utf-8")) < 32:
        raise RuntimeError(f"{name} must contain at least 32 bytes")

    return value


@dataclass(frozen=True)
class AgentSettings:
    a_base_url: str
    internal_token: str
    b_provenance_secret: str


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings(
        a_base_url=os.getenv(
            "SKILLMIRROR_A_BASE_URL",
            "http://127.0.0.1:8000",
        ).rstrip("/"),
        internal_token=require_secret(
            "SKILLMIRROR_INTERNAL_TOKEN"
        ),
        b_provenance_secret=require_secret(
            "SKILLMIRROR_B_PROVENANCE_SECRET"
        ),
    )