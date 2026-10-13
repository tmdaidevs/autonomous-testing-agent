# Classification and Retries

## Result statuses

| Status | Meaning |
|---|---|
| `works` | Observed behavior matches the requirement. |
| `works_with_issue` | The primary behavior works but a secondary defect exists. |
| `issue` | The requirement is violated or completion is blocked by a product defect. |
| `blocked` | An external prerequisite prevents a valid result. |
| `not_tested` | The check has not been attempted. |
| `skipped` | The check was intentionally omitted with a recorded reason. |

## Finding categories

- Functional correctness.
- Reliability and data completeness.
- Usability and discoverability.
- Accessibility and keyboard interaction.
- Diagnostics and supportability.
- Performance and responsiveness.
- Safety and destructive-action protection.
- Documentation or checklist gap.
- Testability or environment constraint.

## Severity

| Severity | Guidance |
|---|---|
| Critical | Data loss, security boundary failure, or system-wide outage with no safe workaround. |
| High | Core workflow fails, data is materially incomplete or wrong, or the application crashes. |
| Medium | Important secondary workflow fails or UX creates substantial confusion or rework. |
| Low | Minor visual, wording, or convenience issue with limited impact. |

## Controlled retries

### Concurrency conflict

Wait for the conflicting operation, then rerun once serially. If serial
execution succeeds, record a concurrency or testability constraint. If the UI
allowed an unsafe collision without guidance, report the UX defect separately.

### Throttling or provider error

Retry serially with bounded backoff. Inspect row-level and nested values because
an outer task may still say `Completed`.

### Delayed processing

Poll documented task or object state. When no documented timeout exists, choose
a bounded interval, record it, and stop rather than waiting indefinitely.

### Browser state

Verify the selected account, workspace, database, and active conversation
before repeating. Clear stale editor or form state explicitly.

### Intermittent UI failure

Capture the first failure before retrying. Record both attempts and whether a
reload, new session, or reauthentication was required.

## Do not retry blindly

Do not repeatedly submit forms, rerun destructive commands, create duplicate
resources, or generate duplicate bug records. Verify persisted state before
another attempt.
