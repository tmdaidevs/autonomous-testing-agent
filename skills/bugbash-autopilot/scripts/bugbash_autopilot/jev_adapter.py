from __future__ import annotations

import hashlib
import importlib.metadata
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from .evidence import EvidenceError, add_evidence
from .io_utils import (
    read_json,
    relative_posix,
    safe_component,
    utc_now,
    write_json,
)


class JevUnavailable(EvidenceError):
    """Raised when the optional Jev execution backend is not ready."""


AgentFactory = Callable[..., Any]
TRACE_HISTORY_FIELDS = (
    "step",
    "action",
    "kind",
    "choice",
    "confidence",
    "latency_ms",
    "operation",
    "target",
    "page_changed",
    "url",
    "executed_ms",
    "elapsed_ms",
)


def _load_jev_agent(
    text_model_required: bool,
) -> AgentFactory:
    if sys.version_info < (3, 12):
        raise JevUnavailable(
            "jev-ultrafast requires Python 3.12 or later. "
            "The core bug-bash tooling can still run on Python 3.10 and 3.11."
        )

    missing = [
        name
        for name in ("TYPESAFE_API_KEY",)
        if not os.environ.get(name)
    ]
    if text_model_required and not os.environ.get("TEXT_MODEL_API_KEY"):
        missing.append("TEXT_MODEL_API_KEY")
    if missing:
        raise JevUnavailable(
            "Missing required Jev environment variables: "
            + ", ".join(missing)
            + ". Values must be supplied through the environment and are never "
            "written to run artifacts."
        )

    try:
        from jev_ultrafast import Agent
    except ImportError as error:
        raise JevUnavailable(
            "jev-ultrafast is not installed. Install the optional integration "
            "with: python -m pip install -e '.[jev]'"
        ) from error
    return Agent


def _next_attempt_directory(run_dir: Path, test_case_id: str) -> Path:
    base = (
        run_dir
        / "adapters"
        / "jev"
        / safe_component(test_case_id, "CHECK")
    )
    base.mkdir(parents=True, exist_ok=True)
    numbers: list[int] = []
    for child in base.glob("attempt-*"):
        if child.is_dir():
            try:
                numbers.append(int(child.name.split("-", 1)[1]))
            except (IndexError, ValueError):
                continue
    attempt = base / f"attempt-{max(numbers, default=0) + 1:03d}"
    attempt.mkdir(parents=True, exist_ok=False)
    return attempt


def _require_test_case(run_dir: Path, test_case_id: str) -> None:
    results = read_json(run_dir / "results.json")
    cases = results.get("test_cases")
    if not isinstance(cases, list) or not any(
        isinstance(item, dict) and item.get("id") == test_case_id
        for item in cases
    ):
        raise EvidenceError(
            f"Unknown test case {test_case_id!r}. Add it to results.json "
            "before browser execution."
        )


def _sanitized_history(history: object) -> list[dict[str, Any]]:
    if not isinstance(history, list):
        return []
    sanitized: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        record = {
            key: item[key]
            for key in TRACE_HISTORY_FIELDS
            if key in item
        }
        record["typed_text"] = bool(item.get("text"))
        sanitized.append(record)
    return sanitized


def _compile_url_pattern(pattern: str | None) -> re.Pattern[str] | None:
    if pattern is None:
        return None
    try:
        return re.compile(pattern)
    except re.error as error:
        raise ValueError(
            f"Invalid --expected-url-regex value {pattern!r}: {error}"
        ) from error


def _verification_result(
    state: dict[str, Any],
    expected_url_pattern: re.Pattern[str] | None,
    expected_text: Iterable[str],
) -> dict[str, Any]:
    status = str(state.get("status", "unknown"))
    page = state.get("page")
    if not isinstance(page, dict):
        page = {}
    final_url = str(page.get("url") or "")
    visible_text = str(page.get("text") or "")
    checks: list[dict[str, Any]] = []

    if expected_url_pattern is not None:
        checks.append(
            {
                "kind": "url_regex",
                "expected": expected_url_pattern.pattern,
                "passed": bool(expected_url_pattern.search(final_url)),
            }
        )
    for expected in expected_text:
        checks.append(
            {
                "kind": "visible_text",
                "expected": expected,
                "passed": expected.casefold() in visible_text.casefold(),
            }
        )

    has_predicates = bool(checks)
    verified = (
        status == "done"
        and has_predicates
        and all(check["passed"] for check in checks)
    )
    return {
        "verified": verified,
        "requires_manual": status == "done" and not has_predicates,
        "agent_status": status,
        "checks": checks,
    }


def _jev_version() -> str | None:
    try:
        return importlib.metadata.version("jev-ultrafast")
    except importlib.metadata.PackageNotFoundError:
        return None


def run_jev_goal(
    run_dir: Path,
    test_case_id: str,
    url: str,
    goal: str,
    *,
    finding_id: str | None = None,
    description: str | None = None,
    expected_url_regex: str | None = None,
    expected_text: Iterable[str] = (),
    redactions: Iterable[tuple[int, int, int, int]] = (),
    highlights: Iterable[tuple[int, int, int, int]] = (),
    register_evidence: bool = True,
    text_model_required: bool = True,
    agent_factory: AgentFactory | None = None,
) -> dict[str, Any]:
    if not test_case_id.strip():
        raise ValueError("test_case_id is required")
    if not url.strip():
        raise ValueError("url is required")
    if not goal.strip():
        raise ValueError("goal is required")
    if not (run_dir / "results.json").is_file():
        raise EvidenceError(
            f"No bug-bash run found at {run_dir}. Run init first."
        )
    _require_test_case(run_dir, test_case_id)

    expected_text_values = [
        value.strip() for value in expected_text if value.strip()
    ]
    expected_url_pattern = _compile_url_pattern(expected_url_regex)
    factory = agent_factory or _load_jev_agent(text_model_required)
    attempt_dir = _next_attempt_directory(run_dir, test_case_id)
    frames_dir = attempt_dir / "frames"
    started_at = utc_now()

    last_state: dict[str, Any] | None = None
    with factory(
        url,
        goal,
        record_dir=frames_dir,
        screenshots=True,
    ) as agent:
        initial_state = agent.snapshot()
        if isinstance(initial_state, dict):
            last_state = initial_state
        for state in agent.run():
            if isinstance(state, dict):
                last_state = state

    if last_state is None:
        raise EvidenceError("Jev returned no observable state")

    frame_paths = sorted(frames_dir.glob("*.jpg"))
    if not frame_paths:
        raise EvidenceError(
            "Jev did not produce screenshot frames. Evidence registration "
            "cannot continue."
        )

    verification = _verification_result(
        last_state,
        expected_url_pattern,
        expected_text_values,
    )
    page = last_state.get("page")
    if not isinstance(page, dict):
        page = {}
    final_url = str(page.get("url") or "")
    history = _sanitized_history(last_state.get("history"))
    goal_hash = hashlib.sha256(goal.encode("utf-8")).hexdigest()
    trace: dict[str, Any] = {
        "schema_version": 1,
        "adapter": "jev-ultrafast",
        "adapter_version": _jev_version(),
        "test_case_id": test_case_id,
        "finding_id": finding_id,
        "started_url": url,
        "final_url": final_url,
        "goal_sha256": goal_hash,
        "status": last_state.get("status"),
        "elapsed_ms": last_state.get("elapsed_ms"),
        "action_count": len(history),
        "history": history,
        "verification": verification,
        "frame_count": len(frame_paths),
        "started_at": started_at,
        "completed_at": utc_now(),
        "models": {
            "typesafe": os.environ.get("TYPESAFE_MODEL", "jev-latest"),
            "text": os.environ.get("TEXT_MODEL"),
        },
        "evidence_id": None,
    }

    failed_checks = [
        check["expected"]
        for check in verification["checks"]
        if not check["passed"]
    ]
    if verification["verified"]:
        actual = (
            f"Jev reached {final_url or 'the final page'} and all deterministic "
            "completion checks passed."
        )
    elif verification["requires_manual"]:
        actual = (
            f"Jev selected DONE at {final_url or 'the final page'}, but no "
            "independent completion predicate was supplied."
        )
    elif failed_checks:
        actual = (
            f"Jev stopped with status {verification['agent_status']}; failed "
            "completion checks: "
            + ", ".join(failed_checks)
        )
    else:
        actual = (
            f"Jev stopped with status {verification['agent_status']} at "
            f"{final_url or 'an unknown URL'}."
        )

    evidence_entry: dict[str, Any] | None = None
    if register_evidence:
        expected_parts: list[str] = []
        if expected_url_pattern is not None:
            expected_parts.append(
                f"URL matches {expected_url_pattern.pattern!r}"
            )
        expected_parts.extend(
            f"Visible text contains {value!r}"
            for value in expected_text_values
        )
        expected = (
            "; ".join(expected_parts)
            if expected_parts
            else "The final state must be independently verified."
        )
        evidence_entry = add_evidence(
            run_dir=run_dir,
            source=frame_paths[-1],
            test_case_id=test_case_id,
            finding_id=finding_id,
            description=description
            or f"Jev final browser state for {test_case_id}",
            page_url=final_url or url,
            action=(
                f"Executed a Jev goal with {len(history)} recorded browser "
                "actions"
            ),
            expected=expected,
            actual=actual,
            redactions=redactions,
            highlights=highlights,
        )
        trace["evidence_id"] = evidence_entry["evidence_id"]

    trace_path = attempt_dir / "trace.json"
    write_json(trace_path, trace)
    trace_relative_path = relative_posix(trace_path, run_dir)

    if verification["verified"]:
        outcome = "works"
    elif verification["requires_manual"]:
        outcome = "needs_verification"
    elif verification["agent_status"] == "blocked":
        outcome = "blocked"
    else:
        outcome = "unverified"
    results_path = run_dir / "results.json"
    results = read_json(results_path)
    test_case = next(
        item
        for item in results["test_cases"]
        if item.get("id") == test_case_id
    )
    attempts = test_case.setdefault("attempts", [])
    attempts.append(
        {
            "adapter": "jev-ultrafast",
            "started_at": started_at,
            "completed_at": trace["completed_at"],
            "outcome": outcome,
            "notes": actual,
            "trace_path": trace_relative_path,
            "verification": verification,
        }
    )
    write_json(results_path, results)

    return {
        "adapter": "jev-ultrafast",
        "test_case_id": test_case_id,
        "status": last_state.get("status"),
        "elapsed_ms": last_state.get("elapsed_ms"),
        "action_count": len(history),
        "final_url": final_url,
        "verification": verification,
        "trace_path": trace_relative_path,
        "frame_count": len(frame_paths),
        "final_frame_path": relative_posix(frame_paths[-1], run_dir),
        "evidence_id": (
            evidence_entry["evidence_id"] if evidence_entry else None
        ),
    }
