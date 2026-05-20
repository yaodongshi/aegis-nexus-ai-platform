# Team AI Platform 疯狂迭代落地计划（2026-05-20）

## 1. 目标与边界

本计划基于以下已更新文档收敛：
- `docs/ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md`
- `docs/MCP_SKILL_RAG_AGENT_EVOLUTION_PROTOCOL.md`（已加现状校正）
- `docs/AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md`（已加现状校正）
- `docs/ITERATION_PLAN.md`（已加现状校正）

核心目标：
1. 先把当前“能看不能用”的治理入口改成“可初始化、可闭环”。
2. 在不破坏现有 27/27 E2E 的前提下，连续推进 M1→M4，形成可演示的真实价值链。
3. 用事实驱动文档，避免目标态和现状混写。

非目标（本轮不做）：
- 直接替换 LiteLLM 的模型治理体系。
- 一次性上线完整多租户权限重构。

---

## 2. 当前差距（执行视角）

### G1：治理页初始化断点
- 现象：菜单有，列表空；无新增仓库入口；Team 依赖手填。
- 风险：用户无法从 UI 完成第一步，功能“名义可用、实际不可用”。

### G2：MCP 仅命名未协议化
- 现象：`/api/skill-sync/mcp/*` 是 REST CRUD。
- 风险：IDE/CLI 无法以 MCP 标准接入，无法共享上下文和工具。

### G3：平台与 LiteLLM 同步边界不清
- 现象：Skill/Agent 被误以为应出现在 LiteLLM。
- 风险：产品认知错配，导致排期偏离。

### G4：客户端接入碎片化
- 现象：只有 opencode 路径，缺 Cursor/Claude Code/Continue 标准模板。
- 风险：团队复用成本高，无法规模化分发。

---

## 3. 总体方案（四阶段）

## 阶段 A（P0，1-2 天）：可初始化治理页
目标：让用户在治理页从 0 完成 Team + Repo 初始化。

交付项：
- Team 下拉选择器（读取 `/api/v1/teams/`）
- Team 快速创建（治理页内创建）
- Git Repo 新增表单（调用 `POST /api/git-repos`）
- Repo Probe 按钮（调用 `GET /api/git-repos/{id}/probe`）
- 空态引导文案（创建 Team → 添加 Repo → Probe → Pull）

验收标准：
- 空数据库登录后，用户无需 curl 即可完成第一条 repo 配置。
- `Pull & Ingest` 可在同页完成并看到事件变化。

## 阶段 B（P1，2-3 天）：模型同步链路落地
目标：明确并打通“平台模型配置 → LiteLLM model_list”。

交付项：
- `litellm_sync` 服务层（渲染 model_list）
- `apply + reload` 执行链路
- 回滚机制（配置快照）

验收标准：
- 新增/修改 provider 与 model 后，LiteLLM 可见并可调用。

## 阶段 C（P1，3-5 天）：真实 MCP Server
目标：将“命名 MCP”升级为协议 MCP（stdio + SSE）。

交付项：
- `backend/mcp_server/` 独立服务
- Tools: `list_skills`, `get_skill_prompt`, `search_rag`, `report_task_run`
- Resources: `skill://`, `rag://`
- Stack-aware 过滤（`pyproject.toml`/`package.json`/`go.mod`/`Cargo.toml`/`__manifest__.py`）

验收标准：
- Cursor/Claude Code 可直接看到并调用工具。
- 同一仓库在不同技术栈下返回不同 skill 子集。

## 阶段 D（P2，2 天）：客户端配置生成器
目标：降低团队接入成本，支持一键初始化。

交付项：
- `/api/v1/runtime/client-config/cursor`
- `/api/v1/runtime/client-config/claude-code`
- `/api/v1/runtime/client-config/continue`
- CLI `aegis init`

验收标准：
- 新成员 5 分钟内完成本地 IDE 绑定。

---

## 4. 执行任务分解（可直接跟踪）

## A. 前端治理可用性修复（进行中）
- [x] A1. 新增 `learningApi.createRepo()`
- [x] A2. 新增 `learningApi.probeRepo()`
- [x] A3. 治理页增加 Team 下拉与 Team 创建
- [x] A4. 治理页增加 Repo 新增表单
- [x] A5. 治理页增加 Repo Probe 操作
- [x] A6. 治理页空态引导文案
- [x] A7. 前端构建与页面回归

## B. 模型同步（待启动）
- [x] B1. 新建 `backend/app/services/litellm_sync.py`（`store.py` 同步入口已委托 service）
- [x] B2. 增加配置渲染与热加载调用（`scripts/apply_litellm_gateway.sh` 已支持 `apply + /api/providers/sync-gateway`）
- [x] B3. 增加失败回滚与审计日志（`backend/app/store.py` 已实现配置文件回滚 + gateway sync best-effort rollback + `litellm/runtime_sync_audit.jsonl` 审计）
- [x] B4. 加入 E2E 脚本断言（`scripts/e2e_full_business_pipeline.sh` Stage 13：sync-gateway + audit log）

## C. MCP Server（待启动）
- [x] C1. 新增 `backend/mcp_server/` 框架（stdio + JSON-RPC skeleton）
- [ ] C2. 实现 tools/resources 基础原语
- [ ] C3. 实现 stack detection + 标签过滤
- [ ] C4. 接入 docker-compose 服务编排
- [ ] C5. 增加最小联调脚本

## D. 客户端配置生成（待启动）
- [ ] D1. Cursor 配置模板
- [ ] D2. Claude Code 配置模板
- [ ] D3. Continue 配置模板
- [ ] D4. CLI 初始化命令

## E. Vector Store Management（进行中）
- [x] E1. 增加向量库配置样例（`config/vector_store.example.yaml`）
- [x] E2. 增加向量库管理脚本（`scripts/vector_store_management.sh`，覆盖 create/manage/test）
- [x] E3. 增加闭环运行手册（`docs/LITELLM_RAG_VECTOR_STORE_RUNBOOK.md`）
- [x] E4. 将向量库烟测加入 `e2e_full_business_pipeline.sh`

---

## 5. 风险与控制

1. 团队接口为空导致流程中断
- 控制：治理页内创建 Team，避免跨页面依赖。

2. 容器路径配置错误导致 Probe 失败
- 控制：UI 中提示容器路径示例，Probe 前置校验。

3. 文档与实现再次漂移
- 控制：每次迭代提交必须同步更新状态段（What is implemented / What is planned）。

---

## 6. 本轮“疯狂迭代”执行记录（2026-05-20）

已开始执行：阶段 A（P0）
- 已完成 API 扩展：repo create/probe
- 已完成治理页功能增强：Team + Repo 初始化能力
- 已完成前端构建校验并发布

继续迭代（阶段 B 入口强化）：
- 已落地 B1：新增 `backend/app/services/litellm_sync.py`，并将 `store.py` 中 LiteLLM 预览/渲染/自动同步/网关同步入口改为 service 委托。
- 已升级 `scripts/apply_litellm_gateway.sh`：从“仅写配置+重启”升级为“写配置+模型同步（/api/providers/sync-gateway）+健康检查”。
- 新增 `sync` 模式，可单独执行网关模型差量同步。
- 已落地 B3：同步失败时执行配置文件回滚，并将同步/失败/回滚结果写入 `litellm/runtime_sync_audit.jsonl`。
- 已落地 B4：E2E 脚本新增 Stage 13，断言网关同步成功、审计文件存在、并包含 `gateway_model_sync` 行为记录。

继续迭代（阶段 E 向量库闭环）：
- 已交付向量库配置样例 `config/vector_store.example.yaml`。
- 已交付向量库管理脚本 `scripts/vector_store_management.sh`（create/list/stats/delete/upsert/search/test）。
- 已交付运行手册 `docs/LITELLM_RAG_VECTOR_STORE_RUNBOOK.md`，覆盖 Create/Manage/Test 三类流程。
- 已将向量库烟测接入 `scripts/e2e_full_business_pipeline.sh`（Stage 12：create/upsert/search/stats 断言）。

继续迭代（阶段 C MCP 启动）：
- 已落地 C1：新增 `backend/mcp_server/` 骨架（`main.py` / `server.py` / `README.md`），支持 stdio + JSON-RPC 初始化与最小工具调用。
- 新增 `scripts/test_mcp_server_smoke.sh` 作为最小协议烟测脚本，验证 `initialize`、`tools/list`、`tools/call(health.ping)`。

---

## 7. 验证与发布命令

在项目根目录使用当前虚拟环境：

```bash
source /Users/yaodongshi/Documents/develop/odoo/odoo19ee/.venv/bin/activate
cd /Users/yaodongshi/Documents/develop/odoo/odoo19ee/team_ai_platform/frontend
npm run build
```

若需端到端验证：

```bash
cd /Users/yaodongshi/Documents/develop/odoo/odoo19ee/team_ai_platform
./scripts/e2e_full_business_pipeline.sh
```
