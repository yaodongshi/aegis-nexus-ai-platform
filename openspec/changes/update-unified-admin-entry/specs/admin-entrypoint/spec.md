## ADDED Requirements

### Requirement: Unified Admin Entry Route

The system SHALL expose a primary management entrypoint at `/admin` for administrator-facing backend operations.

#### Scenario: Administrator opens the primary management portal
- **WHEN** an administrator visits `/admin`
- **THEN** the backend returns the management UI page
- **AND** the page identifies itself as the Team AI Admin Console

### Requirement: Legacy Admin Route Compatibility

The system SHALL preserve the existing `/provider-console` route during the transition to the unified admin entrypoint.

#### Scenario: Existing bookmark still works
- **WHEN** an administrator visits `/provider-console`
- **THEN** the backend returns the same management UI page served at `/admin`

### Requirement: Public Docs Distinguish Control Plane and Data Plane

The system SHALL describe 8000 as the administrator control plane, 9000 as the team workspace, and 4000/6333 as internal infrastructure in operator-facing documentation.

#### Scenario: Operator reviews access endpoints
- **WHEN** an operator reads the setup and usage documentation
- **THEN** the documentation explains that administrators manage the platform from the backend admin UI
- **AND** the documentation does not present Qdrant as a normal user entrypoint