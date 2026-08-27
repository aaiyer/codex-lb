## 1. SQLite engine

- [x] 1.1 Bound the file-backed SQLite pool at four connections with no overflow
- [x] 1.2 Share the main SQLite engine with background sessions in the production path
- [x] 1.3 Apply WAL on first connect and retain the existing per-connection PRAGMAs

## 2. Opt-in history defaults

- [x] 2.1 Default the durable HTTP bridge operation ledger off
- [x] 2.2 Gate conversation identifier extraction behind a default-off setting
- [x] 2.3 Default request-log retention to 30 days and usage-history retention to 45 days

## 3. Verification and documentation

- [x] 3.1 Update focused regression tests
- [x] 3.2 Regenerate the settings reference
- [x] 3.3 Validate OpenSpec and run repository checks
- [x] 3.4 Preserve the cross-event-loop test database escape hatch and verify CI feature tests opt in explicitly
