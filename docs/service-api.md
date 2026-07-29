# Pool-account Service API

The service API is a small machine-to-machine control surface for pool
accounts already managed by codex-lb. It is separate from dashboard sessions
and client proxy API keys. The governing capability is the
[pool-account service API OpenSpec](https://github.com/aaiyer/codex-lb/tree/feat/service-account-api/openspec/specs/pool-account-service-api).

## Enable authentication

Set `CODEX_LB_SERVICE_ADMIN_TOKEN` through a secret manager or the process
environment. The value must be at least 32 characters. When it is unset, blank,
or too weak, the service routes are unavailable; there is no default token.

Do not commit this token, put it in a `.env.example` value, or include it in
logs, traces, screenshots, or support bundles. The imported `auth_json` file is
also sensitive credential material and must be handled as a secret.

For remote access, terminate TLS at codex-lb or at a trusted reverse proxy and
forward the `Authorization` header only to codex-lb. Do not expose the service
API over plaintext HTTP.

## Endpoints

All endpoints require:

```http
Authorization: Bearer <service-admin-token>
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/pool-accounts` | List safe account metadata |
| `GET` | `/api/v1/pool-accounts/{account_id}` | Inspect one account |
| `POST` | `/api/v1/pool-accounts/import` | Import one bounded `auth_json` file |
| `DELETE` | `/api/v1/pool-accounts/{account_id}` | Delete an account |

The list endpoint supports exact `email`, `status`, and `alias` filters,
`limit` from 1 through 200, and an opaque keyset `cursor`. The default limit
is 50. `updatedAt` and `lastSuccessAt` filters are deferred because the
current account model does not persist those timestamps.

Responses contain account ID, email, alias, status, paused state, plan type,
creation time, and last refresh time. They never contain access, refresh, ID,
or service-admin tokens.

## Examples

Use a shell variable supplied by your secret manager. These examples contain
no token value and do not create or store an authentication bundle:

```bash
export SERVICE_ADMIN_TOKEN='<inject-a-secret-of-at-least-32-characters>'

curl --fail-with-body \
  -H "Authorization: Bearer ${SERVICE_ADMIN_TOKEN}" \
  http://127.0.0.1:2455/api/v1/pool-accounts

curl --fail-with-body \
  -H "Authorization: Bearer ${SERVICE_ADMIN_TOKEN}" \
  'http://127.0.0.1:2455/api/v1/pool-accounts?status=active&limit=25'

curl --fail-with-body \
  -H "Authorization: Bearer ${SERVICE_ADMIN_TOKEN}" \
  -F 'auth_json=@/secure/path/provided-by-your-secret-workflow' \
  http://127.0.0.1:2455/api/v1/pool-accounts/import

curl --fail-with-body \
  -X DELETE \
  -H "Authorization: Bearer ${SERVICE_ADMIN_TOKEN}" \
  http://127.0.0.1:2455/api/v1/pool-accounts/<account-id>
```

Start the local backend with the documented development command:

```bash
uv run fastapi run app/main.py --reload --no-proxy-headers
```

The supported container also listens on port 2455. Pass the token through the
container runtime's secret mechanism and mount the persistent data directory;
see [Docker deployment](deployment/docker.md). Back up the database and
encryption key together before account mutations. A normal delete retains
historical request-log data in detached form. Add `?delete_history=true` only
when the permanent history purge has been explicitly approved.

## Errors

Errors use codex-lb's structured API envelope:

```json
{"error":{"code":"pool_account_not_found","message":"Pool account not found"}}
```

Authentication failures return `401`. Invalid cursors or auth bundles return
`400`; an oversized multipart body returns `413`; duplicate identities return
`409`; and unknown or already deleted accounts return `404`.

The import limit is one `auth_json` file, with a 1 MiB file/aggregate limit
and a 2 MiB multipart body limit. Password-based account creation and
workspace-member automation are not supported.

---

*Spec: [pool-account-service-api](https://github.com/aaiyer/codex-lb/tree/feat/service-account-api/openspec/specs/pool-account-service-api)*
