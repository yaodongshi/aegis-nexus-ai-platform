## ADDED Requirements

### Requirement: Persistent User Accounts
The platform SHALL persist user identities and credentials in durable storage so accounts survive service restarts and image rebuilds.

#### Scenario: Service restart keeps account login valid
- **WHEN** an existing user account was created and services are rebuilt/restarted
- **THEN** the account can still authenticate without re-registration

### Requirement: Bootstrap Admin Availability
The platform SHALL ensure at least one admin account is available for first-time management access.

#### Scenario: Fresh deployment admin login
- **WHEN** the database has no user rows
- **THEN** the system creates a bootstrap admin from environment defaults/overrides
- **AND** the admin can log in to access management features

### Requirement: Admin User Governance API
The platform SHALL provide admin-only endpoints for user listing, creation, and enable/disable operations.

#### Scenario: Admin creates and disables a member account
- **WHEN** an admin calls the management endpoints with valid admin auth
- **THEN** the system creates users with controlled roles and updates activation status
- **AND** non-admin callers are rejected

### Requirement: Skill Detail Accessibility
The platform SHALL allow operators to open and inspect full skill details from the skill list UI.

#### Scenario: Open skill detail panel
- **WHEN** an operator clicks a skill card in the skills view
- **THEN** the full skill detail (name/category/description/prompt/tags) is shown
- **AND** lifecycle actions (e.g., delete) are available from the detail view

### Requirement: Expired Session Recovery
The platform SHALL consistently handle expired/invalid tokens by clearing local auth state and redirecting users to login.

#### Scenario: Settings API returns token-expired
- **WHEN** any protected API returns an auth-expired response
- **THEN** the client clears stored token
- **AND** redirects to the login page for recovery
