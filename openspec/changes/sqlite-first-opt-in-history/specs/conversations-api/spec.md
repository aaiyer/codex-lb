## ADDED Requirements

### Requirement: Conversation identifier capture is opt-in

Request logging MUST ignore conversation-identifying client headers by default while continuing to record the existing non-conversation request metadata. Operators MAY explicitly enable conversation analytics to extract supported conversation identifiers into new `request_logs` rows. Changing the setting MUST NOT delete or expose existing rows and MUST NOT remove the conversation APIs.

#### Scenario: Default request logging omits conversation identifiers

- **GIVEN** conversation analytics is not configured
- **WHEN** a supported client sends a conversation-identifying header
- **THEN** the request log stores no conversation identifier
- **AND** user-agent fields continue to use their existing extraction behavior

#### Scenario: Operator enables conversation analytics

- **GIVEN** conversation analytics is explicitly enabled
- **WHEN** a supported client sends a conversation-identifying header
- **THEN** the request log stores the identifier using the existing client-specific precedence rules
