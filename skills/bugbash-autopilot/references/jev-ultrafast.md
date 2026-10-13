# Jev Ultrafast Adapter

[`browser-use/jev-ultrafast`](https://github.com/browser-use/jev-ultrafast)
is an optional fast browser-execution backend. It uses a dynamic indexed action
space over visible DOM and ARIA controls, selects an operation and compatible
target in one TypeSafe request, and uses a separate small model only when text
must be generated.

The dependency is MIT licensed and pinned to a reviewed commit in the optional
`jev` dependency group.

## Role in this skill

Jev may execute narrow, low-risk browser goals. Bug Bash Autopilot remains
responsible for:

- Test planning and dependency management.
- Safety and destructive-action approval.
- Independent outcome verification.
- Finding classification and controlled retries.
- Screenshot redaction and evidence manifests.
- Console, network, SQL, and task diagnostics.
- Intake-system upload and persistence verification.
- Fallback computer use.

Jev selecting `DONE` is never sufficient proof that a check passed.

## Best-fit tasks

Use Jev for:

- Opening a known page.
- Clicking common HTML or ARIA buttons.
- Filling ordinary text fields.
- Selecting native dropdown options.
- Scrolling a simple page.
- Repeating narrow navigation checks at high speed.

Prefer browser computer use or Playwright for:

- File uploads.
- Iframes or shadow DOM.
- Canvas-based controls.
- Pop-up or newly opened tabs.
- Nested scrolling regions.
- Complex keyboard widgets.
- Media playback and audio verification.
- Visual layout, screenshot comparison, or accessibility inspection.
- Console and network debugging.
- Intake forms whose attachment flow must be verified.

If Jev returns `BLOCKED`, reaches its action budget, or cannot observe a
required control, preserve its trace and continue the same check with computer
use. Do not repeatedly rerun the same blocked goal.

## Installation

Jev requires Python 3.12 or later:

```shell
python -m pip install -e ".[jev]"
```

It connects to Chrome through Browser Harness. Complete its browser preflight:

```shell
browser-harness --doctor
```

Allow Chrome remote debugging only through the approved prompt and profile.
Jev creates and owns a background tab; it does not need to take over the
visible tab.

The Browser Harness Chrome profile may differ from the browser profile used by
computer-use or Playwright tools. Authenticate interactively in the Jev-owned
profile when needed. Never place credentials in a Jev goal or text field
fixture.

## Credentials and data egress

Supply credentials through environment variables:

```text
TYPESAFE_API_KEY=
TYPESAFE_MODEL=jev-latest
TEXT_MODEL_API_KEY=
TEXT_MODEL_BASE_URL=https://openrouter.ai/api/v1
TEXT_MODEL=inception/mercury-2.5
TEXT_MODEL_REASONING=none
```

Never write these values into the run, report, trace, screenshot, or repository.

Jev sends structured visible-page state to the configured TypeSafe service.
For text fields it also sends field context to the configured text-model
provider. Do not use Jev on pages whose content is not approved for those
providers. Use local computer interaction instead when data-egress policy is
unclear.

## Run a goal

```shell
bugbash-autopilot jev-run \
  --run-dir runs/my-app \
  --case-id SEARCH-001 \
  --url https://example.test/search \
  --goal "Search for Contoso and stop when matching results are visible." \
  --expected-url-regex "/search" \
  --expected-text "Contoso"
```

Use `--expected-url-regex` and one or more `--expected-text` arguments as
deterministic completion predicates. If no predicate is supplied, the result is
marked `requires_manual` even when Jev selects `DONE`.

For a goal that cannot type, `--click-only` allows execution without
`TEXT_MODEL_API_KEY`.

## Evidence and traces

The adapter:

1. Enables Jev recording.
2. Stores raw frames under
   `adapters/jev/<check-id>/attempt-NNN/frames`.
3. Stores a sanitized trace that excludes typed values, model usage payloads,
   visible page text, and the raw goal.
4. Hashes the goal so the executed input can still be correlated.
5. Adds the adapter outcome and trace path to the test case's attempt history.
6. Registers the final frame through the normal evidence pipeline.
7. Preserves the original JPEG and creates the processed PNG.

Action labels and URLs remain in the sanitized trace and may still be private.
Keep real run directories outside public source control.

Use the normal `--redact` and `--highlight` rectangle options when running the
adapter. Review the processed evidence before external upload.

## Failure handling

- `DONE` without predicates: manual verification required.
- Predicate failure: mark the execution as unverified and inspect with computer
  use.
- `BLOCKED`: preserve the trace and switch backend.
- Stale-page retry inside Jev: retain the executed history and final state.
- Missing credentials or package: treat as an adapter availability issue, not a
  product defect.
- Upload, popup, iframe, shadow DOM, or canvas requirement: route directly to
  computer use.
