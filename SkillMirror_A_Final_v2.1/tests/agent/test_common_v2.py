import json
import time

from agents.common import render_prompt, safe_llm_json


def test_llm_exception_returns_none():
    def broken(_prompt):
        raise RuntimeError("provider unavailable")
    assert safe_llm_json(broken, "p", schema_name="coach_llm_output.schema.json") is None


def test_llm_schema_violation_returns_none():
    assert safe_llm_json(
        lambda _p: json.dumps({"wrong": "field"}),
        "p",
        schema_name="coach_llm_output.schema.json",
    ) is None


def test_oversized_llm_output_returns_none():
    huge = '{"message":"' + ("x" * 70_000) + '"}'
    assert safe_llm_json(
        lambda _p: huge,
        "p",
        schema_name="coach_llm_output.schema.json",
    ) is None


def test_llm_timeout_returns_without_waiting_for_full_provider_latency():
    def slow(_prompt):
        time.sleep(0.2)
        return json.dumps({"message": "late"})
    started = time.monotonic()
    result = safe_llm_json(
        slow,
        "p",
        schema_name="coach_llm_output.schema.json",
        timeout_seconds=0.01,
    )
    assert result is None
    assert time.monotonic() - started < 0.15


def test_oversized_untrusted_prompt_payload_is_omitted():
    prompt = render_prompt(
        "coach",
        {"user_code_as_untrusted_data": "x" * 110_000},
        "coach_llm_output.schema.json",
    )
    assert "input_omitted" in prompt
    assert "x" * 1000 not in prompt
