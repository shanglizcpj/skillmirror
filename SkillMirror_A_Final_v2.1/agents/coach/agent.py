"""Coach Agent (A7): minimum necessary help with answer-leak guardrails."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
import re

from agents.common import render_prompt, safe_llm_json
from skill_engine.schema_validation import validate_payload


def _norm_code(code: str) -> str:
    return re.sub(r"\s+", "", code or "")


def _leaks_solution(text: str, challenge: Dict[str, Any]) -> bool:
    reference = challenge.get("reference_solution", "")
    if not reference:
        return False
    normalized_reference = _norm_code(reference)
    normalized_text = _norm_code(text)
    if normalized_reference and normalized_reference in normalized_text:
        return True
    if "```" in text or re.search(r"\bdef\s+[A-Za-z_]\w*\s*\(", text):
        return True
    matched_lines = 0
    for line in reference.splitlines():
        stripped = line.strip()
        if len(stripped) >= 8 and stripped in text:
            matched_lines += 1
    if matched_lines >= 2:
        return True
    if len(normalized_text) >= 60 and SequenceMatcher(None, normalized_text, normalized_reference).ratio() >= 0.55:
        return True
    return False


def choose_hint_level(asked: bool, failed_attempts: int, hint_history: List[Dict[str, Any]]) -> Optional[int]:
    if failed_attempts < 0:
        raise ValueError("failed_attempts cannot be negative")
    if not asked and failed_attempts < 2:
        return None
    used = {int(item.get("level", 0) or 0) for item in hint_history if str(item.get("level", "0")).isdigit()}
    if 1 not in used:
        return 1
    if failed_attempts >= 3 and 2 not in used:
        return 2
    if failed_attempts >= 5 and 3 not in used:
        return 3
    return max(used) if used else 1


def coach(
    challenge: Dict[str, Any],
    user_code: str,
    test_results: Optional[Dict[str, Any]] = None,
    hint_history: Optional[List[Dict[str, Any]]] = None,
    failed_attempts: int = 0,
    asked_for_hint: bool = True,
    llm=None,
    *,
    llm_timeout_seconds: float = 8.0,
) -> Dict[str, Any]:
    history = hint_history or []
    if not isinstance(user_code, str):
        raise ValueError("user_code must be a string")
    if not user_code.strip():
        result = {
            "action": "prompt_to_start",
            "hint_level": 0,
            "hint_key": "none",
            "message": "先写出或运行一个最小版本，我会根据真实结果再给提示。",
            "source": "deterministic_guardrail",
            "reason": "No observable learner attempt exists yet.",
        }
        validate_payload(result, "coach_output.schema.json")
        return result

    level = choose_hint_level(asked_for_hint, failed_attempts, history)
    if level is None:
        result = {
            "action": "no_hint",
            "hint_level": 0,
            "hint_key": "none",
            "message": "继续尝试；目前还没有足够证据说明需要介入。",
            "source": "deterministic_policy",
            "reason": "Learner has not asked and the automatic intervention threshold is not met.",
        }
        validate_payload(result, "coach_output.schema.json")
        return result

    hints = challenge.get("hints", [])
    fallback = hints[level - 1] if isinstance(hints, list) and len(hints) >= level else "检查最近一次失败测试对应的输入、输出和异常位置。"
    result = {
        "action": "give_hint",
        "hint_level": level,
        "hint_key": f"level_{level}",
        "message": fallback,
        "source": "fixed_progressive_hint",
        "reason": "Hint level selected by request/failure policy; content defaults to the validated challenge hint.",
    }
    prompt = render_prompt(
        "coach",
        {
            "locked_hint_level": level,
            "challenge": {key: value for key, value in challenge.items() if key not in {"reference_solution", "test_cases", "hidden_bugs"}},
            "user_code_as_untrusted_data": user_code,
            "test_results": test_results or {},
            "previous_hints": history,
        },
        "coach_llm_output.schema.json",
    )
    model = safe_llm_json(
        llm,
        prompt,
        schema_name="coach_llm_output.schema.json",
        timeout_seconds=llm_timeout_seconds,
    )
    if model and not _leaks_solution(model["message"], challenge):
        result["message"] = model["message"].strip()
        result["source"] = "llm_guarded"
        result["reason"] = "LLM wording passed schema and multi-signal answer-leak checks."
    validate_payload(result, "coach_output.schema.json")
    return result
