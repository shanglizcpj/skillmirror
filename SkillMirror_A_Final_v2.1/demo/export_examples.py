"""Regenerate committed JSON examples from the executable demo."""
from __future__ import annotations

from pathlib import Path
import json

from run_a_demo import ROOT, run_demo


def _write(name: str, payload) -> None:
    path = ROOT / "examples" / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    result = run_demo()
    accepted = result["evidence_materialization"]["accepted"]
    _write("full_a_demo_output.json", result)
    _write("evidence_examples.json", accepted)
    _write("skill_update_input.json", {
        "skill_id": "debugging",
        "previous_score": 70,
        "trusted_evidence": [item for item in accepted if item["skill"] == "debugging"],
        "trusted_evidence_history": [],
    })


if __name__ == "__main__":
    main()
