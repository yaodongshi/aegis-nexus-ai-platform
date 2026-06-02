## MODIFIED Requirements

### Requirement: Model Authorization Policy
The system SHALL enforce model and capability authorization policies and bind rollout/rollback governance to capability aliases.

#### Scenario: Capability Alias Policy Enforcement
- **WHEN** admin configures policy for capability alias `chat-default`
- **THEN** system applies policy checks before runtime execution
- **AND** policy violations block execution with explicit reason

#### Scenario: Policy-Aware Rollback
- **WHEN** strategy rollback occurs on a protected capability alias
- **THEN** system verifies rollback policy allows downgrade
- **AND** writes immutable governance audit record with decision metadata

## ADDED Requirements

### Requirement: Control-Plane Runtime Governance Hooks
The system SHALL expose governance hooks for runtime state transitions and rollout decisions.

#### Scenario: Approval Required for Risky Transition
- **WHEN** runtime requests transition into `promoted` for high-risk capability
- **THEN** system requires approval workflow completion
- **AND** denies transition until approval is granted

#### Scenario: Immutable Rollout Decision Audit
- **WHEN** promote, demote, or rollback decision is finalized
- **THEN** system records actor, metrics, thresholds, and rationale
- **AND** records are append-only and queryable by operators
