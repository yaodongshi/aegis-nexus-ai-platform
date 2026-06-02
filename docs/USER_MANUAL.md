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

## 3.1 小白 30 分钟上手（先看这节）

这节只做两件事：
1. 让团队成员拿到可用 Key。
2. 让平台开始“自动进化”（通过任务复盘生成技能提案）。

### Step 1：启动平台

```bash
cd team_ai_platform
bash scripts/start.sh
bash scripts/healthcheck.sh
```

看到健康检查通过再继续。

### Step 2：管理员登录后台

1. 浏览器打开：`http://localhost:3000`。
2. 自动跳转/进入管理后台：`/admin`。
3. 输入管理员 Token：`.env` 里的 `TEAM_AI_PLATFORM_ADMIN_TOKEN`。

### Step 3：先接一个可用模型供应商

1. 打开“供应商管理”页签。
2. 填写 `名称 / 类型 / 端点 / API Key`。
3. 点击“新增供应商”。
4. 点击“同步网关列表”。

目标：确保后面发出去的 Key 能真的调用模型。

### Step 4：给团队成员发 Key

1. 打开“Key 管理”页签。
2. 在“生成虚拟 Key”填写：
- 标签：例如“张三开发 Key”
- 成员标识：例如 `u_zhangsan`
- 项目标识：例如 `p_ai_platform`
- 权限范围：`project:*`
- 有效天数：例如 `30`
3. 点击“生成 Key”。
4. 复制系统弹出的 `key_secret` 发给对应成员。

注意：`key_secret` 只在创建时展示一次，务必当场保存。

### Step 5：成员侧接入（复制即用）

成员在自己终端设置：

```bash
export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=<管理员发的key_secret>
```

用下面命令验证 Key 可用：

```bash
curl -sS http://localhost:8000/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

如果返回模型列表，说明团队已经“可用”。

### Step 6：开启自动进化（最小闭环）

1. 管理后台打开“闭环学习”页签。
2. 在“任务复盘上报”填写一次真实任务（标题、总结、错误模式、经验）。
3. 点击“上报并生成提案”。
4. 在右侧“技能更新提案”查看新增提案。
5. 按提案内容更新团队 Skill（先小范围验证，再推广）。

做到这一步，就完成了“人做任务 -> 平台沉淀经验 -> 形成可复用能力”的自动进化起点。

### Step 7：每天只做 3 件事

1. 看平台总览是否健康。
2. 看 Key 用量与异常状态。
3. 上报至少 1 条任务复盘，持续生成提案。

## 3.2 小白版一键流程（脚本）

如果你不想逐页操作，可先用脚本跑通平台能力：

```bash
# 1) 基线采样（确认 capability 可运行）
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_pilot_baseline_run.sh

# 2) 端到端验收（create/run/replay/rollout）
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_e2e_acceptance_run.sh

# 3) 回滚演练（可止损）
TEAM_AI_PLATFORM_ADMIN_TOKEN="<token>" bash scripts/harness_rollback_drill_run.sh
```

报告会生成在 `reports/` 目录，直接用于团队汇报。

## 3.3 自动进化（最后人工审批）

如果你希望“程序自动流转，人工只做最后审批”，请按如下配置：

```bash
cd team_ai_platform
nohup scripts/evolution_auto_workflow.sh > /tmp/evolution_auto_workflow.log 2>&1 &
```

该流程会自动：
1. 扫描 `draft` skill updates。
2. 自动提交审批单（pending）。
3. 对“已批准”的审批单自动执行 apply 生效。

你只需要做最后一步：审批同意。

配套文档：
- `docs/AUTO_EVOLUTION_LAST_APPROVAL_GUIDE.md`
- `docs/FULL_IDIOT_PROOF_SETUP_AND_OPERATION.md`

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

### 6.4 代码仓地址在哪里（闭环学习）

先区分两类代码仓：

1. 平台主仓（你当前项目本身）
- 远端地址可用命令查看：

```bash
cd team_ai_platform
git remote -v
```

2. 闭环学习绑定仓（用于 Skill 提案同步）
- 这不是固定内置地址。
- 平台使用你在“闭环学习 -> Git 代码仓绑定”里配置的仓路径和分支。
- 当前生效的是“当前绑定仓（active）”。

查看当前绑定仓：

```bash
# 需要管理员 Token
curl -sS "http://localhost:3000/api/git-repos/active" \
  -H "X-Admin-Token: $TEAM_AI_PLATFORM_ADMIN_TOKEN"
```

查看全部绑定仓：

```bash
curl -sS "http://localhost:3000/api/git-repos?limit=20&offset=0" \
  -H "X-Admin-Token: $TEAM_AI_PLATFORM_ADMIN_TOKEN"
```

### 6.5 如何看到绑定仓里面的内容

情况 A：绑定的是你本机可访问目录
- 直接用文件浏览器或 IDE 打开该路径。

情况 B：绑定的是容器内路径（例如 /app/...）
- 需要进入容器查看：

```bash
docker exec -it team-ai-backend sh
cd <active_repo_path>
ls -la
git remote -v
```

### 6.6 为什么感觉“没有内置地址”

这是设计如此：
- 平台只维护“绑定关系”（name/path/branch/active），不强制写死一个全局仓地址。
- 目的是让每个团队按自己的仓库规范接入。

如果你希望统一地址，做法是：
1. 在“Git 代码仓绑定”只保留 1 个标准仓。
2. 将其设为 active。
3. 其他仓全部删除或禁用。

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
