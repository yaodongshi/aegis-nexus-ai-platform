## Context
目标是把本地 CLI 产生的技能与知识，在最小打扰的情况下持续同步到平台，并通过 RAG 与治理流程实现可控的自我迭代。

## Goals / Non-Goals
- Goals:
  - Git Hook 或等效机制自动提交本地 skill 到团队仓库
  - 平台自动拉取并发布最新 skill 版本
  - 工作流副产物无感进入 RAG（代码变更、PR、故障复盘、命令会话）
  - RAG 触发可解释的 skill 提案并进入审批
- Non-Goals:
  - 不在首期实现全自动无审批上线
  - 不在首期支持所有 IDE/CLI 的深度插件化

## Architecture
1. Local Capture Layer
- Pre-commit / post-commit hooks:
  - 提取 `.claude/skills/**`、`.opencode/skills/**`、平台导出目录中的 skill 变更
  - 生成 `skill-change.json`（skill_id, target, hash, author, timestamp, commit_ref）
- CLI fallback watcher:
  - 无 Git hook 权限场景，使用文件系统 watcher + 定时 push

2. GitOps Sync Layer
- Upstream push path:
  - 本地 hook 触发 `git add/commit/push` 到 skill repo
  - commit message 规范：`skill(sync): <skill_id> <target> <hash>`
- Platform pull path:
  - Webhook 或轮询触发平台 ingest
  - 校验签名 + 幂等键（repo+commit+path hash）
  - 生成版本化 skill artifact（带 protocol_version）
- Conflict strategy:
  - same-skill same-version: no-op
  - same-skill different-content: create conflict proposal, require review

3. Passive RAG Ingestion Layer
- Sources:
  - Git commits/PR descriptions/review comments
  - CI logs、runbook、incident notes
  - task-runs / skill-updates 历史记录
- Pipeline:
  - parser -> chunker -> embed -> index -> quality score
- Quality gates:
  - 去噪（boilerplate/filter）
  - 置信度阈值和重复度阈值
  - 所有知识条目保留 source trace

4. Skill Evolution Layer
- Trigger:
  - RAG topic drift, repeated failure cluster, high-frequency workaround
- Output:
  - draft skill update（变更理由、样例、回滚策略）
- Safety:
  - policy gate + human approval
  - canary users/team rollout

5. Governance and Observability
- Metrics:
  - sync success rate, ingest latency, proposal acceptance rate, regression ratio
- Audit:
  - 谁触发、何时触发、对应 commit/source、审批链
- Rollback:
  - 一键回滚到上一稳定 skill 版本

## API and Contract Sketch
- `POST /api/skill-sync/hooks/report`
  - 接收 hook 事件（repo, branch, commit, changed_files）
- `POST /api/skill-sync/repos/{repo_id}/pull`
  - 手动或计划任务拉取最新 skill
- `POST /api/rag/ingest/events`
  - 通用知识摄取入口（支持 source_type）
- `POST /api/skill-updates/{id}/promote`
  - 将已验证提案升格为候选发布

## Rollout Plan
- Phase A (1-2 周):
  - Hook 模板 + Git push/pull 最小闭环 + 手工审批
- Phase B (2-4 周):
  - Passive RAG ingest + 主题质量评分 + 提案自动草拟
- Phase C (4-8 周):
  - Canary rollout + 自动回滚 + 策略化自进化

## Risks / Trade-offs
- 风险: 噪声知识污染 RAG
  - 缓解: source whitelist + score threshold + periodic pruning
- 风险: 自动提案误导 skill
  - 缓解: approval gate + regression test on golden tasks
- 风险: 多仓库分支冲突
  - 缓解: repo-level namespace + deterministic merge strategy

## Migration
- 保持已有 learning loop API 可用
- 新增 GitOps/RAG 端点与作业器，不破坏既有客户端
