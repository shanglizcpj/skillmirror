"""JSON Schema loader used by Agents, examples, tests and the API boundary."""
from __future__ import annotations

from functools import lru_cache
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import json

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(TypeError, ValueError))
def _is_timezone_aware_datetime(value: Any) -> bool:
    if not isinstance(value, str) or "T" not in value:
        return False
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.tzinfo is not None


@lru_cache(maxsize=32)
def load_schema(name: str) -> Dict[str, Any]:
    if Path(name).name != name or not name.endswith(".json"):
        raise ValueError("schema name must be a JSON filename")
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def validate_payload(payload: Any, schema_name: str) -> None:
    validator = Draft202012Validator(load_schema(schema_name), format_checker=FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in errors[:8]
        )
        raise ValueError(f"{schema_name} validation failed: {details}")
