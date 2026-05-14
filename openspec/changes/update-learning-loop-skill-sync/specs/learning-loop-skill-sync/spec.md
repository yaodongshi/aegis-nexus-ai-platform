## ADDED Requirements

### Requirement: Task Completion Reporting
The system SHALL provide an API that allows external execution tools to report completed task summaries and error context.

#### Scenario: Tool reports completed task
- **WHEN** a tool client calls `POST /api/task-runs/report` with task summary and lessons learned
- **THEN** the system stores a task run record
- **AND** the system creates a draft skill update proposal linked to the task run

### Requirement: Skill Update Application Flow
The system SHALL allow administrators to apply a skill update proposal into a managed skill record.

#### Scenario: Admin applies a proposal
- **WHEN** an admin calls `POST /api/skill-updates/{update_id}/apply`
- **THEN** the proposal status becomes `applied`
- **AND** the target skill metadata is updated with proposed prompts and rationale

### Requirement: Skill Bundle Sync
The system SHALL support syncing applied skill updates to reusable files for local cache or Git repository workflows.

#### Scenario: Admin syncs skill update to local cache
- **WHEN** an admin calls `POST /api/skill-updates/{update_id}/sync` with mode `local`
- **THEN** the system writes a skill bundle file under the configured output path
- **AND** the proposal status becomes `synced`

#### Scenario: Admin syncs skill update to git
- **WHEN** an admin calls `POST /api/skill-updates/{update_id}/sync` with mode `git`
- **THEN** the system writes a skill bundle file under repository path
- **AND** the system optionally performs git add/commit based on request options

### Requirement: Admin Console Learning Tab
The system SHALL provide a learning loop tab in the admin console for reporting task outcomes and operating skill update proposals.

#### Scenario: Admin manages learning loop from UI
- **WHEN** an admin opens `/admin` and switches to the learning tab
- **THEN** the page allows submitting task reports
- **AND** the page lists skill update proposals with apply and sync actions
