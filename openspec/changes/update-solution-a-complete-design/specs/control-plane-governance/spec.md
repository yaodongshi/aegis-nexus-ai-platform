## ADDED Requirements
### Requirement: Team-Centric Governance Model
The control plane SHALL manage ownership using team, owner type, and owner ID as first-class governance fields.

#### Scenario: Virtual key created for a service owner
- **WHEN** an admin creates a virtual key with owner type `service`
- **THEN** the key record stores team ID, owner type, and owner ID for policy and audit scope

### Requirement: Virtual Key Lifecycle Operations
The control plane SHALL support create, list, revoke, and rotate lifecycle operations for virtual keys.

#### Scenario: Key rotation keeps ownership continuity
- **WHEN** an admin rotates an active key
- **THEN** the old key becomes revoked and the new key references the old key via lifecycle linkage

### Requirement: Policy Enforcement Metadata
The control plane SHALL persist key policy metadata including allow/deny model lists, quotas, rate limits, burst limits, and emergency block state.

#### Scenario: Admin updates key policy
- **WHEN** admin submits a key policy update
- **THEN** the policy record is upserted and retrievable through policy query endpoint

### Requirement: Control Plane API Namespace
The control plane SHALL expose governance APIs under `/api/v1/*` and SHALL not mix them into data-plane namespace.

#### Scenario: Client requests governance API
- **WHEN** an admin calls a key management endpoint
- **THEN** the route is served from `/api/v1/*` and requires control-plane authentication
