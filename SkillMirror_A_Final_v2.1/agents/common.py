"""Shared, fail-closed utilities for SkillMirror Agent modules."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import json
import re

from skill_engine.schema_validation import validate_payload

LLMCallable = Callable[[str], str]
PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
MAX_PROMPT_INPUT_CHARS = 100_000


def extract_json(text: str) -> Dict[str, Any]:
    """Parse one JSON object from plain text or a markdown JSON fence."""
    if not isinstance(text, str):
        raise ValueError("LLM output must be a string")
    stripped = text.strip()
    if len(stripped) > 100_000:
        raise ValueError("LLM output exceeds the 100 KB safety limit")
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.I)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        start, end = stripped.find("{"), stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        obj = json.loads(stripped[start : end + 1])
    if not isinstance(obj, dict):
        raise ValueError("Structured Agent output must be a JSON object")
    return obj


def safe_llm_json(
    llm: Optional[LLMCallable],
    prompt: str,
    *,
    schema_name: Optional[str] = None,
    timeout_seconds: float = 8.0,
) -> Optional[Dict[str, Any]]:
    """Call an injected model with a deadline; any failure signals fallback.

    Network clients should still configure their own connect/read timeouts. The
    wrapper rejects malformed or schema-invalid output before it can affect a
    deterministic decision.
    """
    if llm is None:
        return None
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="skillmirror-llm")
    future = executor.submit(llm, prompt)
    try:
        obj = extract_json(future.result(timeout=max(0.001, timeout_seconds)))
        if schema_name:
            validate_payload(obj, schema_name)
        return obj
    except (Exception, FutureTimeout):
        future.cancel()
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def compact_json(data: Any) -> str:
    """Serialize user-controlled content as quoted data, not instructions."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)


def render_prompt(name: str, payload: Dict[str, Any], schema_name: str) -> str:
    """Load the versioned prompt file used at runtime and inject data/schema."""
    prompt_path = PROMPT_DIR / f"{name}.txt"
    template = prompt_path.read_text(encoding="utf-8")
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    input_json = compact_json(payload)
    if len(input_json) > MAX_PROMPT_INPUT_CHARS:
        input_json = compact_json({
            "input_omitted": "Untrusted payload exceeded the runtime prompt limit; use deterministic locked facts/fallback."
        })
    return (
        template.replace("{{OUTPUT_SCHEMA}}", compact_json(schema))
        .replace("{{INPUT_JSON}}", input_json)
    )
