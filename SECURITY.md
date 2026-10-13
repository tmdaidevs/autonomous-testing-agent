# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities privately through GitHub's security
advisory interface rather than opening a public issue.

## Evidence handling

Test evidence can contain authentication state, personal information, internal
URLs, access tokens, request headers, customer content, and unpublished product
details. Before sharing evidence:

1. Capture only the minimum area needed to prove the behavior.
2. Review the browser chrome, address bar, console, and network details.
3. Redact credentials, tokens, email addresses, and unrelated personal data.
4. Keep the unmodified original in restricted storage.
5. Publish only the processed copy.
6. Verify that the processed copy no longer exposes the sensitive value.

The helper tools reduce accidental disclosure but do not replace human review.

## External browser-model providers

The optional Jev Ultrafast adapter sends structured visible-page state to the
configured TypeSafe service. When text entry is needed, field context is also
sent to the configured text-model provider. Do not enable this adapter for
pages whose content is not approved for those providers. API keys must be
supplied through environment variables and must never be written to run
artifacts.
