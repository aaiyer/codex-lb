## 1. Contract

- [x] 1.1 Define service-admin routing pause, resume, and status behavior
- [x] 1.2 Define HTTP and existing-WebSocket waiting semantics

## 2. Implementation

- [x] 2.1 Add one process-local routing gate with cancellation-safe waiter accounting
- [x] 2.2 Gate proxy HTTP/WebSocket admission and new Responses turns
- [x] 2.3 Add authenticated service API endpoints and safe audit events

## 3. Verification and documentation

- [x] 3.1 Add unit and integration regression coverage
- [x] 3.2 Document the service API workflow and process-local ceiling
- [x] 3.3 Verify generated OpenAPI, strict OpenSpec, lint, types, and focused tests
