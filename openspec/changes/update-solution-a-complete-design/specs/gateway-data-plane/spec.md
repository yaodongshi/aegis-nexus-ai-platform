## ADDED Requirements
### Requirement: Unified Data Plane via LiteLLM
The system SHALL expose a single OpenAI-compatible data-plane endpoint through LiteLLM for all supported CLI clients.

#### Scenario: CLI client uses unified endpoint
- **WHEN** a supported client sends completion requests to the platform endpoint
- **THEN** the request is accepted through LiteLLM without client-specific protocol changes

### Requirement: Deterministic Runtime Config Generation
The control plane SHALL generate LiteLLM runtime configuration deterministically from persisted governance state.

#### Scenario: Key policy update triggers config regeneration
- **WHEN** a virtual key policy is created or updated
- **THEN** the generated LiteLLM configuration reflects the latest allowed and denied model constraints

### Requirement: Safe Gateway Apply and Verification
The platform SHALL provide an operational flow to apply gateway config changes and verify data-plane readiness.

#### Scenario: Operator applies gateway config
- **WHEN** operator runs gateway apply workflow
- **THEN** system validates config syntax and verifies model listing endpoint before marking the apply action successful
