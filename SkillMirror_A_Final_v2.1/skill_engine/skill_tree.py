from __future__ import annotations
from pathlib import Path
import json

from .schema_validation import validate_payload

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "skill_tree.json"


def load_skill_tree(path: str | None = None):
    p = Path(path) if path else DEFAULT_PATH
    tree = json.loads(p.read_text(encoding="utf-8"))
    validate_payload(tree, "skill_tree.schema.json")
    ids = []
    for skill in tree["root_skill"]["children"]:
        ids.append(skill["id"])
        ids.extend(child["id"] for child in skill.get("children", []))
    if len(ids) != len(set(ids)):
        raise ValueError("skill_tree contains duplicate skill/subskill IDs")
    return tree


def get_subskills(skill_id: str, path: str | None = None):
    tree = load_skill_tree(path)
    for skill in tree["root_skill"]["children"]:
        if skill["id"] == skill_id:
            return [x["id"] for x in skill.get("children", [])]
    return []


def validate_skill_pair(skill_id: str, sub_skill_id: str, path: str | None = None) -> bool:
    return sub_skill_id in get_subskills(skill_id, path)
