## ADDED Requirements
### Requirement: Skill Registry as Control Plane Resource
The control plane SHALL manage Skill packages as versioned registry resources with ownership and lifecycle metadata.

#### Scenario: Skill package is registered
- **WHEN** an admin registers a new skill package version
- **THEN** the platform stores identity, owner scope, version metadata, and publication status

### Requirement: RAG Registry as Control Plane Resource
The control plane SHALL manage RAG datasets and retrieval settings as governed registry resources.

#### Scenario: RAG dataset is registered
- **WHEN** a dataset registration request is accepted
- **THEN** the platform stores dataset identity, embedding configuration, and sharing scope

### Requirement: Cloud Sync Workflow for Skill and RAG
The platform SHALL provide sync status tracking for Skill and RAG resources between local control-plane state and cloud artifacts.

#### Scenario: Sync operation completes
- **WHEN** a sync workflow is executed for a Skill or RAG resource
- **THEN** the resource status records success or failure with timestamp and operator context

### Requirement: Governance Binding with Virtual Keys
The platform SHALL allow Skill and RAG resources to be associated with team and key policy context for access governance.

#### Scenario: Team key accesses governed Skill
- **WHEN** a request references a Skill bound to team governance
- **THEN** authorization checks evaluate virtual key ownership and active policy before granting access
