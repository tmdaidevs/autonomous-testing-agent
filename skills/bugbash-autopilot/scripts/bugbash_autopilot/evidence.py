from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, UnidentifiedImageError

from .io_utils import (
    read_json,
    relative_posix,
    safe_component,
    sha256_file,
    slugify,
    utc_now,
    write_json,
)


MANIFEST_PATH = Path("evidence") / "manifest.json"
RESULTS_PATH = Path("results.json")
ATTACHMENT_STATUSES = {
    "not_attempted",
    "uploaded",
    "blocked",
    "not_supported",
    "rejected",
}


class EvidenceError(RuntimeError):
    """Raised when evidence cannot be safely created or updated."""


def initialize_run(
    run_dir: Path,
    run_id: str,
    title: str,
    source_document: str | None = None,
    target_url: str | None = None,
    max_attachment_bytes: int = 2 * 1024 * 1024,
) -> tuple[Path, Path]:
    if max_attachment_bytes <= 0:
        raise ValueError("max_attachment_bytes must be greater than zero")

    results_path = run_dir / RESULTS_PATH
    manifest_path = run_dir / MANIFEST_PATH
    if results_path.exists() or manifest_path.exists():
        raise EvidenceError(
            f"Run already exists at {run_dir}. Refusing to overwrite it."
        )

    (run_dir / "evidence" / "originals").mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence" / "processed").mkdir(parents=True, exist_ok=True)
    created_at = utc_now()

    results = {
        "schema_version": 1,
        "run": {
            "id": run_id,
            "title": title,
            "source_document": source_document,
            "target_url": target_url,
            "created_at": created_at,
            "max_attachment_bytes": max_attachment_bytes,
        },
        "test_cases": [],
        "findings": [],
        "submissions": [],
    }
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": created_at,
        "policy": {
            "max_attachment_bytes": max_attachment_bytes,
            "preserve_originals": True,
        },
        "evidence": [],
    }
    write_json(results_path, results)
    write_json(manifest_path, manifest)
    return results_path, manifest_path


def parse_rectangle(value: str) -> tuple[int, int, int, int]:
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise ValueError(
            f"Rectangle must contain integers: {value!r}"
        ) from error
    if len(parts) != 4:
        raise ValueError(
            f"Rectangle must be x,y,width,height: {value!r}"
        )
    x, y, width, height = parts
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError(
            f"Rectangle values must be non-negative with positive size: {value!r}"
        )
    return x, y, width, height


def _validate_rectangles(
    rectangles: Iterable[tuple[int, int, int, int]],
    image_width: int,
    image_height: int,
) -> list[tuple[int, int, int, int]]:
    validated: list[tuple[int, int, int, int]] = []
    for x, y, width, height in rectangles:
        if x + width > image_width or y + height > image_height:
            raise EvidenceError(
                "Rectangle exceeds image bounds: "
                f"{x},{y},{width},{height} for {image_width}x{image_height}"
            )
        validated.append((x, y, width, height))
    return validated


def _next_evidence_number(entries: list[dict[str, Any]]) -> int:
    numbers: list[int] = []
    for entry in entries:
        evidence_id = str(entry.get("evidence_id", ""))
        if evidence_id.startswith("EVD-"):
            try:
                numbers.append(int(evidence_id[4:]))
            except ValueError:
                continue
    return max(numbers, default=0) + 1


def _save_with_limit(
    image: Image.Image,
    destination: Path,
    max_bytes: int,
) -> tuple[int, int, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    current = image.copy()
    if current.mode not in {"RGB", "RGBA", "P"}:
        current = current.convert("RGBA")

    def save(candidate: Image.Image) -> None:
        candidate.save(
            destination,
            format="PNG",
            optimize=True,
            compress_level=9,
        )

    save(current)
    while (
        destination.stat().st_size > max_bytes
        and current.width > 480
        and current.height > 320
    ):
        next_size = (
            max(480, int(current.width * 0.85)),
            max(320, int(current.height * 0.85)),
        )
        if next_size == current.size:
            break
        current = current.resize(next_size, Image.Resampling.LANCZOS)
        save(current)

    if destination.stat().st_size > max_bytes:
        quantized_source = current.convert("RGB")
        for colors in (128, 64, 32):
            quantized = quantized_source.quantize(
                colors=colors,
                method=Image.Quantize.MEDIANCUT,
            )
            save(quantized)
            current = quantized
            if destination.stat().st_size <= max_bytes:
                break

    final_bytes = destination.stat().st_size
    if final_bytes > max_bytes:
        destination.unlink(missing_ok=True)
        raise EvidenceError(
            f"Could not compress image below {max_bytes} bytes without "
            "reducing it below the minimum readable dimensions."
        )
    return current.width, current.height, final_bytes


def _link_evidence_to_results(
    run_dir: Path,
    evidence_id: str,
    test_case_id: str,
    finding_id: str | None,
) -> None:
    results_path = run_dir / RESULTS_PATH
    if not results_path.exists():
        return
    results = read_json(results_path)
    changed = False

    for test_case in results.get("test_cases", []):
        if test_case.get("id") == test_case_id:
            evidence_ids = test_case.setdefault("evidence_ids", [])
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
                changed = True

    if finding_id:
        for finding in results.get("findings", []):
            if finding.get("id") == finding_id:
                evidence_ids = finding.setdefault("evidence_ids", [])
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
                    changed = True

    if changed:
        write_json(results_path, results)


def add_evidence(
    run_dir: Path,
    source: Path,
    test_case_id: str,
    description: str,
    finding_id: str | None = None,
    page_url: str | None = None,
    action: str | None = None,
    expected: str = "",
    actual: str = "",
    captured_at: str | None = None,
    redactions: Iterable[tuple[int, int, int, int]] = (),
    highlights: Iterable[tuple[int, int, int, int]] = (),
    max_bytes: int | None = None,
) -> dict[str, Any]:
    manifest_path = run_dir / MANIFEST_PATH
    if not manifest_path.exists():
        raise EvidenceError(
            f"No evidence manifest found at {manifest_path}. Run init first."
        )
    if not source.is_file():
        raise FileNotFoundError(f"Evidence source does not exist: {source}")
    if not test_case_id.strip():
        raise ValueError("test_case_id is required")
    if not description.strip():
        raise ValueError("description is required")

    manifest = read_json(manifest_path)
    entries = manifest.setdefault("evidence", [])
    number = _next_evidence_number(entries)
    evidence_id = f"EVD-{number:03d}"
    case_component = safe_component(test_case_id, "CHECK")
    short_description = slugify(description)[:64]
    source_suffix = source.suffix.lower() or ".png"
    original_name = (
        f"{number:03d}-{case_component}-{short_description}{source_suffix}"
    )
    processed_name = (
        f"{number:03d}-{case_component}-{short_description}.png"
    )
    original_path = (
        run_dir / "evidence" / "originals" / case_component / original_name
    )
    processed_path = (
        run_dir / "evidence" / "processed" / case_component / processed_name
    )
    original_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, original_path)

    try:
        with Image.open(original_path) as loaded:
            loaded.load()
            image = loaded.copy()
    except UnidentifiedImageError as error:
        original_path.unlink(missing_ok=True)
        raise EvidenceError(f"Unsupported or invalid image: {source}") from error

    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA")
    validated_redactions = _validate_rectangles(
        redactions, image.width, image.height
    )
    validated_highlights = _validate_rectangles(
        highlights, image.width, image.height
    )
    draw = ImageDraw.Draw(image)
    for x, y, width, height in validated_redactions:
        draw.rectangle(
            (x, y, x + width, y + height),
            fill=(20, 20, 20, 255) if image.mode == "RGBA" else (20, 20, 20),
        )
    line_width = max(3, min(image.width, image.height) // 160)
    for x, y, width, height in validated_highlights:
        draw.rectangle(
            (x, y, x + width, y + height),
            outline=(220, 38, 38, 255)
            if image.mode == "RGBA"
            else (220, 38, 38),
            width=line_width,
        )

    attachment_limit = max_bytes or int(
        manifest.get("policy", {}).get(
            "max_attachment_bytes", 2 * 1024 * 1024
        )
    )
    width, height, byte_count = _save_with_limit(
        image,
        processed_path,
        attachment_limit,
    )
    entry: dict[str, Any] = {
        "evidence_id": evidence_id,
        "test_case_id": test_case_id,
        "finding_id": finding_id,
        "kind": "screenshot",
        "path": relative_posix(processed_path, run_dir),
        "original_path": relative_posix(original_path, run_dir),
        "description": description,
        "captured_at": captured_at or utc_now(),
        "page_url": page_url,
        "action": action,
        "expected": expected,
        "actual": actual,
        "sha256": sha256_file(processed_path),
        "original_sha256": sha256_file(original_path),
        "image": {
            "width": width,
            "height": height,
            "bytes": byte_count,
        },
        "redactions": [list(rectangle) for rectangle in validated_redactions],
        "highlights": [list(rectangle) for rectangle in validated_highlights],
        "attachment": {
            "status": "not_attempted",
            "external_tracking_id": None,
            "failure_reason": None,
        },
    }
    entries.append(entry)
    write_json(manifest_path, manifest)
    _link_evidence_to_results(
        run_dir,
        evidence_id,
        test_case_id,
        finding_id,
    )
    return entry


def record_upload(
    run_dir: Path,
    evidence_id: str,
    status: str,
    tracking_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    if status not in ATTACHMENT_STATUSES:
        raise ValueError(
            f"Invalid attachment status {status!r}; expected one of "
            f"{sorted(ATTACHMENT_STATUSES)}"
        )
    if status == "uploaded" and not tracking_id:
        raise ValueError("Uploaded evidence requires an external tracking ID")
    if status in {"blocked", "rejected"} and not reason:
        raise ValueError(f"{status} evidence requires a failure reason")

    manifest_path = run_dir / MANIFEST_PATH
    manifest = read_json(manifest_path)
    entry = next(
        (
            item
            for item in manifest.get("evidence", [])
            if item.get("evidence_id") == evidence_id
        ),
        None,
    )
    if entry is None:
        raise EvidenceError(f"Unknown evidence ID: {evidence_id}")

    entry["attachment"] = {
        "status": status,
        "external_tracking_id": tracking_id,
        "failure_reason": reason,
    }
    write_json(manifest_path, manifest)

    finding_id = entry.get("finding_id")
    results_path = run_dir / RESULTS_PATH
    if tracking_id and finding_id and results_path.exists():
        results = read_json(results_path)
        changed = False
        for finding in results.get("findings", []):
            if finding.get("id") == finding_id:
                tracking_ids = finding.setdefault(
                    "external_tracking_ids", []
                )
                if tracking_id not in tracking_ids:
                    tracking_ids.append(tracking_id)
                    changed = True
        if changed:
            write_json(results_path, results)
    return entry


def lookup_evidence(run_dir: Path, identifier: str) -> list[dict[str, Any]]:
    manifest = read_json(run_dir / MANIFEST_PATH)
    matches: list[dict[str, Any]] = []
    for entry in manifest.get("evidence", []):
        attachment = entry.get("attachment", {})
        values = {
            entry.get("evidence_id"),
            entry.get("test_case_id"),
            entry.get("finding_id"),
            attachment.get("external_tracking_id"),
        }
        if identifier in values:
            matches.append(entry)
    return matches
