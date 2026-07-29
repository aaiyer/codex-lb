# Context

## Existing boundaries

The accounts module already owns account import, encrypted credential
storage, usage refresh, request-log retention, and account deletion. The new
router is therefore a thin service boundary over `AccountsService`; it does
not duplicate persistence or credential handling.

The dashboard uses session authentication and the client proxy uses API-key
authentication. The service API has a separate dependency and a separate
configuration value so a credential from one boundary cannot authorize the
other.

## Contract decisions

- The service token is optional at deployment time but the API is unavailable
  unless it is configured with a non-blank value at least 32 characters long.
- Token comparison is performed on fixed-length SHA-256 digests using the
  standard-library constant-time comparison primitive. The helper is kept
  isolated so a future token store can add hashes, scopes, and rotation
  without coupling those concerns to the routes.
- List filters are exact email, status, and alias predicates. They are
  applied in SQL before the bounded query limit. Account IDs are the stable
  keyset cursor; the cursor is opaque at the HTTP boundary.
- `updatedAt` and `lastSuccessAt` are deferred because the current Account
  model does not persist those fields. The API exposes the existing
  `createdAt` and `lastRefreshAt` metadata instead.
- A normal delete retains request-log rows as historical records with their
  account reference detached. `delete_history=true` is the explicit,
  destructive opt-in for purging those rows.

## Sensitive-data rules

The imported auth bundle and all credential fields remain write-only. They
must not appear in response models, audit details, request logs, fixtures, or
documentation examples. Test data uses synthetic JWT-like values only.
