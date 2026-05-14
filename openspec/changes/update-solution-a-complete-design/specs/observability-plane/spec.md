## ADDED Requirements
### Requirement: Single Active Observability Backend
The platform SHALL run with one active observability backend profile per environment.

#### Scenario: Production selects Langfuse profile
- **WHEN** production environment is configured for observability
- **THEN** Langfuse is selected as the active backend and receives inference trace data

### Requirement: Langfuse Preferred Integration
The platform SHALL provide first-class integration support for Langfuse as the default observability option.

#### Scenario: Inference request is executed
- **WHEN** data-plane completion is processed
- **THEN** trace metadata, model usage, and cost fields are emitted to Langfuse

### Requirement: Helicone Compatibility Profile
The platform SHALL provide an optional Helicone profile for environments that require Helicone compatibility.

#### Scenario: Environment uses Helicone profile
- **WHEN** Helicone profile is enabled by configuration
- **THEN** observability pipeline emits compatible request metadata to Helicone endpoint

### Requirement: Usage Reconciliation Contract
The control plane SHALL reconcile observability usage data with key audit and policy context for governance reporting.

#### Scenario: Daily reconciliation job runs
- **WHEN** the scheduled reconciliation process executes
- **THEN** usage metrics are joined with virtual key ownership and policy context for admin reporting
