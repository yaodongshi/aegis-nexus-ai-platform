# Specification: Control Plane - Team Governance & Administration

## Capability Overview
The control plane provides centralized governance, team management, user lifecycle, virtual key management, model authorization, and policy enforcement for the AI platform. It exposes REST APIs under `/api/v1/*` and implements RBAC-based access control with auditability.

## Core Requirements

### Requirement: Persistent User Account Management
The system SHALL maintain durable user accounts with authentication credentials, roles, and metadata across platform restarts.

#### Scenario: Bootstrap Admin User
- **WHEN** platform starts for the first time
- **THEN** system creates a default admin user with provided credentials (from bootstrap token)
- **AND** stores credentials with PBKDF2-HMAC-SHA256 hashing
- **AND** no other user can be created until admin initializes platform

#### Scenario: Create User by Admin
- **WHEN** admin invokes `POST /api/v1/users` with name, email, password
- **THEN** system creates user with `active=true` and assigned role
- **AND** returns user ID and confirmation

#### Scenario: User Login
- **WHEN** user submits credentials to `POST /api/v1/auth/login`
- **THEN** system validates password hash
- **AND** if valid, returns JWT token with expiry (e.g., 24h) and refresh token
- **AND** if invalid, returns 401 Unauthorized

### Requirement: User Lifecycle Management
The system SHALL support user enable/disable, password reset, and role assignment via admin interface.

#### Scenario: Admin Disables User
- **WHEN** admin invokes `PATCH /api/v1/users/{id}` with `active=false`
- **THEN** user's active sessions are invalidated
- **AND** future login attempts fail with "account disabled" message

#### Scenario: User Requests Password Reset
- **WHEN** user initiates password reset from login page
- **THEN** system sends reset token via email or other channel
- **AND** token is single-use and expires in 1 hour
- **AND** user can set new password via reset link

#### Scenario: Admin Forces Re-login on Token Expiry
- **WHEN** user's JWT token expires (>24h)
- **THEN** frontend detects 401 response from API
- **AND** redirects to login page with message "Session expired, please login again"
- **AND** user must re-authenticate

### Requirement: Role-Based Access Control (RBAC)
The system SHALL enforce role-based permissions for all operations.

#### Scenario: Admin Performs User Management
- **WHEN** admin with role `admin` calls `GET /api/v1/users`
- **THEN** system returns full list of users with all fields
- **AND** no other role can access this endpoint

#### Scenario: User Accesses Own Profile
- **WHEN** user with role `user` calls `GET /api/v1/users/me`
- **THEN** system returns their own profile only
- **AND** excludes sensitive fields (password hash, reset tokens)

#### Scenario: Guest Access to Public Resources
- **WHEN** unauthenticated request attempts to access protected resource
- **THEN** system returns 403 Forbidden
- **AND** redirects to login page

### Requirement: Virtual Key Management
The system SHALL manage virtual keys for model access, tied to users, with rate limiting and audit trails.

#### Scenario: Admin Creates Virtual Key
- **WHEN** admin calls `POST /api/v1/keys` with name and user assignment
- **THEN** system generates cryptographically secure token (32+ chars)
- **AND** returns key once (not stored in plain text)
- **AND** stores hashed key in database

#### Scenario: User Uses Virtual Key for API Access
- **WHEN** user or external consumer calls `POST /v1/chat/completions` with header `Authorization: Bearer {virtual_key}`
- **THEN** system verifies key is valid and maps to active user
- **AND** increments rate-limit counter for that user
- **AND** forwards request to LiteLLM with user context

#### Scenario: Virtual Key Expiry
- **WHEN** virtual key reaches expiry date or is manually revoked
- **THEN** system rejects future requests with that key
- **AND** logs revocation event with timestamp and admin user

### Requirement: Model Authorization Policy
The system SHALL enforce which models users can access based on policies.

#### Scenario: Admin Configures Model Access
- **WHEN** admin calls `POST /api/v1/policies/model-access` with model name and allowed user groups
- **THEN** system stores policy
- **AND** enforces it in `/v1/models` responses (only returns models user is authorized for)

#### Scenario: User Queries Available Models
- **WHEN** user calls `GET /v1/models` with their token
- **THEN** system returns only models they are authorized for based on policies
- **AND** excludes disabled or restricted models

### Requirement: Audit Logging
The system SHALL maintain tamper-proof audit logs of all governance actions.

#### Scenario: Admin Action Logged
- **WHEN** admin creates/updates/deletes user or policy
- **THEN** system logs: timestamp, admin user ID, action type, affected resource, old/new values
- **AND** logs are immutable (no deletion, only append)

#### Scenario: Security Review
- **WHEN** operator queries `GET /api/v1/audit-logs?resource=user&action=create`
- **THEN** system returns paginated list of user creation events
- **AND** includes admin IDs and timestamps for accountability

## API Boundaries

| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/api/v1/auth/login` | POST | public | User authentication |
| `/api/v1/auth/refresh` | POST | authenticated | Refresh JWT token |
| `/api/v1/users` | GET | admin | List all users |
| `/api/v1/users` | POST | admin | Create user |
| `/api/v1/users/{id}` | PATCH | admin | Update user (enable/disable/role) |
| `/api/v1/users/me` | GET | authenticated | Get own profile |
| `/api/v1/keys` | POST | admin | Create virtual key |
| `/api/v1/keys` | GET | authenticated | List own keys |
| `/api/v1/keys/{id}` | DELETE | admin\|owner | Revoke key |
| `/api/v1/policies/model-access` | POST\|GET\|DELETE | admin | Model authorization policies |
| `/api/v1/audit-logs` | GET | admin | Query audit trail |

## Data Model

```
User:
  id: UUID (primary key)
  username: string (unique)
  email: string (unique)
  password_hash: string (PBKDF2-HMAC-SHA256)
  role: enum('admin', 'user')
  active: boolean (default true)
  created_at: timestamp
  updated_at: timestamp

VirtualKey:
  id: UUID
  user_id: UUID (foreign key)
  key_hash: string
  name: string
  created_at: timestamp
  expires_at: timestamp (nullable)
  revoked_at: timestamp (nullable)

Policy:
  id: UUID
  policy_type: enum('model-access', 'rate-limit', ...)
  target_resource: string (e.g., 'model:gpt-4')
  allowed_roles: list of roles
  conditions: JSON (additional constraints)
  created_at: timestamp
  updated_at: timestamp

AuditLog:
  id: UUID
  timestamp: timestamp
  admin_user_id: UUID
  action_type: string (create|update|delete|login_failed)
  resource_type: string (user|key|policy)
  resource_id: UUID
  old_value: JSON (nullable)
  new_value: JSON (nullable)
  status: enum('success', 'failure')
  details: string (nullable)
```

## Non-Functional Requirements

- **Latency**: User lookups <100ms (indexed by username/email)
- **Consistency**: Role/policy changes visible to new API requests within 1 second
- **Availability**: Auth service 99.9% uptime SLA
- **Security**: All tokens signed with HS256, rotation every 24h
- **Audit**: Retention of audit logs ≥1 year
