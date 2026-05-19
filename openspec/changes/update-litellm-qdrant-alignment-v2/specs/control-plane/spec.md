## MODIFIED Requirements

### Requirement: Admin Control Surface Prioritization
The admin console SHALL prioritize AI governance and closed-loop modules in primary navigation, while keeping legacy non-core modules as compatibility-only entries.

#### Scenario: Primary navigation follows governance-first order
- **WHEN** an administrator opens the main console
- **THEN** primary entries include dashboard, skills, agents, RAG knowledge, repositories, observe, governance, keys, models, and providers
- **AND** legacy modules are displayed separately as compatibility entries

### Requirement: Documentation Baseline Governance
The platform SHALL maintain a single active architecture baseline document and a documentation index that classifies active documents and archived documents.

#### Scenario: Team member checks current execution baseline
- **WHEN** a team member opens the docs index
- **THEN** they can identify the active master plan document
- **AND** phase reports and superseded designs are marked as archived references

### Requirement: MCP Skill Bundle Lifecycle
The platform SHALL support MCP-based skill bundle upload/download and team-wide skill synchronization via generated rules.

#### Scenario: Team publishes and synchronizes a new skill bundle
- **WHEN** an authorized operator uploads a skill bundle through MCP
- **THEN** the bundle is validated, versioned, and stored in the skill registry
- **AND** a team sync rule can be generated and applied to synchronize the skill across team members

### Requirement: Session and CLI Knowledge Evolution Loop
The platform SHALL ingest effective knowledge from session and CLI gateway telemetry into RAG, summarize it into skill updates, and generate agent workflows for continuous optimization.

#### Scenario: Effective knowledge flows from session to RAG and then to skill and agent
- **WHEN** session or CLI interactions produce reusable and validated knowledge
- **THEN** the knowledge is filtered and ingested into RAG with metadata and traceability
- **AND** rule-based summarization produces skill update candidates and agent workflow candidates
- **AND** subsequent execution feedback is ingested for iterative optimization
