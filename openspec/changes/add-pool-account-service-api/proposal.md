# Add pool-account service API

## Why

Operators need a narrowly scoped, machine-to-machine API for managing the
codex-lb pool accounts that are already persisted by the accounts module.
Dashboard sessions and client proxy keys are deliberately unsuitable for this
purpose because they have different trust boundaries and lifecycles.

## What changes

- Add a service-admin Bearer-authenticated API for listing, inspecting,
  importing, and deleting pool accounts.
- Reuse the existing account repository, import parser, encryption, deletion
  semantics, audit service, and multipart limits.
- Add SQL-backed email, status, and alias filters with bounded limit/cursor
  pagination.
- Keep responses credential-free and record only safe metadata in audit events.
- Document configuration, TLS deployment, endpoint behavior, and the
  intentionally deferred metadata filters.

## Non-goals

- Browser, Playwright, ChatGPT Business workspace-member, or CAPTCHA/MFA
  automation.
- Exporting, displaying, or logging access, refresh, ID, or service-admin
  tokens.
- Replacing dashboard authentication or client proxy-key authentication.
- Changing the existing dashboard account routes or adding a database
  migration.

## Compatibility and rollout

The API is closed when `CODEX_LB_SERVICE_ADMIN_TOKEN` is unset. When set, it
must be at least 32 characters. Existing dashboard and proxy routes retain
their current dependencies and response contracts. The endpoint is intended
to be placed behind TLS and an operator-controlled network boundary.
