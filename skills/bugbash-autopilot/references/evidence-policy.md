# Evidence Policy

## Capture requirements

- Capture every confirmed UI issue.
- Capture representative successful states when they prove a high-risk
  requirement or establish a before/after comparison.
- Capture the smallest useful area while retaining product and object context.
- Capture before navigating away, dismissing a dialog, or retrying.
- Pair screenshots with text for audio, video, timing, and intermittent issues.

## Naming

Use deterministic names:

```text
NNN-<check-id>-<short-description>.png
```

The helper assigns the numeric prefix and stores originals and processed copies
under separate directories.

## Metadata

Each evidence entry records:

- Evidence ID.
- Check ID and optional finding ID.
- Capture timestamp.
- Page URL.
- Action just performed.
- Expected and actual behavior.
- Description of what the image proves.
- Original and processed paths.
- SHA-256 hashes, dimensions, and file size.
- Attachment status and failure reason.
- External tracking ID.
- Related console, network, SQL, and task artifacts.

## Annotation

Use a thin high-contrast rectangle around the defective region. Do not obscure
the surrounding context. Avoid arrows or labels that cover product text.

Always preserve the original. An annotation is a derived copy.

## Redaction

Redact:

- Passwords, tokens, cookies, authorization headers, and connection strings.
- Email addresses and personal identifiers not required for the finding.
- Internal URLs or tenant identifiers when evidence will leave the approved
  boundary.
- Customer, financial, health, or other regulated data.
- Unrelated browser tabs, notifications, and desktop content.

Review the processed image at full resolution. Pixelation alone may be
reversible; the helper uses opaque filled rectangles.

## Compression

Respect the intake system's byte limit. The helper first optimizes PNG output,
then resizes and color-quantizes when necessary. If the limit cannot be reached
without making the evidence unreadable, keep the local file and record the
attachment as blocked.

## Upload verification

An evidence item may have one of these states:

- `not_attempted`
- `uploaded`
- `blocked`
- `not_supported`
- `rejected`

Only use `uploaded` after reopening the persisted intake record and verifying
its attachment indicator or downloadable file.

## Failure fallback

If upload fails:

1. Preserve the processed local image.
2. Record the exact error message.
3. Reauthenticate only through the approved login flow.
4. Retry once when the failure indicates expired authentication.
5. Submit text without an attachment only when policy permits it.
6. Include the local evidence path in the submission log.
7. Never state that the image was attached.

## Public repositories

Commit only synthetic or explicitly reviewed and redacted images. Real
application evidence belongs in restricted storage by default.
