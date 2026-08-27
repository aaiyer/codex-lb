## ADDED Requirements

### Requirement: Service administrators can pause and resume local routing

The service API MUST expose `POST /api/v1/routing/pause`,
`POST /api/v1/routing/resume`, and `GET /api/v1/routing/status` behind the
existing fail-closed service-admin Bearer authentication dependency. Pause and
resume MUST be idempotent. Status responses MUST contain only the process-local
paused state and current waiter count. Successful mutations MUST emit safe audit
events without credentials or client request data.

The routing gate MUST be process-local and MUST start resumed on every process
start. This scope controls the complete supported single-process SQLite
deployment. Coordinating optional multi-replica PostgreSQL deployments remains
outside this contract.

#### Scenario: Missing service authentication fails closed

- **WHEN** a client calls a routing-maintenance endpoint without a valid configured service-admin token
- **THEN** the request returns the existing structured service-authentication error
- **AND** routing state does not change

#### Scenario: Repeated mutations are idempotent

- **GIVEN** local routing is paused
- **WHEN** an authorized service administrator pauses it again
- **THEN** the endpoint succeeds and routing remains paused
- **WHEN** the administrator resumes it twice
- **THEN** both requests succeed and routing remains resumed

#### Scenario: Status is credential-free

- **WHEN** an authorized service administrator reads routing status
- **THEN** the response contains the paused state and waiter count
- **AND** it contains no account, credential, authorization, prompt, or response data
