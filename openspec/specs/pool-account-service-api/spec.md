# Pool-account service API

## Requirements

### Requirement: Service-admin authentication is isolated and fail closed
The service API MUST use an authentication dependency distinct from dashboard
session authentication and client proxy-key authentication. It MUST read
`CODEX_LB_SERVICE_ADMIN_TOKEN`, reject an unset or blank value by leaving the
API unavailable, reject configured values shorter than 32 characters, and
compare a presented Bearer credential in constant time. Service credentials
and authorization headers MUST NOT be emitted in responses, audit details, or
application logs.

### Requirement: Pool-account lifecycle endpoints are credential-free
The service API MUST expose `GET /api/v1/pool-accounts`,
`GET /api/v1/pool-accounts/{account_id}`,
`POST /api/v1/pool-accounts/import`, and
`DELETE /api/v1/pool-accounts/{account_id}`. List and detail responses MUST
contain only safe account metadata: account ID, email, alias, status, paused
state, plan type, creation time, and last refresh time. Import MUST be a
bounded multipart upload with a required `auth_json` file and MUST reuse the
existing auth parser, encrypted persistence, conflict handling, and safe
response. Delete MUST reuse existing deletion semantics, retain historical
request-log rows by default, and require explicit `delete_history=true` to
purge those rows.

### Requirement: Collection queries are bounded and repository-backed
The collection endpoint MUST support exact email, status, and alias filters,
limit values from 1 through 200, and an opaque keyset cursor. Filters MUST be
applied in the repository query before limiting results. Unsupported metadata
such as `updatedAt` and `lastSuccessAt` remains deferred because the current
model does not persist it.

### Requirement: Service operations report stable errors and safe audit events
Missing or invalid service authentication MUST return structured HTTP 401
responses. Invalid uploads and cursors MUST return structured HTTP 400,
oversized uploads HTTP 413, identity conflicts HTTP 409, and unknown or
repeated account IDs HTTP 404. Successful imports and deletes MUST emit audit
events containing safe metadata only. Existing dashboard and client proxy
authentication and response contracts MUST remain unchanged.
