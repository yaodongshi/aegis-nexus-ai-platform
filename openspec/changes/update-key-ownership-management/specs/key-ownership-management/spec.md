## ADDED Requirements

### Requirement: Virtual Keys Store Human-Readable Ownership Labels

The system SHALL persist a human-readable label for each issued virtual key so administrators can identify which colleague or usage scenario the key belongs to.

#### Scenario: Admin issues a labeled key
- **WHEN** an administrator issues a virtual key with a label
- **THEN** the key record stores that label
- **AND** subsequent key list responses return the label

### Requirement: Virtual Keys Are Filterable By Ownership Context

The system SHALL allow administrators to filter virtual keys by member, project, status, or free-text keyword.

#### Scenario: Admin narrows keys to one colleague
- **WHEN** an administrator requests the key list with `user_id=u_1001`
- **THEN** only keys owned by `u_1001` are returned

#### Scenario: Admin searches by keyword
- **WHEN** an administrator requests the key list with a keyword that matches a label or project
- **THEN** the response only includes matching keys

### Requirement: Admin UI Shows Key Ownership Fields

The admin console SHALL expose key owner, project, scope, quota, and label fields during key issuance and list rendering.

#### Scenario: Admin opens key management
- **WHEN** the administrator switches to the key management tab
- **THEN** the issue form includes fields for label, member, project, scope, quota, and expiry
- **AND** the key list shows ownership metadata for each key