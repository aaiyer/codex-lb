## Why

Replacing a pool account while clients are routing can admit work against the
old pool or return a transient no-account error. The supported SQLite topology
has one application process, so it can hold new work locally during this short
maintenance window without adding database coordination.

## What Changes

- Add service-admin-authenticated pause, resume, and status endpoints.
- Hold new proxy HTTP requests without sending response bytes while paused.
- Hold new Responses turns received on already-connected WebSockets without
  forwarding them or emitting an error.
- Let already-admitted work finish, then route released waiters against the
  current account pool.
- Keep the pause state process-local and reset it on process start.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pool-account-service-api`: expose authenticated routing-maintenance controls.
- `proxy-admission-control`: define waiting and admission behavior while routing is paused.
