# Implementation tasks

## OpenSpec and configuration

- [x] Record the capability, non-goals, and deferred fields.
- [x] Add explicit service-admin token configuration with fail-closed
      validation.
- [x] Add an isolated constant-time Bearer dependency.

## API and domain integration

- [x] Add credential-free pool-account response schemas.
- [x] Add SQL-backed filters and bounded cursor pagination.
- [x] Add list and detail endpoints.
- [x] Add bounded multipart import endpoint using the existing auth bundle
      parser and account service.
- [x] Add deletion endpoint with explicit historical-log purge semantics.
- [x] Add safe import/delete audit events.
- [x] Keep dashboard and proxy authentication and routes unchanged.

## Verification and documentation

- [x] Add focused authentication, contract, lifecycle, pagination, audit, and
      redaction tests using synthetic credentials only.
- [x] Verify generated OpenAPI and settings documentation.
- [x] Document configuration, TLS, endpoint examples, errors, and retention.
- [x] Run focused tests and the relevant upstream regression suite.
- [x] Run lint/type/docs/OpenSpec checks that are available in the checkout.

OpenSpec CLI validation was attempted with `openspec`, `uv run openspec`, and
`uvx openspec`; no executable or package is available in this checkout. Ruff,
`ty`, generated settings verification, OpenAPI checks, and the strict MkDocs
build all pass. The full unit suite reports two unrelated metrics-test failures
because its import-hook simulation does not make `prometheus_client` absent in
this environment; the relevant account/dashboard/proxy regression slices pass.
