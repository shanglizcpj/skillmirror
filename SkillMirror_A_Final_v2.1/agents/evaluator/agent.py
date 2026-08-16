"""Evaluator Agent (A8): explain process and propose verifiable events."""
from __future__ import annotations

from difflib import SequenceMatcher
from hashlib import sha256
from typing import Any, Dict, List, Optional
import json
import re

from agents.common import render_prompt, safe_llm_json
from skill_engine.provenance import sign_verification_record
from skill_engine.schema_validation import validate_payload


def _canonical(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest(data: Any) -> str:
    return "sha256:" + sha256(_canonical(data).encode("utf-8")).hexdigest()


def _norm(code: str) -> str:
    return re.sub(r"\s+", "", code or "")


def _record(
    ref_id: str,
    record_type: str,
    source: Dict[str, Any],
    *,
    user_id: str,
    session_id: str,
    challenge_id: str,
    hint_level: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "ref_id": ref_id,
        "type": record_type,
        "status": "verified" if source.get("verification_status") == "verified" else "unverified",
        "user_id": user_id,
        "session_id": session_id,
        "challenge_id": challenge_id,
        "timestamp": source.get("timestamp"),
        "payload_digest": _digest(source),
        **({"hint_level": hint_level} if hint_level else {}),
    }


def _test_summary(item: Dict[str, Any]) -> Optional[tuple[int, int]]:
    try:
        passed, total = int(item.get("passed")), int(item.get("total"))
    except (TypeError, ValueError):
        return None
    if total <= 0 or passed < 0 or passed > total:
        return None
    return passed, total


def _regression_count(item: Dict[str, Any]) -> Optional[int]:
    try:
        count = int(item.get("regressions", 0) or 0)
    except (TypeError, ValueError):
        return None
    return count if count >= 0 else None


def evaluate(
    challenge: Dict[str, Any],
    action_logs: Optional[List[Dict[str, Any]]] = None,
    code_versions: Optional[List[Dict[str, Any]]] = None,
    test_results: Optional[List[Dict[str, Any]]] = None,
    hint_history: Optional[List[Dict[str, Any]]] = None,
    submitted_code: str = "",
    elapsed_seconds: Optional[float] = None,
    llm=None,
    *,
    user_id: str,
    session_id: str,
    verification_provenance_secret: str | bytes | None = None,
    llm_timeout_seconds: float = 8.0,
) -> Dict[str, Any]:
    logs, versions, tests, hints = action_logs or [], code_versions or [], test_results or [], hint_history or []
    challenge_id = str(challenge.get("challenge_id") or "")
    target_skill = challenge.get("target_skill")
    candidates: List[Dict[str, Any]] = []
    records: List[Dict[str, Any]] = []
    flags: List[str] = []
    if not isinstance(submitted_code, str) or not submitted_code.strip():
        flags.append("empty_submission")

    event_refs: Dict[str, List[str]] = {}
    event_to_type = {
        "code_executed": "run_log",
        "run_program": "run_log",
        "custom_test_added": "custom_test_log",
        "boundary_input_tested": "custom_test_log",
        "bug_reproduced": "error_reproduction_log",
        "reproduced_error": "error_reproduction_log",
    }
    for index, log in enumerate(logs):
        event = log.get("event")
        record_type = event_to_type.get(event)
        if not record_type:
            continue
        ref_id = str(log.get("log_id") or f"LOG-{index + 1}")
        records.append(_record(ref_id, record_type, log, user_id=user_id, session_id=session_id, challenge_id=challenge_id))
        event_refs.setdefault(event, []).append(ref_id)

    valid_tests: List[tuple[Dict[str, Any], int, int, str, str]] = []
    for index, test in enumerate(tests):
        summary = _test_summary(test)
        if summary is None:
            flags.append("malformed_test_result")
            continue
        passed, total = summary
        regressions = _regression_count(test)
        if regressions is None:
            flags.append("malformed_test_result")
            continue
        ref_id = str(test.get("run_id") or f"RUN-{index + 1}")
        scope = test.get("scope")
        if regressions > 0:
            record_type = "regression_test_result"
        elif scope in {"hidden", "hidden_and_public"}:
            record_type = "hidden_test_result"
        else:
            record_type = "public_test_result"
        record = _record(ref_id, record_type, test, user_id=user_id, session_id=session_id, challenge_id=challenge_id)
        records.append(record)
        if test.get("verification_status") != "verified":
            flags.append("unverified_test_result")
        valid_tests.append((test, passed, total, ref_id, record_type))

    hint_refs = []
    for index, hint in enumerate(hints):
        try:
            level = int(hint.get("level", 0) or 0)
        except (TypeError, ValueError):
            flags.append("malformed_hint_record")
            continue
        if level not in {1, 2, 3}:
            continue
        ref_id = str(hint.get("hint_id") or f"HINT-{index + 1}")
        hint_refs.append((level, ref_id))
        records.append(_record(
            ref_id,
            "hint_record",
            hint,
            user_id=user_id,
            session_id=session_id,
            challenge_id=challenge_id,
            hint_level=f"level_{level}",
        ))

    last_verified = next((
        item for item in reversed(valid_tests)
        if item[0].get("verification_status") == "verified" and item[4] == "hidden_test_result"
    ), None)
    if last_verified and submitted_code.strip():
        test, passed, total, ref_id, _record_type = last_verified
        if passed == total:
            refs = [ref_id] + ([max(hint_refs)[1]] if hint_refs else [])
            candidates.append({
                "event": "challenge_tests_passed",
                "verification_refs": refs,
                "hint_level": f"level_{max(hint_refs)[0]}" if hint_refs else "none",
                "reason": f"{passed}/{total} verified hidden tests passed for {target_skill}.",
            })

    if target_skill == "debugging":
        run_refs = event_refs.get("code_executed", []) + event_refs.get("run_program", [])
        if run_refs:
            candidates.append({"event": "ran_program_proactively", "verification_refs": [run_refs[0]], "reason": "Learner executed the program during diagnosis."})
        boundary_refs = event_refs.get("custom_test_added", []) + event_refs.get("boundary_input_tested", [])
        if boundary_refs:
            candidates.append({"event": "designed_boundary_input_proactively", "verification_refs": [boundary_refs[0]], "reason": "Learner tested a boundary input."})
        reproduce_refs = event_refs.get("bug_reproduced", []) + event_refs.get("reproduced_error", [])
        if reproduce_refs:
            candidates.append({"event": "reproduced_bug_before_modification", "verification_refs": [reproduce_refs[0]], "reason": "Learner reproduced the failure before editing."})

        passed_counts = [passed for _test, passed, _total, _ref, _type in valid_tests]
        no_progress = 0
        for previous, current in zip(passed_counts, passed_counts[1:]):
            no_progress = no_progress + 1 if current <= previous else 0
        if len(passed_counts) >= 2:
            history_ref = "TH-" + sha256(_canonical(tests).encode("utf-8")).hexdigest()[:12]
            history_source = {"verification_status": "verified" if all(test.get("verification_status") == "verified" for test in tests) else "unverified", "tests": tests}
            records.append(_record(history_ref, "test_history", history_source, user_id=user_id, session_id=session_id, challenge_id=challenge_id))
            if no_progress >= 2:
                candidates.append({"event": "repeated_ineffective_modifications", "verification_refs": [history_ref], "reason": "At least two consecutive changes produced no verified progress."})
            elif passed_counts[0] < valid_tests[0][2]:
                candidates.append({"event": "first_fix_failed", "verification_refs": [history_ref], "reason": "The first unsuccessful fix is retained as neutral process context."})
        regression = next((item for item in reversed(valid_tests) if (_regression_count(item[0]) or 0) > 0 and item[0].get("verification_status") == "verified"), None)
        if regression:
            candidates.append({"event": "introduced_new_bug_after_fix", "verification_refs": [regression[3]], "reason": "A previously passing case regressed after a modification."})

    if hint_refs:
        level, ref_id = max(hint_refs)
        candidates.append({"event": f"used_hint_level_{level}", "verification_refs": [ref_id], "reason": f"Learner used a Level-{level} hint."})

    reference = challenge.get("reference_solution", "")
    if reference and submitted_code.strip():
        similarity = SequenceMatcher(None, _norm(reference), _norm(submitted_code)).ratio()
        if similarity >= 0.98 and (len(versions) <= 1 or len(logs) <= 2):
            flags.append("possible_direct_copy")

    final = last_verified
    if final:
        _, passed, total, _, _ = final
        debug_text = f"Final verified tests: {passed}/{total}." if target_skill == "debugging" else "Challenge did not target debugging."
    else:
        debug_text = "No valid verified hidden-test result was provided."
    result = {
        "problem_solving_analysis": "Learner process was reconstructed from verified logs, versions, tests and hints." if logs or tests else "Insufficient process history.",
        "debugging_analysis": debug_text,
        "testing_analysis": "Learner-created boundary activity was observed." if event_refs.get("custom_test_added") or event_refs.get("boundary_input_tested") else "No learner-created boundary activity was observed.",
        "reasoning_summary": "Evaluator proposes named events only; Evidence Engine locks rule fields and requires matching verified records.",
        "evidence_candidates": candidates,
        "verification_records": records,
        "flags": sorted(set(flags)),
        "analysis_source": "deterministic_verified_logs",
        "elapsed_seconds": elapsed_seconds,
    }
    prompt = render_prompt(
        "evaluator",
        {
            "challenge": {key: value for key, value in challenge.items() if key not in {"reference_solution", "test_cases"}},
            "action_logs": logs,
            "code_versions": versions,
            "test_results": tests,
            "hint_history": hints,
            "locked_facts": result,
        },
        "evaluator_llm_output.schema.json",
    )
    model = safe_llm_json(
        llm,
        prompt,
        schema_name="evaluator_llm_output.schema.json",
        timeout_seconds=llm_timeout_seconds,
    )
    if model:
        for key in ("problem_solving_analysis", "debugging_analysis", "testing_analysis", "reasoning_summary"):
            result[key] = model[key]
        result["analysis_source"] = "llm_text_refinement_over_locked_facts"
    for record in result["verification_records"]:
        record.update({
            "challenge_digest": challenge.get("content_hash"),
            "target_skill": challenge.get("target_skill"),
            "target_subskill": challenge.get("target_subskill"),
            "difficulty": challenge.get("difficulty"),
        })
    if verification_provenance_secret is not None:
        result["verification_records"] = [
            sign_verification_record(record, verification_provenance_secret)
            for record in result["verification_records"]
        ]
    validate_payload(result, "evaluator_output.schema.json")
    return result
