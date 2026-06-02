## MODIFIED Requirements

### Requirement: Approval Gates & Governance
The system SHALL enforce governance checks before evolution is applied and before strategy promotion in runtime rollout.

#### Scenario: Block Promotion on Regression
- **WHEN** canary metrics for a candidate strategy fail threshold checks
- **THEN** system blocks promotion
- **AND** triggers rollback path and alert notification

#### Scenario: Require Runtime Conformance Validation
- **WHEN** a new runtime adapter is introduced for evolution workflows
- **THEN** system validates adapter conformance tests
- **AND** rejects rollout if mandatory scenarios fail

## ADDED Requirements

### Requirement: Evolution Strategy Promotion Lifecycle
The system SHALL evaluate candidate evolution strategies through canary windows before full adoption.

#### Scenario: Candidate Promotion After Success Window
- **WHEN** candidate strategy passes configured success criteria during evaluation window
- **THEN** system promotes strategy for full traffic
- **AND** records baseline versus candidate metrics for audit

#### Scenario: Candidate Demotion After Drift Detection
- **WHEN** post-promotion drift indicates sustained regression
- **THEN** system demotes candidate strategy
- **AND** restores prior stable strategy automatically
- **AND** links demotion to associated execution traces
