## Why

The default file-backed SQLite path opens a new connection for every session through `NullPool`, creates a second engine for background work, and executes `journal_mode=WAL` on every connection. Under concurrent proxy and scheduler traffic this creates avoidable connection churn and lock setup. Separately, durable bridge transcripts and conversation identifiers are recorded by default even when an operator does not use those history features.

## What Changes

- Use SQLAlchemy's native bounded async pool for file-backed SQLite: four connections, no overflow.
- Reuse the main SQLite engine for production background sessions and set WAL only on the engine's first connection.
- Default the HTTP bridge durable operation ledger and conversation identifier analytics off; both remain available by explicit configuration.
- Default request-log retention to 30 days and usage-history retention to 45 days while preserving explicit `0` overrides.
- Leave PostgreSQL behavior, schemas, APIs, and existing stored rows unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `database-backends`: file-backed SQLite uses one bounded shared pool and one-time WAL setup.
- `responses-api-compat`: durable operation recording is opt-in.
- `conversations-api`: conversation identifier capture is opt-in.
- `data-retention`: safe bounded windows apply by default when no override is configured.
