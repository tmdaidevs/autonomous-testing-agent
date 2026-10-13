from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from bugbash_autopilot.evidence import initialize_run
from bugbash_autopilot.io_utils import read_json, write_json
from bugbash_autopilot.jev_adapter import (
    JevUnavailable,
    _load_jev_agent,
    run_jev_goal,
)
from bugbash_autopilot.validation import validate_run


class FakeJevAgent:
    def __init__(
        self,
        url: str,
        goal: str,
        *,
        record_dir: Path,
        screenshots: bool,
    ) -> None:
        assert screenshots is True
        self.url = url
        self.goal = goal
        self.record_dir = Path(record_dir)
        self.record_dir.mkdir(parents=True)
        Image.new("RGB", (640, 480), "white").save(
            self.record_dir / "000000.jpg"
        )
        self._initial = {
            "status": "ready",
            "elapsed_ms": 0,
            "history": [],
            "page": {
                "url": url,
                "text": "Loading",
            },
        }

    def snapshot(self) -> dict:
        return self._initial

    def run(self):
        Image.new("RGB", (640, 480), "#e9eef8").save(
            self.record_dir / "000125.jpg"
        )
        yield {
            "status": "done",
            "elapsed_ms": 125,
            "history": [
                {
                    "step": 1,
                    "action": "Search",
                    "kind": "fill",
                    "choice": "TYPE_TEXT:3",
                    "confidence": 0.92,
                    "latency_ms": 50,
                    "operation": "TYPE_TEXT",
                    "target": "Search field",
                    "page_changed": True,
                    "url": "https://example.test/results",
                    "executed_ms": 80,
                    "elapsed_ms": 125,
                    "text": "private typed value",
                    "usage": {"input_tokens": 999},
                }
            ],
            "page": {
                "url": "https://example.test/results",
                "text": "Search complete. 3 matching records.",
            },
        }

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


def _run_with_case(run_dir: Path) -> None:
    initialize_run(run_dir, "jev-run", "Jev integration run")
    results_path = run_dir / "results.json"
    results = read_json(results_path)
    results["test_cases"] = [
        {
            "id": "NAV-001",
            "title": "Open search results",
            "status": "works",
            "expected": "The results page is visible.",
            "actual": "The results page is visible.",
            "dependencies": [],
            "finding_ids": [],
            "evidence_ids": [],
            "attempts": [],
        }
    ]
    write_json(results_path, results)


def test_jev_adapter_verifies_and_registers_sanitized_evidence(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    _run_with_case(run_dir)

    result = run_jev_goal(
        run_dir=run_dir,
        test_case_id="NAV-001",
        url="https://example.test",
        goal="Search for matching records.",
        expected_url_regex=r"/results$",
        expected_text=["3 matching records"],
        agent_factory=FakeJevAgent,
    )

    assert result["verification"]["verified"] is True
    assert result["evidence_id"] == "EVD-001"
    trace_path = run_dir / result["trace_path"]
    serialized_trace = trace_path.read_text(encoding="utf-8")
    assert "private typed value" not in serialized_trace
    assert "input_tokens" not in serialized_trace
    trace = json.loads(serialized_trace)
    assert trace["history"][0]["typed_text"] is True
    assert trace["goal_sha256"]
    results = read_json(run_dir / "results.json")
    assert results["test_cases"][0]["attempts"][0]["adapter"] == "jev-ultrafast"
    assert results["test_cases"][0]["attempts"][0]["outcome"] == "works"
    assert validate_run(run_dir).valid


def test_jev_done_requires_independent_predicate(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _run_with_case(run_dir)

    result = run_jev_goal(
        run_dir=run_dir,
        test_case_id="NAV-001",
        url="https://example.test",
        goal="Open the results page.",
        register_evidence=False,
        agent_factory=FakeJevAgent,
    )

    assert result["verification"] == {
        "verified": False,
        "requires_manual": True,
        "agent_status": "done",
        "checks": [],
    }


def test_jev_preflight_does_not_print_or_store_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("TEXT_MODEL_API_KEY", raising=False)

    with pytest.raises(JevUnavailable, match="TYPESAFE_API_KEY"):
        _load_jev_agent(text_model_required=True)
