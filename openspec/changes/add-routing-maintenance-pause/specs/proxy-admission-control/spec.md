## ADDED Requirements

### Requirement: A routing maintenance pause holds new work locally

While the process-local routing gate is paused, new proxy HTTP requests MUST
remain connected without receiving response headers, response body bytes, or a
local maintenance error, and MUST NOT begin account selection or upstream work.
New Responses turns received on an already-connected downstream WebSocket MUST
remain pending locally without an error event and MUST NOT be sent upstream.
Already-admitted HTTP requests and Responses turns MAY finish normally.

Resume MUST wake every connected waiter. Each released request or turn MUST
perform account selection only after it is released so it observes the current
pool. A disconnected or cancelled client MUST be removed from the waiter count.
Dashboard, health, internal, and service-administration routes MUST remain
available while routing is paused.

#### Scenario: HTTP request waits without a response

- **GIVEN** local routing is paused
- **WHEN** a client sends a proxy HTTP request
- **THEN** codex-lb sends no HTTP response headers or body and starts no upstream work while paused
- **WHEN** routing resumes
- **THEN** the same request continues through ordinary routing

#### Scenario: Existing Responses WebSocket holds a new turn

- **GIVEN** a downstream Responses WebSocket was connected before routing paused
- **WHEN** the client sends a new `response.create` frame while paused
- **THEN** codex-lb keeps the WebSocket connected and emits no maintenance error
- **AND** it does not prepare, select, reserve, connect, or send upstream work for that turn
- **WHEN** routing resumes
- **THEN** the held turn continues through ordinary preparation and routing

#### Scenario: Already-admitted work completes

- **GIVEN** a request or Responses turn passed the gate before pause began
- **WHEN** routing is paused
- **THEN** that work may finish normally
- **AND** later work waits behind the closed gate

#### Scenario: Waiting client disconnects

- **GIVEN** a client is waiting for routing to resume
- **WHEN** its task is cancelled or its connection disconnects
- **THEN** the waiter is removed without upstream work or a leaked reservation
