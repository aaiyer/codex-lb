## MODIFIED Requirements

### Requirement: Retention defaults are bounded and validated

Fresh configuration MUST default request-log retention to 30 days and usage-history retention to 45 days. Retention windows are resolved per source with dashboard-first precedence: a non-NULL `dashboard_settings.request_log_retention_days` / `dashboard_settings.usage_history_retention_days` value MUST win; when the dashboard value is NULL the corresponding deprecated env alias (`CODEX_LB_REQUEST_LOG_RETENTION_DAYS` / `CODEX_LB_USAGE_HISTORY_RETENTION_DAYS`) MUST apply; when neither supplies a value, the safe code default MUST apply. At every layer the explicit value `0` means disabled.

The dashboard settings API MUST expose, per retention window, the read-only effective value (`requestLogRetentionDays` / `usageHistoryRetentionDays`) alongside the nullable stored override (`requestLogRetentionOverrideDays` / `usageHistoryRetentionOverrideDays`, `null` = inherit). Updates MUST use only the override fields with tri-state semantics: a field absent from the payload leaves the stored value unchanged; a field present with `null` MUST clear the override back to inherit; a field present with a value MUST store it as the override — including a value equal to the current effective value. Because overrides round-trip verbatim, a full GET-then-PUT save echoing the override fields unchanged MUST NOT alter stored values.

Both the env validators and dashboard settings API MUST accept `0` or values at or above their safety floors (30 days for request logs, 45 days for usage history) up to 3650. Values between 1 and the floor MUST be rejected.

#### Scenario: Default configuration uses bounded retention

- **GIVEN** neither retention setting has a dashboard override or environment value
- **WHEN** effective retention is resolved
- **THEN** request-log retention is 30 days
- **AND** usage-history retention is 45 days

#### Scenario: Unsafe env retention values fail fast

- **WHEN** an operator sets `request_log_retention_days=7` or `usage_history_retention_days=10`
- **THEN** settings validation MUST raise an error at startup naming the violated floor

#### Scenario: Unsafe dashboard retention values are rejected

- **WHEN** a dashboard update carries `requestLogRetentionOverrideDays=7` or `usageHistoryRetentionOverrideDays=10`
- **THEN** the API MUST reject the update with a validation error
- **AND** stored settings remain unchanged

#### Scenario: Full-save echoes round-trip inherit unchanged

- **GIVEN** no dashboard override exists and an env alias supplies the effective retention
- **WHEN** a client performs a full GET-then-PUT save echoing `requestLogRetentionOverrideDays: null` back
- **THEN** the stored value remains NULL so later changes to the env alias still take effect

#### Scenario: An explicit override equal to the env alias is stored

- **GIVEN** `CODEX_LB_REQUEST_LOG_RETENTION_DAYS=90` and no dashboard override
- **WHEN** a client PUTs `requestLogRetentionOverrideDays: 90`
- **THEN** the override MUST be stored even though the effective value remains 90

#### Scenario: Dashboard value overrides the inherited default

- **GIVEN** `CODEX_LB_REQUEST_LOG_RETENTION_DAYS=90` and a dashboard value of 30
- **WHEN** the retention job runs
- **THEN** the request-log cutoff MUST be computed from 30 days

#### Scenario: Dashboard zero disables inherited retention

- **GIVEN** a dashboard usage-history retention override of 0
- **WHEN** the retention job runs
- **THEN** no usage-history rows are deleted

#### Scenario: Present-null restores the inherited default

- **GIVEN** a stored dashboard override and `CODEX_LB_REQUEST_LOG_RETENTION_DAYS=90`
- **WHEN** a client updates the override to `null`
- **THEN** the stored value MUST become NULL
- **AND** effective retention falls back to 90 days

#### Scenario: Env alias applies while the dashboard value is unset

- **GIVEN** a NULL dashboard value and `CODEX_LB_REQUEST_LOG_RETENTION_DAYS=90`
- **WHEN** the retention job runs
- **THEN** the request-log cutoff MUST be computed from 90 days

## RENAMED Requirements

### Requirement: Retention is opt-in and validated
- **FROM:** Retention is opt-in and validated
- **TO:** Retention defaults are bounded and validated
