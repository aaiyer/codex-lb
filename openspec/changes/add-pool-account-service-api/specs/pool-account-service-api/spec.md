# Pool-account service API

## ADDED Requirements

### Requirement: Service-admin authentication is isolated and fail closed
The service API MUST use an authentication dependency distinct from dashboard
session authentication and client proxy-key authentication. The dependency
MUST read `CODEX_LB_SERVICE_ADMIN_TOKEN`, reject an unset or blank value by
leaving the API unavailable, reject configured values shorter than 32
characters, and compare a presented Bearer credential in constant time.

#### Scenario: Missing service configuration
- **WHEN** a request reaches a service API route while the service token is
  unset
- **THEN** the API returns HTTP 401 with a structured service-authentication
  error

#### Scenario: Missing or invalid credential
- **WHEN** a request omits the Bearer credential or presents a non-matching
  credential
- **THEN** the API returns HTTP 401 with the same structured error family

#### Scenario: Service credential is processed safely
- **WHEN** a service request is authenticated or rejected
- **THEN** neither the presented token nor an authorization header is emitted
  in a response, audit detail, or application log

### Requirement: Pool-account list and detail responses are credential-free
The service API MUST expose `GET /api/v1/pool-accounts` and
`GET /api/v1/pool-accounts/{account_id}`. Responses MUST contain only safe
account metadata: account ID, email, alias, status, paused state, plan type,
creation time, and last refresh time. Responses MUST NOT contain access,
refresh, ID, or other credential material.

#### Scenario: List pool accounts
- **WHEN** an authenticated client requests the collection
- **THEN** the response is HTTP 200 with an `accounts` array and an opaque
  nullable `nextCursor`

#### Scenario: Inspect an existing pool account
- **WHEN** an authenticated client requests an existing account ID
- **THEN** the response is HTTP 200 with the same credential-free metadata

#### Scenario: Inspect an unknown pool account
- **WHEN** an authenticated client requests an unknown account ID
- **THEN** the response is HTTP 404 with a structured not-found error

### Requirement: Collection filtering and pagination are bounded
The collection endpoint MUST support exact `email`, `status`, and `alias`
filters and a bounded `limit` from 1 through 200. Filtering MUST happen in
the repository query before the limit is applied. The endpoint MUST support an
opaque cursor for keyset pagination and MUST return a structured HTTP 400 for
an invalid cursor. Other filters, including `updatedAt` and `lastSuccessAt`,
are deferred until the model stores those fields or a later capability adds
them.

#### Scenario: Filter and page a collection
- **WHEN** an authenticated client supplies supported filters and a valid
  limit/cursor
- **THEN** only matching rows from the bounded repository query are returned
  with a cursor when more rows remain

#### Scenario: Unsupported metadata is not implied
- **WHEN** a client asks for a filter that is not in the documented contract
- **THEN** the API does not silently perform inefficient application-memory
  filtering or claim support for the deferred metadata

### Requirement: Auth-bundle import is bounded and reuses account services
The service API MUST expose `POST /api/v1/pool-accounts/import` as a bounded
multipart upload with a required `auth_json` file. It MUST reuse the existing
auth-bundle parser, encrypted account persistence, identity conflict handling,
and safe import response. Invalid bundles or malformed uploads MUST return a
structured 400, an identity conflict MUST return 409, and an oversized upload
MUST be rejected by the existing 413 multipart limit. The raw bundle and its
credentials MUST NOT be returned or logged.

#### Scenario: Import a valid synthetic bundle
- **WHEN** an authenticated client uploads one valid `auth_json` file within
  the configured multipart bounds
- **THEN** the account is persisted through the existing account service and a
  credential-free 200 response is returned

#### Scenario: Reject invalid or oversized import
- **WHEN** an authenticated client uploads malformed data, omits `auth_json`,
  or exceeds the multipart limit
- **THEN** the request fails with structured 400 or 413 behavior and no
  credential material is emitted

### Requirement: Deletion preserves history by default and audits safe metadata
The service API MUST expose
`DELETE /api/v1/pool-accounts/{account_id}`. A normal deletion MUST reuse the
existing account deletion service and retain historical request-log rows with
their account reference detached. `delete_history=true` MUST be an explicit
opt-in that purges historical request-log data. Unknown and repeated deletes
MUST return structured HTTP 404 responses. Successful imports and deletes MUST
emit audit events containing safe metadata only.

#### Scenario: Delete while retaining history
- **WHEN** an authenticated client deletes an existing account without
  `delete_history=true`
- **THEN** the account is removed, historical request-log rows remain
  detached, and a safe deletion audit event is emitted

#### Scenario: Explicitly purge history
- **WHEN** an authenticated client deletes an existing account with
  `delete_history=true`
- **THEN** the account and its historical request-log rows are removed and a
  safe deletion audit event records the explicit choice

#### Scenario: Repeated deletion
- **WHEN** an authenticated client deletes an account that no longer exists
- **THEN** the API returns HTTP 404 without creating a misleading success audit
  event

### Requirement: Existing boundaries remain compatible
Adding the service API MUST NOT change the dashboard account routes, dashboard
session authentication, client proxy-key authentication, or their response
contracts.

#### Scenario: Existing dashboard and proxy checks
- **WHEN** the existing dashboard and proxy regression tests run after the
  service API is enabled
- **THEN** they continue to pass with their existing authentication behavior
