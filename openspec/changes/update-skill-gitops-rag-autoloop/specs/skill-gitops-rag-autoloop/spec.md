## ADDED Requirements

### Requirement: Git Hook Triggered Skill Sync
The platform SHALL support receiving and processing skill change events triggered by Git hooks or equivalent local watchers.

#### Scenario: Local hook reports a skill change
- **WHEN** a CLI environment reports a hook event containing repository, commit, and changed skill files
- **THEN** the platform stores the event with an idempotency key
- **AND** the platform links changed files to skill records or creates pending mapping tasks

### Requirement: Bidirectional Skill Repository Sync
The platform SHALL support both push-to-repo and pull-from-repo sync for managed skills with deterministic conflict handling.

#### Scenario: Platform pulls latest skill artifacts from repository
- **WHEN** a pull sync is triggered for a configured skill repository
- **THEN** the platform ingests newer artifact versions
- **AND** conflicting updates are marked as review-required instead of auto-overwrite

### Requirement: Passive RAG Ingestion from Daily Work
The platform SHALL ingest knowledge signals from daily engineering activities without requiring explicit manual knowledge entry.

#### Scenario: Commit and task artifacts are ingested
- **WHEN** commit metadata, PR comments, and task reports arrive through configured connectors
- **THEN** the platform extracts chunks and source trace metadata
- **AND** the platform indexes valid chunks into RAG with quality scores

### Requirement: RAG-to-Skill Proposal Loop
The platform SHALL generate skill update proposals from validated RAG signals and route them through governance before release.

#### Scenario: High-confidence signal creates proposal
- **WHEN** repeated high-confidence retrieval signals indicate a stable improvement opportunity
- **THEN** the platform creates a draft skill update proposal with evidence links
- **AND** the proposal requires approval before promotion to active skill

### Requirement: Governance, Rollback, and Observability
The platform SHALL provide approval audit trail, rollback operations, and operational metrics for auto-evolution workflows.

#### Scenario: Proposal is approved and later rolled back
- **WHEN** an approved proposal causes measurable regression in canary metrics
- **THEN** operators can rollback to the previous skill version in one action
- **AND** the audit log records the proposal, approver, rollback reason, and impacted scope
