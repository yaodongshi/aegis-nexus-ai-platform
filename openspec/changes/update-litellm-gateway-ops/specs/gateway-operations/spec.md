## ADDED Requirements

### Requirement: Standard Gateway Apply Workflow
The system SHALL provide a standard script-based workflow to apply LiteLLM gateway configuration updates after provider changes.

#### Scenario: Apply gateway configuration
- **WHEN** an operator runs the gateway apply script
- **THEN** the script restarts LiteLLM
- **AND** prints a clear follow-up verification command

### Requirement: Optional Models Verification in Health Checks
The system SHALL support optional `/v1/models` verification in health checks when an admin key is available.

#### Scenario: Health check with master key
- **WHEN** `LITELLM_MASTER_KEY` is set in environment
- **THEN** health check executes a `/v1/models` request
- **AND** returns success or warning with actionable output

### Requirement: Consistent Operator Documentation
The system SHALL document a single operational path for applying gateway changes and running MVP checks.

#### Scenario: Operator follows docs
- **WHEN** operator follows README or user guide
- **THEN** steps reference the same scripts and variable names
- **AND** no conflicting admin token variable names appear
