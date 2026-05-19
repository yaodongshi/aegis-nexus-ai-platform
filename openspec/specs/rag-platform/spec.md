# Specification: RAG Platform - Knowledge Base & Document Management

## Capability Overview
The RAG (Retrieval-Augmented Generation) platform ingests documents from multiple sources (Git commits, PRs, issues, user uploads, session artifacts), stores them with vector embeddings, and provides semantic search. RAG documents are immutable, quality-scored, and linked to Skill evolution proposals.

## Core Requirements

### Requirement: Document Ingestion from Multiple Sources
The system SHALL accept documents from passive sources (Git, sessions) and active sources (user upload, feedback).

#### Scenario: Ingest Passive Document from Git Commit
- **WHEN** Git hook fires on commit (via CI/CD or local hook)
- **THEN** system extracts commit metadata (SHA, author, timestamp, message, diff)
- **AND** parses code changes as document content
- **AND** creates knowledge record with source_type='git_commit', source_id=commit_SHA
- **AND** stores with idempotency check (same commit SHA = no duplicate)

#### Scenario: Ingest Passive Document from Pull Request
- **WHEN** PR event fires (via webhook)
- **THEN** system extracts PR metadata (title, description, diff, reviewers)
- **AND** creates knowledge record with source_type='pull_request', source_id=PR_url
- **AND** includes PR state (open, merged, closed) and timestamp

#### Scenario: Ingest Passive Document from Issue or Discussion
- **WHEN** issue/discussion created or updated
- **THEN** system extracts title, description, and comments
- **AND** creates knowledge record linking issue number and latest state
- **AND** updates on new comments with incremental knowledge addition

#### Scenario: Ingest from User Session or Experiment
- **WHEN** user logs experiment result or session transcript
- **THEN** system receives via `POST /api/v1/knowledge/ingest` with content, metadata, quality_score
- **AND** creates knowledge record with source_type='user_session' or 'experiment'
- **AND** stores quality_score provided by user or AI ranker

#### Scenario: Bulk Ingest via Passive RAG Pipeline
- **WHEN** system receives `POST /api/v1/skill-sync/rag/ingest` with batch of items
- **THEN** system validates: source_id uniqueness, content non-empty, quality_score in [0,1]
- **AND** filters items by min_quality_score threshold (e.g., >0.5)
- **AND** deduplicates by (source_type, source_id) pair
- **AND** stores accepted items and returns rejection details

### Requirement: Document Storage & Retrieval
The system SHALL store documents with metadata and enable semantic search via embeddings.

#### Scenario: Store Document with Embedding
- **WHEN** document is ingested
- **THEN** system calls embedding provider (OpenAI, Langfuse, etc.) to vectorize content
- **AND** stores: document_id, content, embedding_vector, source metadata, quality_score, created_at
- **AND** maintains "created_at" immutably (document records never modified)

#### Scenario: Semantic Search
- **WHEN** user or evolution algorithm calls `POST /api/v1/knowledge/search` with query
- **THEN** system vectorizes query
- **AND** runs cosine-similarity search against stored embeddings
- **AND** returns top-K results with scores and source links
- **AND** results sorted by similarity score (descending)

#### Scenario: Filter Search Results
- **WHEN** user calls `GET /api/v1/knowledge/search?query=...&source_type=git_commit&min_quality=0.8`
- **THEN** system applies filters before ranking
- **AND** returns only git commits with quality_score ≥0.8
- **AND** respects time range filters if provided (e.g., last 7 days)

#### Scenario: Retrieve Knowledge by ID
- **WHEN** caller requests `GET /api/v1/knowledge/{id}`
- **THEN** system returns full document with: id, content, source info, quality_score, embedding_metadata
- **AND** includes lineage: which Skill proposals reference this doc

### Requirement: Quality Scoring & Filtering
The system SHALL assess document quality and filter by threshold before using for Skill evolution.

#### Scenario: Auto-Score Quality on Ingest
- **WHEN** document is ingested without explicit quality_score
- **THEN** system applies heuristic ranker: content length, keyword relevance, source credibility
- **AND** stores auto-calculated quality_score in [0,1]
- **AND** documents with score <0.2 are rejected silently (logged, not stored)

#### Scenario: User Provides Quality Feedback
- **WHEN** user sees proposed Skill change from RAG doc and rejects it
- **THEN** user can call `PATCH /api/v1/knowledge/{id}` with feedback
- **AND** system adjusts quality_score and stores feedback
- **AND** uses feedback to retrain ranking model

#### Scenario: High-Quality Documents Trigger Evolution
- **WHEN** document ingested with quality_score ≥0.75
- **THEN** system automatically triggers Skill evolution pipeline
- **AND** generates proposal comparing document insights to related skills
- **AND** surfaces proposal to relevant skill owner

### Requirement: Knowledge Lifecycle & Retention
The system SHALL manage document retention, archival, and linkage to Skill evolution.

#### Scenario: Knowledge Age-Out
- **WHEN** document is older than retention window (e.g., 1 year)
- **THEN** system marks as `archived` but keeps searchable for audit
- **AND** stops using in Skill proposal generation unless explicitly referenced

#### Scenario: Link Knowledge to Skill Evolution
- **WHEN** Skill proposal is approved and applied
- **THEN** system stores lineage link: Skill version ← → Knowledge documents that influenced it
- **AND** user can later view "this Skill was updated because of these Git commits and docs"

#### Scenario: Deduplicate Knowledge
- **WHEN** same source_id ingested twice (e.g., same Git commit via webhook + manual sync)
- **THEN** system reuses existing record
- **AND** does NOT create duplicate entries
- **AND** idempotency enforced at (source_type, source_id) pair level

### Requirement: Search Integration with Skills
The system SHALL enable evolution algorithm to search knowledge base for skill improvement signals.

#### Scenario: Evolution Algorithm Searches for Skill-Related Knowledge
- **WHEN** Skill evolution job runs for skill 'analyze-sentiment'
- **THEN** algorithm searches knowledge base for related documents (via semantic similarity)
- **AND** retrieves top-10 docs with highest relevance and quality
- **AND** generates proposal if docs suggest prompt improvements

#### Scenario: Trace Skill Origin to Knowledge Source
- **WHEN** user views Skill version history
- **THEN** each version can show: source_type (manual|automated), source_knowledge_ids if automated
- **AND** user can drill into knowledge artifacts that inspired the version

## API Boundaries

| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/api/v1/knowledge` | GET | authenticated | List recent documents |
| `/api/v1/knowledge` | POST | authenticated | Create/ingest single doc |
| `/api/v1/knowledge/{id}` | GET | authenticated | Get doc details |
| `/api/v1/knowledge/{id}` | PATCH | authenticated | Provide quality feedback |
| `/api/v1/knowledge/search` | POST | authenticated | Semantic search |
| `/api/v1/knowledge/search` | GET | authenticated | Search with filters |
| `/api/v1/skill-sync/rag/ingest` | POST | agent | Bulk passive ingest |
| `/api/v1/knowledge/related-skills/{id}` | GET | authenticated | Find skills linked to doc |

## Data Model

```
KnowledgeBase:
  id: UUID
  content: text (immutable)
  content_hash: string (SHA256, enables dedup)
  embedding_vector: vector (immutable)
  source_type: enum('git_commit', 'pull_request', 'issue', 'user_session', 'experiment', 'uploaded_doc', 'custom')
  source_id: string (unique within source_type, e.g., commit SHA, PR URL)
  source_metadata: JSON (e.g., Git author, PR reviewers, issue number)
  quality_score: float [0,1] (from heuristic or user feedback)
  quality_feedback: list of {feedback_type ('like'|'dislike'), reason, user_id, timestamp}
  created_at: timestamp (immutable)
  ingested_at: timestamp (when added to system, may differ from source creation)
  state: enum('active', 'archived', 'rejected')
  retention_until: timestamp (when to archive if not referenced)

KnowledgeLineage:
  knowledge_id: UUID
  skill_id: UUID
  skill_version: string
  influence_score: float (how much this doc influenced the proposal)
  influence_type: enum('prompt_improvement', 'example_suggestion', 'edge_case_fix')
  lineage_created_at: timestamp

KnowledgeSearch:
  # Denormalized index (auto-maintained for fast search)
  id: UUID
  knowledge_id: UUID (foreign key)
  query_terms: JSON (indexed keywords for fast text search pre-filter)
  # Uses vector DB (e.g., Qdrant) for embedding similarity
```

## Integration Points

- **With Skill Platform**: Proposals reference knowledge IDs; versions link to knowledge lineage
- **With Git System**: Receives commit, PR, issue webhooks
- **With Embedding Provider**: Calls external service to vectorize documents
- **With Evolution Algorithm**: Searched by Skill evolution job; triggers proposals

## Non-Functional Requirements

- **Latency**: Semantic search <500ms for top-10 results; similarity scoring <100ms per doc
- **Storage**: Deduplication via content_hash ensures minimal storage; retention window configurable
- **Quality**: Min quality_score ≥0.5 for Skill evolution use; rejected docs (<0.2) logged but not stored
- **Consistency**: Knowledge state (active/archived) changes propagate to Skill evolution within 1 minute
