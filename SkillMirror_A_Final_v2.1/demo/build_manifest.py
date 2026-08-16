"""Build a deterministic SHA-256 manifest for source and deliverable files."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST_SHA256.txt"
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".git"}


def main() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == MANIFEST:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts) or path.suffix == ".pyc":
            continue
        digest = sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {relative.as_posix()}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
