# Harness Runtime 迁移与发布 Runbook（2026-06-02）

更新日期：2026-06-02  
适用范围：Team AI Platform 控制面接入可插拔 Harness Runtime（local-graph/noop）

## 1. 目标与边界

本 Runbook 用于完成从“仅控制面计划管理”到“控制面 + Harness Runtime 执行链路”的迁移发布，覆盖：
- capability contract（runtime_adapter、rollout metadata）
- plan create/run/event/replay 全链路
- rollout promote/rollback 治理审计
- metrics/alerts 基线采样与回归验证

不包含：
- LiteLLM 提供商新增接入流程
- Qdrant collection 初始化流程

## 2. 版本与产物

- OpenSpec 变更：`add-extensible-harness-runtime-architecture`
- 关键代码路径：
  - `backend/app/harness/`
  - `backend/app/routers/harness.py`
- 自动化脚本：
  - `scripts/harness_pilot_baseline_run.sh`
  - `scripts/harness_e2e_acceptance_run.sh`
  - `scripts/harness_rollback_drill_run.sh`
- 证据报告目录：`reports/`

## 3. 发布前检查

1. 环境与容器

```bash
cd team_ai_platform
bash scripts/dev_build_and_up.sh --skip-tests --skip-frontend-build
bash scripts/healthcheck.sh
```

2. API 可达性

```bash
curl -sS -o /tmp/runtime_health.json -w "%{http_code}\n" http://localhost:3000/api/platform/runtime-health
```

期望：返回 `200` 或 `401`（若开启 admin token 校验）。

3. Admin Token 就绪

- 通过 `.env` 提供 `TEAM_AI_PLATFORM_ADMIN_TOKEN`，或
- 从 backend 容器环境读取同名变量后注入脚本运行。

## 4. 迁移执行步骤

### Step A：能力基线采样（Task 5.4）

```bash
cd team_ai_platform
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_pilot_baseline_run.sh
```

产物：
- `reports/harness_pilot_baseline_latest.md`
- `reports/harness_pilot_baseline_<date>.md`

### Step B：端到端验收（Task 6.2）

```bash
cd team_ai_platform
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_e2e_acceptance_run.sh
```

验收链路：
- create plan -> run -> complete
- trace fetch -> replay
- canary/promote/rollback -> audit

产物：
- `reports/harness_e2e_acceptance_latest.md`
- `reports/harness_e2e_acceptance_<date>.md`

### Step C：回滚演练（Task 6.3）

```bash
cd team_ai_platform
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_rollback_drill_run.sh
```

演练链路：
- 注入 canary
- 执行 rollout rollback
- 触发 plan rollback terminal event
- 校验 trace/audit/metrics

产物：
- `reports/harness_rollback_drill_latest.md`
- `reports/harness_rollback_drill_<date>.md`

## 5. 验收标准（DoD）

- `reports/` 中至少存在一套最新与日期固化报告。
- E2E 报告中 flow 检查全部 `passed`。
- Rollback Drill 报告中以下项为 `passed`：
  - `contract_restored_after_rollback`
  - `plan_rollback_terminal_state`
  - `audit_contains_rollback_decision`
- OpenSpec 严格校验通过：

```bash
cd team_ai_platform
openspec validate add-extensible-harness-runtime-architecture --strict
```

## 6. 常见故障与处理

1. `502 Bad Gateway`（`/api/*`）
- 现象：frontend 到 backend 反代临时失联。
- 处理：

```bash
cd team_ai_platform
docker compose restart frontend
```

2. `Invalid admin token` / `401`
- 现象：harness API 受保护。
- 处理：确认脚本传入 `TEAM_AI_PLATFORM_ADMIN_TOKEN`。

3. `trace_id mismatch for plan`（`409`）
- 现象：`POST /plans/{plan_id}/events` 未带匹配 trace id。
- 处理：请求头设置 `X-Trace-Id=<plan.trace_id>`。

## 7. 回滚策略

若发布后发现执行面异常，按以下顺序处理：
1. 将 capability contract 的 `runtime_adapter` 回退为 `noop`。
2. 对异常 canary 执行 rollout `rollback`，清空 canary 策略与流量。
3. 保留 `reports/` 与 rollout decisions 作为审计证据。
4. 重新执行 Step B 和 Step C 验证恢复状态。

## 8. 交付清单

- 代码：Harness Runtime adapter + router + plan lock + replay + rollout audit
- 脚本：baseline/e2e/rollback drill 三个自动化入口
- 证据：`reports/` 下最新报告与日期固化报告
- 规范：OpenSpec tasks 勾选状态 + strict validate 通过
