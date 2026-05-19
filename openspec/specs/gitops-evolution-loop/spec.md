# Specification: GitOps Evolution Loop - Automated Skill Evolution from Repository Activity

## Capability Overview
The GitOps evolution loop captures development activity (Git commits, PRs, code reviews, experiments) and automatically proposes skill improvements. It provides bidirectional sync between platform skills and Git repositories, with approval gates and rollback capability for safety.

## Core Requirements

### Requirement: Git Hooks & Local CLI Integration
The system SHALL capture development events via Git hooks and local CLI commands.

#### Scenario: Git Push Hook Captures Commit Changes
- **WHEN** developer runs `git push` in local environment with hook installed
- **THEN** local Git hook fires (post-push or CI/CD hook)
- **AND** extracts commit metadata: SHA, author, message, diff, timestamp
- **AND** POSTs to platform: `POST /api/v1/skill-sync/git/capture` with commit data
- **AND** platform returns ack or ingestion status

#### Scenario: Local CLI Update Skill Command
- **WHEN** developer runs `$ ai-cli skill update --experiment-id=exp-123 --path=./prompt.md`
- **THEN** CLI captures local file changes
- **AND** creates patch with before/after content
- **AND** POSTs to platform with metadata: developer_id, timestamp, related_issues
- **AND** platform ingests as source_type='cli_update'

#### Scenario: Bidirectional Sync: Download Skill from Platform
- **WHEN** developer runs `$ ai-cli skill fetch skill-name --save-to=./my-skill.yaml`
- **THEN** CLI calls `GET /api/v1/skills/skill-name` (latest published version)
- **AND** downloads current prompt_content, metadata, tags
- **AND** saves to local file with platform link embedded

#### Scenario: Bidirectional Sync: Push Skill Changes Back to Platform
- **WHEN** developer edits local skill file and runs `$ ai-cli skill push ./my-skill.yaml`
- **THEN** CLI detects changes (diff) and creates patch
- **AND** POSTs to `POST /api/v1/skills/{id}/propose` with source='cli_push'
- **AND** platform creates proposal for owner review

#### Scenario: Conflict Detection in Bidirectional Sync
- **WHEN** developer's local skill version diverges from platform version (edit-then-publish conflict)
- **THEN** CLI detects version mismatch on push attempt
- **AND** returns error with merge strategy options: rebase|manual-resolve|fetch-latest
- **AND** prompts developer to resolve before retry

### Requirement: Passive RAG Ingestion from Git Activity
The system SHALL automatically extract knowledge from Git commits, PRs, and discussions.

#### Scenario: Passive Ingest from Multiple Commits
- **WHEN** CI/CD or scheduled job runs `POST /api/v1/skill-sync/rag/ingest` with batch of recent commits
- **THEN** platform ingests each commit as KnowledgeBase record
- **AND** extracts: commit message (title), diff (code changes), author, timestamp
- **AND** applies heuristic quality scoring (e.g., message clarity, diff size, frequency)
- **AND** filters low-quality items (<0.3 score) and rejects
- **AND** returns ingestion report: received_count, accepted_count, rejected_count

#### Scenario: Auto-Detect Experimental Results in PR Description
- **WHEN** PR created with description containing markers: `[EXPERIMENT] metrics: ...` or `[BENCHMARK] ...`
- **THEN** platform extracts experimental metadata
- **AND** creates high-quality KnowledgeBase record (score ≥0.8 if structured)
- **AND** tags with 'experimental-result' for searchability

#### Scenario: Extract Discussion Insights from Issues
- **WHEN** issue/discussion closed with summary or resolution note
- **THEN** platform (via webhook) captures final discussion state
- **AND** ingests resolved_issue_id with knowledge links to related PRs/commits
- **AND** stores as KnowledgeBase with source_type='issue'

### Requirement: Skill Evolution Pipeline
The system SHALL propose automated Skill improvements based on knowledge insights.

#### Scenario: Evolution Job Searches Knowledge for Skill-Related Insights
- **WHEN** scheduled job runs every N hours (e.g., 6h) to evaluate all active skills
- **THEN** for each skill, searches KnowledgeBase for semantically similar docs (quality ≥0.6)
- **AND** retrieves top-10 docs related to skill's domain
- **AND** passes to LLM prompt-improvement engine with context

#### Scenario: LLM Generates Skill Proposal
- **WHEN** evolution engine receives skill context and knowledge docs
- **THEN** LLM generates: improved_prompt, reasoning, quality_score_estimate, test_cases
- **AND** compares proposed_prompt to current_prompt for meaningful differences (>5% change threshold)
- **AND** if significant, creates SkillProposal record with details
- **AND** proposal status='pending' awaiting owner review

#### Scenario: Proposal Includes Lineage & Reasoning
- **WHEN** proposal is created
- **THEN** it stores: source_knowledge_ids (linked docs), reasoning (why change helps), confidence_score
- **AND** user can view "this was suggested because: [doc1, doc2, ...]" on approval UI

#### Scenario: Proposal Auto-Approval for Low-Risk Changes
- **WHEN** skill owner enables auto-approval policy (e.g., quality_score ≥0.85)
- **THEN** evolution engine automatically approves and applies high-confidence proposals
- **AND** publishes new skill version with state='published'
- **AND** logs auto-approval action with confidence scores
- **AND** sends notification to owner: "Skill X auto-updated from [source]"

#### Scenario: Manual Approval with Review
- **WHEN** proposal has confidence <0.85 or owner disabled auto-approval
- **THEN** system surfaces proposal in UI with before/after diff
- **AND** owner can review reasoning, linked knowledge docs, and test cases
- **AND** owner approves (`POST .../approve`) or rejects (`POST .../reject`) with feedback
- **AND** rejection feedback feeds back to evolution model for tuning

### Requirement: Approval Gates & Governance
The system SHALL enforce governance checks before evolution is applied.

#### Scenario: Approval Gate: Test Execution
- **WHEN** proposal is pending approval
- **THEN** system runs automated tests against proposed_prompt (if test suite exists)
- **AND** compares results to current_prompt results (regression detection)
- **AND** blocks approval if regression detected (>5% success rate drop)
- **AND** owner must manually override or fix proposal

#### Scenario: Approval Gate: Policy Check
- **WHEN** proposal suggests changing sensitive parameters (e.g., system_role, temperature thresholds)
- **THEN** system checks organization policy
- **AND** blocks if policy violation (e.g., "temperature must be ≤0.7")
- **AND** requires admin approval if attempting policy override

#### Scenario: Approval Gate: Audit Trail
- **WHEN** proposal is approved
- **THEN** system logs: proposal_id, approver_id, approval_timestamp, applied_version_id, decision_details
- **AND** creates immutable audit record for compliance

### Requirement: Rollback Capability
The system SHALL enable rollback if evolution introduces regressions.

#### Scenario: Detect Performance Regression
- **WHEN** skill execution metrics show degradation (>10% error rate increase after auto-evolution)
- **THEN** system alerts owner: "Skill X performance degraded after version Y. [Rollback] button"

#### Scenario: Manual Rollback
- **WHEN** owner clicks [Rollback] button on skill version
- **THEN** system calls `POST /api/v1/skills/{id}/rollback`
- **AND** restores previous stable version
- **AND** immediately publishes (state='published')
- **AND** logs rollback with reason and initiator

### Requirement: GitOps Observability
The system SHALL provide visibility into the evolution workflow and decisions.

#### Scenario: View Evolution Timeline
- **WHEN** user accesses skill detail page and clicks "Evolution Timeline" tab
- **THEN** system displays chronological log of:
  - Commits that influenced this skill (Git source)
  - Knowledge documents ingested (RAG source)
  - Proposals generated (with confidence score)
  - Approvals/rejections (with reason)
  - Versions applied (with lineage)
  - Rollbacks (with cause)

#### Scenario: Evolution Dashboard
- **WHEN** operator accesses `GET /api/v1/dashboard/evolution`
- **THEN** system returns metrics: total proposals_generated, approved_count, rejected_count, auto_approved_count
- **AND** breakdown by skill, by source_type (git|rag_doc|issue)
- **AND** recent activities (last 7 days)

## API Boundaries

| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/api/v1/skill-sync/git/capture` | POST | cli\|webhook | Capture Git events |
| `/api/v1/skill-sync/rag/ingest` | POST | agent\|webhook | Bulk ingest knowledge |
| `/api/v1/skills/{id}/propose` | POST | cli\|agent | Create evolution proposal |
| `/api/v1/skills/{id}/proposals` | GET | owner\|admin | List proposals for skill |
| `/api/v1/skills/{id}/proposals/{pid}/approve` | POST | owner\|admin | Approve proposal |
| `/api/v1/skills/{id}/proposals/{pid}/reject` | POST | owner\|admin | Reject proposal |
| `/api/v1/skills/{id}/rollback` | POST | owner\|admin | Rollback version |
| `/api/v1/dashboard/evolution` | GET | admin | Evolution metrics |
| `/api/v1/skills/{id}/evolution-timeline` | GET | owner\|admin | Evolution history |

## Data Model Extensions

```
GitEvent:
  id: UUID
  event_type: enum('commit', 'pr_created', 'pr_merged', 'issue_closed', 'discussion_resolved')
  repository_url: string
  git_ref: string (commit SHA or PR #)
  git_author: string
  captured_at: timestamp
  ingested_into_knowledge: boolean
  knowledge_ids: list of UUID (if ingested)

SkillProposal (extends from skill-platform):
  # Additional fields for evolution tracking
  generated_by: enum('manual', 'auto_evolution', 'cli_push')
  confidence_score: float [0,1] (for auto-generated)
  test_results: JSON (pass/fail, regression delta)
  policy_checks: JSON (compliance results)
  approval_gate_status: enum('pending', 'passed', 'failed_tests', 'failed_policy')
  evolution_timeline_id: UUID (link to evolution log)

EvolutionTimeline:
  id: UUID
  skill_id: UUID
  event_type: enum('commit_ingested', 'proposal_generated', 'proposal_approved', 'version_published', 'rollback')
  event_timestamp: timestamp
  source_metadata: JSON (Git commit, knowledge_id, proposal_id, etc.)
  user_id: UUID (nullable, agent if automated)
  details: text (decision reasoning, metrics, etc.)
```

## Integration Points

- **With Git System**: Receives webhooks from GitHub/GitLab/Gitea; CLI tool syncs with platform
- **With RAG Platform**: Ingests knowledge; searches for evolution signals
- **With Skill Platform**: Creates proposals; applies versions; tracks lineage
- **With LLM Provider**: Uses embedding/generation APIs for proposal creation
- **With Test Framework**: Runs regression tests on proposals before approval
- **With Control Plane**: Enforces policy checks; audits decisions

## Non-Functional Requirements

- **Proposal Latency**: Generated within 30 min of knowledge ingestion for scheduled jobs
- **Evolution Frequency**: Jobs run at most every 6 hours per skill (configurable)
- **Consistency**: Proposal creation atomic with knowledge ingestion (no orphaned proposals)
- **Safety**: All auto-approvals require confidence_score ≥0.85; below threshold → manual gate
- **Rollback**: Can rollback within 24h; older versions require manual intervention
- **Observability**: All evolution decisions logged with full context for audit/compliance
