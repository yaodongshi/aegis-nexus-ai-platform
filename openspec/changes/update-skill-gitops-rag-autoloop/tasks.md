## 1. Planning and Spec
- [ ] 1.1 Confirm repository and branch strategy for skill artifacts.
- [x] 1.2 Confirm required hook templates for Claude/OpenCode clients.
- [ ] 1.3 Approve API contracts for hook report, repo pull, and rag ingest.

## 2. Backend Implementation
- [x] 2.1 Add hook event ingestion endpoint with signature and idempotency checks.
- [x] 2.2 Add Git repo pull worker and commit parser for skill artifacts.
- [x] 2.3 Add passive RAG ingestion endpoint and source adapters.
- [ ] 2.4 Add evolution proposal generator from RAG quality signals.
- [ ] 2.5 Add policy/approval gate and rollback hooks for promoted skills.

## 3. Frontend and CLI
- [x] 3.1 Add sync dashboard for repo status and last hook events.
- [ ] 3.2 Add proposal review UI with source evidence and diff preview.
- [x] 3.3 Provide CLI hook bootstrap scripts and local watcher fallback.

## 4. Validation
- [x] 4.1 Add unit/integration tests for hook ingest, pull sync, and conflict flow.
- [ ] 4.2 Add E2E test for passive RAG -> proposal -> apply pipeline.
- [ ] 4.3 Run load test for ingestion and retrieval latency SLO.
- [x] 4.4 Run security checks for webhook signature and secret rotation.
