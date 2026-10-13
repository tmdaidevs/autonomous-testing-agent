from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    value = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return value.replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def slugify(value: str, fallback: str = "evidence") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or fallback


def safe_component(value: str, fallback: str = "item") -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return normalized or fallback


def resolve_run_path(run_dir: Path, relative_path: str) -> Path:
    base = run_dir.resolve()
    candidate = (base / Path(relative_path)).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as error:
        raise ValueError(
            f"Path escapes the run directory: {relative_path}"
        ) from error
    return candidate


def relative_posix(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()
