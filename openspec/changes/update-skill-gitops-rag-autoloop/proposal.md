# Change: Build GitOps + Passive RAG + Skill Auto-Loop

## Why
当前技能平台已经具备基础 CRUD、导出和 learning-loop 能力，但还未形成“开发行为自动沉淀知识、知识反哺技能、技能再反哺 CLI”的闭环。团队需要低感知接入，避免额外操作成本。

## What Changes
- Add Git hooks and watcher integration contract for local CLI skill update capture.
- Add bidirectional sync between platform skills and Git repositories with conflict strategy.
- Add passive RAG ingestion pipeline from commit/PR/issue/session artifacts.
- Add skill evolution pipeline that proposes prompt updates from validated RAG signals.
- Add governance controls (approval, policy, rollback, observability) for automatic evolution.
- Define phased rollout and SLOs to reduce operational and model risks.

## Impact
- Affected specs: `skill-gitops-rag-autoloop`
- Affected code:
  - backend: `app/routers/learning.py`, `app/routers/skills.py`, `app/store.py`, new workers/pipeline modules
  - frontend: skills detail/list and governance pages for sync/evolution operations
  - tooling: CLI hook templates, repo sync scripts, ingestion adapters
- External dependencies:
  - Git repository access token or deploy key
  - Optional queue/worker runtime for async processing
  - Vector DB / embedding provider stability
