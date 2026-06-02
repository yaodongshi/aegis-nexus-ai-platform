## ADDED Requirements

### Requirement: Pluggable Harness Runtime Adapter
The system SHALL provide a pluggable runtime adapter layer so execution engines can be replaced without changing business-facing control-plane contracts.

#### Scenario: Route Plan Execution Through Adapter
- **WHEN** a task plan is created for a capability alias
- **THEN** control-plane resolves the runtime adapter for that alias
- **AND** execution starts through adapter APIs
- **AND** business-facing API contracts remain unchanged

#### Scenario: Swap Runtime Engine Without Contract Break
- **WHEN** operator switches from runtime A to runtime B for a capability alias
- **THEN** existing control-plane endpoints continue to function
- **AND** clients do not need payload shape changes

### Requirement: Task Plan Lock State Machine
The system SHALL enforce a strict task state machine where only validated runtime/tool events can transition state.

#### Scenario: Reject Invalid Transition
- **WHEN** an event tries to move plan state from `created` directly to `completed`
- **THEN** system rejects transition with validation error
- **AND** records rejection in audit log

#### Scenario: Tool-Only Terminal State
- **WHEN** model text claims completion without corresponding runtime tool event
- **THEN** system does not mark plan as `completed`
- **AND** plan remains in last valid non-terminal state

### Requirement: Strategy Rollout and Rollback Control
The system SHALL support canary rollout, promote/demote, and rollback at capability alias level.

#### Scenario: Promote Strategy After Canary Success
- **WHEN** candidate strategy meets configured success, latency, and cost thresholds in canary window
- **THEN** system promotes candidate strategy for full traffic
- **AND** writes immutable rollout decision audit event

#### Scenario: Automatic Rollback on Regression
- **WHEN** candidate strategy violates regression thresholds during rollout
- **THEN** system rolls back to previous stable strategy
- **AND** marks decision as `rolled_back`
- **AND** emits alert event for operators

### Requirement: End-to-End Trace Propagation
The system SHALL propagate a unified trace identifier across frontend, control-plane, runtime adapter, and gateway.

#### Scenario: Query Full Execution Trace
- **WHEN** operator inspects a failed plan
- **THEN** system can retrieve all events by shared `trace_id`
- **AND** include control-plane decisions, runtime events, and gateway invocations

#### Scenario: Replay From Trace
- **WHEN** operator triggers replay on a failed plan
- **THEN** system rehydrates execution context from stored events
- **AND** starts replay from the last stable checkpoint
