## MODIFIED Requirements

### Requirement: File-backed SQLite engines use one bounded shared pool

The production file-backed SQLite request and background session factories MUST share one async engine. That engine MUST use a bounded native pool with exactly four retained connections and no overflow. SQLite `:memory:` databases MUST preserve the existing shared-engine behavior so schema state remains visible to background tasks.

The engine MUST execute `PRAGMA journal_mode=WAL` only for its first connection. Every connection MUST retain `synchronous=NORMAL`, foreign-key enforcement, and the existing busy timeout. PostgreSQL engine creation and its configurable pool controls MUST remain unchanged.

The existing `CODEX_LB_TEST_DATABASE_URL` test escape hatch MUST use `NullPool` so one imported async engine can safely cross the test harness's event-loop boundaries. This exception MUST NOT affect the production database path.

#### Scenario: File SQLite uses one bounded pool

- **GIVEN** `database_url` resolves to a file-backed SQLite database
- **WHEN** the application initializes request and background sessions for that URL
- **THEN** both factories use the same engine
- **AND** its pool size is four with zero overflow

#### Scenario: WAL setup is not repeated per pooled connection

- **GIVEN** the file-backed SQLite pool opens more than one connection
- **WHEN** each connection is configured
- **THEN** `journal_mode=WAL` runs only on the engine's first connection
- **AND** the per-connection safety PRAGMAs run for every connection

#### Scenario: PostgreSQL pooling is unchanged

- **GIVEN** `database_url` resolves to PostgreSQL
- **WHEN** the application creates its main or background async engine
- **THEN** PostgreSQL pool sizing, overflow, pre-ping, and recycle controls remain configured as before

#### Scenario: Test database avoids cross-loop pooling

- **GIVEN** `CODEX_LB_TEST_DATABASE_URL` is set to a file-backed SQLite database
- **WHEN** the test harness creates its async engine
- **THEN** that engine uses `NullPool`
- **AND** the production bounded-pool behavior remains unchanged

## RENAMED Requirements

### Requirement: File-backed SQLite engines do not retain idle pooled descriptors
- **FROM:** File-backed SQLite engines do not retain idle pooled descriptors
- **TO:** File-backed SQLite engines use one bounded shared pool
