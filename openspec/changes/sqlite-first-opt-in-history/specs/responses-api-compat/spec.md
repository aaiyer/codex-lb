## ADDED Requirements

### Requirement: Durable operation recording is opt-in

The HTTP responses session bridge operation ledger MUST be disabled by default. While disabled, the proxy MUST NOT create durable operation rows or event spools, attach durable operation metadata, or admit recovery paths that require the ledger. Operators MAY explicitly enable the existing ledger and its bounded transcript retention behavior.

#### Scenario: Default bridge traffic writes no durable transcript

- **GIVEN** the operation-ledger setting is not configured
- **WHEN** an eligible HTTP bridge request is submitted and streamed
- **THEN** no durable operation row or event spool is created
- **AND** the request keeps the existing non-ledger continuity behavior

#### Scenario: Operator enables durable recovery

- **GIVEN** the operation-ledger setting is explicitly enabled
- **WHEN** an eligible bridge request is submitted
- **THEN** the existing durable operation, replay-fence, and transcript-retention requirements apply
