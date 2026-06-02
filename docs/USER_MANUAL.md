# Team AI Platform 用户手册（迭代主文档）

更新日期：2026-06-02  
文档定位：唯一用户手册主文档，后续所有用户操作说明在本文件持续迭代。

## 1. 手册范围

本手册覆盖：
- 平台部署与启动
- 管理员配置
- 业务用户日常使用
- Harness Runtime 验收与回滚演练
- 故障排查与运维检查

不覆盖：
- 源码级开发规范（见开发规范文档）
- 供应商私有模型接入细节

## 2. 用户角色

1. 平台管理员
- 负责环境变量、服务启动、网关同步、发布验收。

2. 运营/产品用户
- 负责功能验收、指标观察、流程回传。

3. 技术支持
- 负责故障定位、日志排查、回滚执行。

## 3. 系统入口

1. 前端入口
- `http://localhost:3000`

2. 后端 API 与文档
- `http://localhost:8000`
- `http://localhost:8000/docs`

3. Open WebUI
- `http://localhost:9000`

4. 数据面接口
- OpenAI 兼容路径：`/v1/*`

5. 控制面接口
- 平台控制路径：`/api/v1/*`

## 4. 快速开始（首次）

1. 进入项目

```bash
cd team_ai_platform
```

2. 启动服务

```bash
bash scripts/start.sh
```

3. 健康检查

```bash
bash scripts/healthcheck.sh
```

4. 校验网关配置

```bash
bash scripts/apply_litellm_gateway.sh check
```

## 5. 环境变量

最小必要变量：
- `LITELLM_MASTER_KEY`
- `LITELLM_SALT_KEY`
- `TEAM_AI_PLATFORM_ADMIN_TOKEN`
- `OPENAI_API_KEY`（使用 OpenAI 时）
- `LITELLM_INTERNAL_BASE_URL`

说明：
- `.env` 仅本地使用，不提交。
- 生产环境建议使用密钥管理服务，不直接明文落盘。

## 6. 日常操作流程

### 6.1 平台可用性检查

```bash
bash scripts/healthcheck.sh
curl -sS http://localhost:3000/api/platform/runtime-health
```

检查项：
- 容器均为 running/healthy
- runtime-health 返回可用状态（200 或受鉴权保护的 401）

### 6.2 模型与能力别名检查

目标：确认业务始终调用能力别名，而不是具体模型名。

推荐别名：
- `chat-default`
- `embed-default`
- `reasoning-default`

### 6.3 RAG 基本闭环

目标：验证 ingest -> embedding -> retrieval -> evolution 路径。

建议顺序：
1. 导入样本知识
2. 触发检索
3. 查看检索结果质量
4. 观察性能与日志

## 7. Harness Runtime 使用与验收

### 7.1 基线采样

```bash
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_pilot_baseline_run.sh
```

输出报告：
- `reports/harness_pilot_baseline_latest.md`

### 7.2 端到端验收

```bash
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_e2e_acceptance_run.sh
```

输出报告：
- `reports/harness_e2e_acceptance_latest.md`

### 7.3 回滚演练

```bash
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_rollback_drill_run.sh
```

输出报告：
- `reports/harness_rollback_drill_latest.md`

### 7.4 严格规范校验

```bash
openspec validate add-extensible-harness-runtime-architecture --strict
```

## 8. 用户侧操作规范

1. 一律使用能力别名调用，不写死供应商模型名。
2. 验收报告必须保存 latest 和日期固化两个版本。
3. 发生异常优先执行可回滚动作，后做根因定位。
4. 提测必须附：版本号、提交号、环境、用例、回滚方案。

## 9. 常见问题

### 9.1 访问 `/api/*` 返回 502

处理：

```bash
docker compose restart frontend
```

### 9.2 调用返回 Invalid admin token

处理：
- 校验 `TEAM_AI_PLATFORM_ADMIN_TOKEN` 是否与 backend 一致。

### 9.3 事件注入返回 trace_id mismatch for plan

处理：
- 调用 `POST /api/v1/harness/plans/{plan_id}/events` 时，附带 `X-Trace-Id=<plan.trace_id>`。

### 9.4 `/v1/models` 返回 401

说明：
- 未带 key 返回 401 是预期行为。

### 9.5 报告里 success_rate 异常偏低

处理：
- 检查 plan 是否停留在非终态。
- 检查是否正确注入 complete/rollback 终态事件。

## 10. 运维检查清单

每日：
1. 服务健康检查
2. runtime-health 检查
3. 最近一次验收报告状态检查
4. 错误日志与告警检查

每周：
1. 回滚演练复盘
2. 指标趋势复盘（success_rate/latency/cost/rollback_rate）
3. 文档与脚本版本同步检查

## 11. 升级与回滚指南

### 升级前
1. 备份关键配置
2. 执行健康检查
3. 记录当前 commit 与镜像信息

### 升级后
1. 执行 e2e 验收脚本
2. 执行 rollback drill 脚本
3. 归档本次报告

### 失败回滚
1. 将 runtime adapter 切回 `noop`
2. 对 canary 执行 rollback
3. 复测 e2e 与 rollback drill

## 12. 变更记录（手册迭代）

- 2026-06-02 v1.0
  - 初版建立：整合启动、验收、回滚、排障、运维清单。

---

维护规则：
- 新增用户操作必须更新本手册，不再新增平行 user-guide 文档。
- 历史说明优先以“版本变更记录”方式附在本手册末尾。
