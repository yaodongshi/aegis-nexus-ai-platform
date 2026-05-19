# Specification: Skill Platform - Prompt Template Management & Evolution

## Capability Overview
The skill platform manages reusable prompt templates for AI execution. Users can create, edit, version, and publish skills. Skills can evolve through manual updates or AI-assisted proposals from RAG insights. The platform tracks lineage, versions, and deployment status.

## Core Requirements

### Requirement: Skill Creation & Basic CRUD
The system SHALL allow users to create and manage prompt templates as reusable skills.

#### Scenario: Create Skill
- **WHEN** user calls `POST /api/v1/skills` with name, description, and prompt_content
- **THEN** system creates skill in `draft` state with version `1.0`
- **AND** assigns created_by to current user
- **AND** returns skill ID and metadata

#### Scenario: User Edits Skill (Draft State)
- **WHEN** user calls `PATCH /api/v1/skills/{id}` with updated prompt_content
- **THEN** system allows edit only if current state is `draft` or `unpublished`
- **AND** does NOT auto-increment version (still `1.0` in draft)
- **AND** saves updated_at timestamp

#### Scenario: User Reads Skill Details
- **WHEN** user calls `GET /api/v1/skills/{id}`
- **THEN** system returns complete skill including version history
- **AND** current state, created_by, last_updated_by, and audit trail

#### Scenario: User Lists Own Skills
- **WHEN** user calls `GET /api/v1/skills?created_by=me`
- **THEN** system returns all skills created by that user
- **AND** includes state, current version, and last_updated timestamp

### Requirement: Skill Versioning
The system SHALL track multiple versions of skills and enable rolling back to previous versions.

#### Scenario: Publish Skill Version
- **WHEN** user calls `POST /api/v1/skills/{id}/publish`
- **THEN** system marks current state as `published` and locks it (read-only)
- **AND** creates immutable version record (e.g., `1.0`) in version history
- **AND** returns version ID and effective_at timestamp

#### Scenario: View Skill Version History
- **WHEN** user calls `GET /api/v1/skills/{id}/versions`
- **THEN** system returns list of all versions with: version number, publish date, published_by, diff from previous
- **AND** each version shows which AI models or features used it

#### Scenario: Rollback to Previous Version
- **WHEN** user calls `POST /api/v1/skills/{id}/rollback?version=1.0`
- **THEN** system creates new version that restores previous content
- **AND** increments version counter (e.g., `1.1`)
- **AND** logs rollback with reason
- **AND** publishes immediately if caller is admin or owner

### Requirement: Skill State Lifecycle
The system SHALL enforce clear state transitions: `draft` → `published` → `deprecated` → `archived`.

#### Scenario: Skill Lifecycle Transitions
- **WHEN** skill is in `draft` state
  - **THEN** only owner can edit; not available for execution
- **WHEN** user publishes skill
  - **THEN** state becomes `published`; available for use in `/v1/chat/completions`
- **WHEN** owner calls `POST /api/v1/skills/{id}/deprecate`
  - **THEN** state becomes `deprecated`; still usable but marked as obsolete
  - **AND** frontend shows warning "This skill is deprecated"
- **WHEN** owner calls `POST /api/v1/skills/{id}/archive`
  - **THEN** state becomes `archived`; hidden from default list
  - **AND** can only be accessed by owner via direct ID lookup

#### Scenario: Cannot Edit Published Skill
- **WHEN** user attempts `PATCH /api/v1/skills/{id}` with state `published`
- **THEN** system returns 409 Conflict
- **AND** directs user to create new version via fork or rollback

### Requirement: Skill Tags & Discoverability
The system SHALL allow tagging skills for organization and search.

#### Scenario: Tag Skill with Categories
- **WHEN** user calls `PATCH /api/v1/skills/{id}` with `tags=["nlp", "sentiment-analysis", "production"]`
- **THEN** system stores tags as indexed metadata
- **AND** enables search by tag

#### Scenario: Discover Skills by Tag
- **WHEN** user calls `GET /api/v1/skills?tag=nlp`
- **THEN** system returns all published/available skills with that tag
- **AND** results sorted by: most recently updated, then popularity (usage count)

### Requirement: Skill Usage & Metrics
The system SHALL track usage, success rate, and feedback for skills.

#### Scenario: Track Skill Execution
- **WHEN** LiteLLM executes chat completion using skill ID
- **THEN** system logs: timestamp, user_id, skill_id, model, input_tokens, output_tokens
- **AND** tracks result (success or error)

#### Scenario: View Skill Metrics
- **WHEN** user calls `GET /api/v1/skills/{id}/metrics`
- **THEN** system returns: total executions, success_rate (%), avg_tokens, last_used_at
- **AND** includes 30-day rolling metrics and trend (↑ or ↓)

#### Scenario: Skill Popularity
- **WHEN** user calls `GET /api/v1/skills?sort=popularity`
- **THEN** system returns skills sorted by execution count (descending)

### Requirement: Skill Evolution & Proposal Integration
The system SHALL surface AI-generated improvement proposals linked to RAG insights.

#### Scenario: View Skill Evolution Proposals
- **WHEN** user calls `GET /api/v1/skills/{id}/proposals`
- **THEN** system returns list of pending proposals with: source (Git commit/PR/RAG doc), quality_score, before/after diff
- **AND** each proposal links to originating knowledge artifact

#### Scenario: Approve Skill Proposal
- **WHEN** user calls `POST /api/v1/skills/{id}/proposals/{proposal_id}/approve`
- **THEN** system creates new skill version with proposed content
- **AND** sets state to `published` if auto-approval enabled
- **AND** logs approval with user_id and timestamp
- **AND** links version to proposal via lineage_source

#### Scenario: Reject Skill Proposal with Feedback
- **WHEN** user calls `POST /api/v1/skills/{id}/proposals/{proposal_id}/reject` with reason
- **THEN** system marks proposal as `rejected`
- **AND** stores feedback reason for future evolution algorithm tuning
- **AND** notifies proposal originator (if automated)

## API Boundaries

| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/api/v1/skills` | GET | authenticated | List user's skills |
| `/api/v1/skills` | POST | authenticated | Create skill |
| `/api/v1/skills/{id}` | GET | authenticated | Get skill details |
| `/api/v1/skills/{id}` | PATCH | owner\|admin | Update skill (if draft) |
| `/api/v1/skills/{id}/publish` | POST | owner\|admin | Publish version |
| `/api/v1/skills/{id}/unpublish` | POST | owner\|admin | Unpublish (revert to draft) |
| `/api/v1/skills/{id}/deprecate` | POST | owner\|admin | Mark as deprecated |
| `/api/v1/skills/{id}/archive` | POST | owner\|admin | Archive skill |
| `/api/v1/skills/{id}/versions` | GET | owner\|admin | Version history |
| `/api/v1/skills/{id}/rollback` | POST | owner\|admin | Restore previous version |
| `/api/v1/skills/{id}/metrics` | GET | owner\|admin | Usage metrics |
| `/api/v1/skills/{id}/proposals` | GET | owner\|admin | Evolution proposals |
| `/api/v1/skills/{id}/proposals/{pid}/approve` | POST | owner\|admin | Accept proposal |
| `/api/v1/skills/{id}/proposals/{pid}/reject` | POST | owner\|admin | Reject proposal |

## Data Model

```
Skill:
  id: UUID
  name: string (indexed)
  description: string
  prompt_content: text
  created_by: UUID (foreign key to User)
  owner_id: UUID (can be different from creator)
  state: enum('draft', 'published', 'deprecated', 'archived')
  tags: list of strings (indexed)
  current_version: string (e.g., '1.0')
  created_at: timestamp
  updated_at: timestamp
  updated_by: UUID

SkillVersion:
  id: UUID
  skill_id: UUID (foreign key)
  version: string (semantic versioning)
  prompt_content: text (immutable)
  published_at: timestamp
  published_by: UUID
  lineage_source: JSON (tracks origin: Git commit, RAG doc, etc.)
  test_results: JSON (optional, linked to automated tests)

SkillProposal:
  id: UUID
  skill_id: UUID
  proposed_content: text
  quality_score: float (0-1)
  source_type: enum('git_commit', 'pull_request', 'rag_document', 'user_feedback')
  source_id: string (e.g., Git commit SHA)
  reasoning: text (why this change improves the skill)
  proposed_by: UUID (agent or user)
  status: enum('pending', 'approved', 'rejected')
  created_at: timestamp
  decided_at: timestamp (nullable)
  decided_by: UUID (nullable)
  feedback: text (rejection reason or approval comment)

SkillMetrics:
  skill_id: UUID
  window_start: timestamp (e.g., start of today)
  execution_count: integer
  success_count: integer
  error_count: integer
  avg_input_tokens: float
  avg_output_tokens: float
  last_executed_at: timestamp
```

## Integration Points

- **With RAG Platform**: Receives proposals via `/api/v1/skills/{id}/proposals` endpoint
- **With Git System**: Lineage references Git commit SHAs and PR URLs
- **With LiteLLM**: Published skills available in `/v1/models` and usable in `/v1/chat/completions`
- **With Control Plane**: User/owner validation via role checks

## Non-Functional Requirements

- **Latency**: List 1000 skills <500ms; get skill details <100ms
- **Consistency**: Publish operation atomic (all-or-nothing version creation + state change)
- **Immutability**: Published version content cannot be modified (enforce at DB level via constraints)
