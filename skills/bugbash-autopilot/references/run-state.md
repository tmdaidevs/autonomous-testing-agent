# Run State

## Files

Each run has:

- `results.json`: run context, cases, findings, attempts, and submissions.
- `evidence/manifest.json`: original and processed evidence metadata.
- `Bug-Bash-Report.md`: generated human-readable report.

## Test case

```json
{
  "id": "B2-UX-1",
  "title": "Insights render",
  "status": "issue",
  "expected": "A chart and chart selector appear.",
  "actual": "The page remains on a spinner.",
  "finding_ids": ["BUG-004"],
  "evidence_ids": ["EVD-002"],
  "dependencies": ["B1-SQL-2"],
  "attempts": [
    {
      "started_at": "2026-10-13T08:00:00Z",
      "completed_at": "2026-10-13T08:03:00Z",
      "outcome": "issue",
      "notes": "Still spinning after a serial reload."
    }
  ]
}
```

## Finding

```json
{
  "id": "BUG-004",
  "title": "Insights never finishes loading",
  "severity": "high",
  "area": "Content browsing",
  "test_case_ids": ["B2-UX-1"],
  "steps": [
    "Open the table.",
    "Select Insights.",
    "Wait for the documented processing interval."
  ],
  "expected": "A chart and chart selector appear.",
  "actual": "The spinner remains indefinitely.",
  "impact": "Users cannot inspect generated insights.",
  "recommendation": "Bound loading and expose processing or error state.",
  "evidence_ids": ["EVD-002"],
  "external_tracking_ids": ["BB-12345678"]
}
```

## Evidence exception

When capture is impossible, use a non-empty explanation:

```json
{
  "evidence_ids": [],
  "evidence_exception": "The browser process terminated before a screenshot could be captured."
}
```

An exception documents missing evidence; it does not make the result as strong
as a captured artifact.
