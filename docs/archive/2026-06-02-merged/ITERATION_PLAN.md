# Team AI Platform — 迭代计划与现状对比

> 对齐声明（2026-05-19）：本文档保留用于历史差距分析，当前路线图以 `AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md` 的 Phase A/B/C 为准。
>
> ⚠️ **现状校正（2026-05-20）**：本计划中"客户端配置生成 30%"、"MCP 0%"、"Skill→LiteLLM 同步"等条目的真实完成度，以及 M1–M5 落地路线图，请以 [`ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md`](./ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md) 为准。

**版本**: v1.0  
**日期**: 2026-05-16  
**状态**: 历史参考（非当前主基线）

---

## 1. 现状全量盘点（基于代码扫描）

### 1.1 基础设施状态

| 组件 | 配置状态 | 运行状态 | 说明 |
|------|---------|---------|------|
| PostgreSQL (litellm_db) | ✅ DSN 已配置 | ✅ 运行中 (healthy) | 供 LiteLLM + 平台共用 |
| LiteLLM :4000 | ✅ 已连接 | ✅ 运行中 | config.yaml 仅含 master_key |
| Qdrant :6333 | ✅ URL 已配置 | ✅ 运行中 | 客户端已初始化 |
| Embedding 模型 | ⚠️ `text-embedding-v3` 配置但未在 LiteLLM 注册 | ❌ 不可用 | `embedding_available: false` |

### 1.2 后端模块现状矩阵

| 模块 | 文件 | 数据存储 | 功能完整度 | 缺口 |
|------|------|---------|-----------|------|
| 供应商管理 | `routers/providers.py` | PostgreSQL ✅ | **85%** | 模型发现后未自动注册到平台 model 表 |
| 供应商 → LiteLLM 同步 | `store._sync_providers_to_litellm_config()` | — | **90%** | `/model/new` 调用有，但 model_alias 未关联 user 配额 |
| 虚拟 Key (platform) | `routers/keys.py` + `store.issue_key()` | PostgreSQL ✅ | **40%** | ❌ 未调用 LiteLLM `/key/generate`，发出的 key 不可用 |
| 虚拟 Key (LiteLLM) | — | LiteLLM DB | **0%** | LiteLLM 完全不知道我们的 key |
| Skill CRUD | `routers/skills.py` | PostgreSQL ✅ | **90%** | 缺版本号字段、无 diff 视图 |
| Skill 向量化 | `store.create_skill()` → Qdrant | Qdrant (warming) | **50%** | Embedding 模型未在 LiteLLM 注册 → 失败 |
| Skill 语义搜索 | `store.search_skills()` | Qdrant / 词汇 | **60%** | Qdrant 可用时向量搜索，否则降级词汇；Qdrant 不可用 |
| Skill 更新提案 | `routers/learning.py` | PostgreSQL ✅ | **70%** | 缺 ApprovalRecord 联动、缺 re-embedding on apply |
| Git 仓库管理 | `routers/learning.py` (git-repos) | PostgreSQL ✅ | **70%** | 有 probe/activate，缺 webhook 接收端点 |
| 技能审批 | `routers/approvals.py` | PostgreSQL ✅ | **30%** | 仅 submit/list/get，缺 approve/reject 动作端点 |
| 知识库存储 | `api/v1/knowledge.py` | ❌ 内存字典 | **20%** | 重启数据全丢，无 embedding，无 RAG |
| Knowledge 向量化 | — | — | **0%** | 完全未实现 |
| RAG 注入中间件 | `openai_compat.py` | — | **10%** | 仅支持显式 skill_id 注入，无自动 RAG 搜索 |
| /v1/models 透明化 | `openai_compat.py` | — | **0%** | 未代理 `/v1/models` 到 LiteLLM |
| 客户端配置生成 | `store.build_client_runtime_config()` | — | **30%** | 仅支持 opencode，未支持 Claude Code/Continue/Cursor |
| 会话记录 | `routers/sessions.py` | PostgreSQL ✅ | **70%** | 缺 injected_skill_ids 字段记录 RAG 注入详情 |
| 治理策略 | `routers/policies.py` | PostgreSQL ✅ | **80%** | 基本完整 |
| 平台概览 | `routers/platform.py` | — | **80%** | 基本完整 |

### 1.3 前端模块现状

| 页面 | 路由 | 状态 | 说明 |
|------|------|------|------|
| 控制台 | `/` | ✅ 完整 | 含平台健康卡片 |
| 团队/项目/仓库 | `/teams` `/projects` `/repos` | ✅ 完整 | |
| 智能体/任务 | `/agents` `/tasks` | ✅ 完整 | |
| 知识库+技能库 | `/knowledge` | ✅ UI 完整 | 后端 knowledge 未持久化 |
| 插件/观测 | `/plugins` `/observe` | ✅ 完整 | |
| 设置 | `/settings` | ✅ 含运行时配置 Tab | |
| 虚拟密钥 | `/keys` | ✅ UI 完整 | 发出的 key 实际不可用 |
| 模型注册 | `/models` | ✅ UI 完整 | |
| AI 服务商 | `/providers` | ✅ UI 完整 | |
| 治理中心 | `/governance` | ✅ UI 完整 | approve 端点缺失 |

---

## 2. 目标 vs 现状差距总表

| 目标功能 | 目标状态 | 现状 | Gap |
|---------|---------|------|-----|
| LLM 供应商 → LiteLLM 同步 | 实时热同步 | 95% 实现 | 细节优化 |
| 虚拟 Key → LiteLLM 桥接 | Key 在 LiteLLM 中真实存在 | **0%** | ❌ 核心缺口 |
| 开发者拿 key 直接可用 | 拿到 key 立刻接入 | **0%** | ❌ 阻塞所有下游 |
| /v1/models 返回完整模型列表 | 与直连原厂一致 | **0%** | ❌ 缺口 |
| Skill 向量化入 Qdrant | 创建即向量化 | 50% (embedding 配错) | ⚠️ 需修配置 |
| Knowledge 向量化 | 上传即分块+向量化 | **0%** | ❌ 完全缺失 |
| RAG 自动注入 | 每次对话自动注入 | **10%** | ❌ 需实现 |
| 技能更新审批闭环 | draft→审批→apply→re-embed | 70% | ⚠️ 缺最后链接 |
| Git webhook 接收 | 接收 PR merge 事件 | **0%** | ❌ 完全缺失 |
| Approve/Reject 端点 | 管理员一键审批 | **0%** | ❌ 缺失 |
| Claude Code 配置生成 | 一键生成配置文件 | **0%** | ❌ 缺失 |
| Continue.dev 配置生成 | 一键生成配置文件 | **0%** | ❌ 缺失 |
| Cursor 配置生成 | 一键生成配置文件 | **0%** | ❌ 缺失 |
| Knowledge 持久化到 DB | 重启不丢数据 | **0%** (内存字典) | ❌ 严重 |

---

## 3. 迭代计划（共 4 次迭代）

```
当前状态                    Sprint 1        Sprint 2        Sprint 3        Sprint 4
────────────────────────────────────────────────────────────────────────────────
Key 发出但不可用    ──────→  Key 桥接 LiteLLM → 开发者可用 ──→ 审批闭环完整 → 全量生产就绪
Knowledge 内存字典  ──────→  DB 持久化       → RAG 向量化  ──→ 自动注入      → 性能优化
RAG 不工作         ──────→  Embedding 激活  → Knowledge+  ──→ 全量 RAG 注入  → 智能路由
Skill 无自动更新    ──────→  审批端点         → Git webhook ──→ 闭环完整       → 版本历史
配置生成仅 opencode ──────→  Claude Code 支持 → Continue.dev → Cursor/通用    → 企业版特性
```

---

## 4. Sprint 1 — 地基打通（预计 3 天）

**目标**：开发者拿到虚拟 Key 后立刻可以使用，Embedding 服务激活

### Sprint 1 任务清单

| # | 任务 | 文件 | 类型 |
|---|------|------|------|
| 1.1 | 在 LiteLLM 中注册 embedding 模型（`text-embedding-3-small`） | `litellm/config.yaml` | 配置 |
| 1.2 | `issue_key()` 调用 LiteLLM `/key/generate`，返回真实 sk-key | `store.py` | 后端 |
| 1.3 | `revoke_key()` 调用 LiteLLM `/key/delete` | `store.py` | 后端 |
| 1.4 | `KeyRecord` 新增 `litellm_key_id` 字段，PostgreSQL 表迁移 | `schemas.py` + `store.py` | 后端 |
| 1.5 | `/v1/models` 端点代理到 LiteLLM 并返回完整列表 | `openai_compat.py` | 后端 |
| 1.6 | `build_client_runtime_config()` 新增 Claude Code 模板 | `store.py` | 后端 |
| 1.7 | `build_client_runtime_config()` 新增 Continue.dev 模板 | `store.py` | 后端 |
| 1.8 | `build_client_runtime_config()` 新增 Cursor 模板 | `store.py` | 后端 |
| 1.9 | 前端"设置 → 运行时配置"新增 4 个工具的配置复制按钮 | `pages/settings/index.tsx` | 前端 |
| 1.10 | Docker 重新 build 并验证 | `docker-compose.yml` | 部署 |

**Sprint 1 验收标准**：
- `curl http://localhost:8000/api/skills/search-status` 返回 `embedding_available: true`
- 通过 `/api/keys/issue` 发放的 key 能直接在 `claude` CLI 使用
- `GET http://localhost:8000/v1/models` 返回完整模型列表
- opencode / Claude Code / Continue.dev / Cursor 配置可一键复制

---

## 5. Sprint 2 — RAG 激活（预计 4 天）

**目标**：知识库持久化+向量化，Skill RAG 全面可用

### Sprint 2 任务清单

| # | 任务 | 文件 | 类型 |
|---|------|------|------|
| 2.1 | `api/v1/knowledge.py` 从内存字典改为 PostgreSQL 持久化 | `knowledge.py` + `store.py` | 后端 |
| 2.2 | `store.py` 新增 `knowledge_collection` Qdrant 集合 | `store.py` | 后端 |
| 2.3 | 知识文档上传时触发分块（chunk_size=512, overlap=64） | `store.py` | 后端 |
| 2.4 | 分块后调用 LiteLLM `/v1/embeddings` 向量化 | `store.py` | 后端 |
| 2.5 | 向量存入 Qdrant `knowledge_collection` | `store.py` | 后端 |
| 2.6 | `KnowledgeRecord` 新增 `qdrant_chunk_ids` 字段 | `schemas.py` | 后端 |
| 2.7 | 新增 `GET /api/v1/knowledge/search?query=xxx` 端点 | `knowledge.py` | 后端 |
| 2.8 | `openai_compat.py` 实现 Skill 自动 RAG 注入逻辑 | `openai_compat.py` | 后端 |
| 2.9 | `openai_compat.py` 新增 Knowledge RAG 注入（并行搜索） | `openai_compat.py` | 后端 |
| 2.10 | `SessionRecord` 新增 `injected_skill_ids` + `injected_knowledge_ids` 字段 | `schemas.py` + `store.py` | 后端 |
| 2.11 | `openai_compat.py` 注入后异步记录 SessionRecord | `openai_compat.py` | 后端 |
| 2.12 | 前端知识库页面新增 RAG 状态指示器 | `pages/knowledge/index.tsx` | 前端 |
| 2.13 | 前端观测页 AI 会话 tab 显示注入的 Skill/Knowledge 列表 | `pages/observe/index.tsx` | 前端 |
| 2.14 | Docker 重新 build 并验证 RAG 效果 | — | 部署 |

**Sprint 2 验收标准**：
- 上传知识文档后 `knowledge_collection` 有向量数据
- 通过 Claude Code 提问时，后台日志显示 RAG 注入记录
- 观测页能看到每次会话注入了哪些 Skill/Knowledge

---

## 6. Sprint 3 — 技能治理闭环（预计 3 天）

**目标**：完整的 Skill 更新审批 + Git webhook + re-embedding

### Sprint 3 任务清单

| # | 任务 | 文件 | 类型 |
|---|------|------|------|
| 3.1 | `routers/approvals.py` 新增 `POST /{id}/approve` 端点 | `approvals.py` | 后端 |
| 3.2 | `routers/approvals.py` 新增 `POST /{id}/reject` 端点 | `approvals.py` | 后端 |
| 3.3 | `SkillUpdateRecord` 新增 `approval_id` + `git_pr_url` 字段 | `schemas.py` | 后端 |
| 3.4 | `store.apply_skill_update()` 审批通过后触发 re-embedding | `store.py` | 后端 |
| 3.5 | 新增 `POST /api/skill-updates/git-webhook` 端点 | `routers/learning.py` | 后端 |
| 3.6 | Git webhook: 验证 HMAC-SHA256 签名 | `routers/learning.py` | 后端 |
| 3.7 | Git webhook: 解析 skills/*.md 文件变更，创建 SkillUpdateRecord | `store.py` | 后端 |
| 3.8 | Git webhook: 自动创建关联 ApprovalRecord | `store.py` | 后端 |
| 3.9 | `SkillRecord` 新增 `version` 字段，每次 apply 递增 | `schemas.py` + `store.py` | 后端 |
| 3.10 | 前端治理中心 approve/reject 按钮连接新端点 | `pages/governance/index.tsx` | 前端 |
| 3.11 | 前端知识库技能 Tab 新增技能 diff 对比视图 | `pages/knowledge/index.tsx` | 前端 |
| 3.12 | 前端新增 Skill 更新版本历史视图 | `pages/knowledge/index.tsx` | 前端 |
| 3.13 | Docker 重新 build 并验证完整闭环 | — | 部署 |

**Sprint 3 验收标准**：
- `POST /api/skill-updates/git-webhook` 接收 GitHub 推送事件后自动创建审批
- 管理员在治理中心 approve 后 Skill 向量自动更新
- Skill 记录显示版本号递增历史

---

## 7. Sprint 4 — 生产加固（预计 3 天）

**目标**：性能、安全、可观测性、用户体验全面加固

### Sprint 4 任务清单

| # | 任务 | 文件 | 类型 |
|---|------|------|------|
| 4.1 | RAG 注入结果缓存（TTL=5min，避免重复向量搜索） | `store.py` | 性能 |
| 4.2 | Embedding 失败时降级词汇搜索并记录日志 | `store.py` | 可靠性 |
| 4.3 | Key 用量从 LiteLLM DB 实时查询（替换本地统计） | `store.py` | 数据一致性 |
| 4.4 | 费用报表端点（按用户/团队/模型统计） | `routers/platform.py` | 功能 |
| 4.5 | 配额预警（剩余 20% 时发平台内通知） | `store.py` | 治理 |
| 4.6 | 供应商健康探活定时任务（每 5 分钟） | `store.py` | 可靠性 |
| 4.7 | Knowledge 文档删除时清理 Qdrant chunks | `store.py` | 数据一致性 |
| 4.8 | Skill 归档时从 Qdrant 删除向量 | `store.py` | 数据一致性 |
| 4.9 | 前端控制台实时费用图表 | `pages/dashboard/index.tsx` | 前端 |
| 4.10 | 前端 Key 管理页显示实时用量进度条 | `pages/keys/index.tsx` | 前端 |
| 4.11 | 前端供应商页显示健康探活状态徽章 | `pages/providers/index.tsx` | 前端 |
| 4.12 | 完整 E2E 测试文档 + Docker 生产配置模板 | `docs/` | 文档 |

**Sprint 4 验收标准**：
- RAG 响应时间 < 200ms（含向量搜索）
- Key 用量实时准确（从 LiteLLM DB 查询）
- 供应商故障自动在 5 分钟内触发告警
- 完整的从"注册供应商"到"开发者使用"的 E2E 测试通过

---

## 8. 迭代总览时间表

```
Week 1        Week 2        Week 3        Week 4
━━━━━━━━━━━   ━━━━━━━━━━━   ━━━━━━━━━━━   ━━━━━━━━━━━
Sprint 1      Sprint 2      Sprint 3      Sprint 4
地基打通       RAG 激活       技能治理        生产加固
Day 1-3       Day 4-7       Day 8-10      Day 11-13

里程碑:        里程碑:        里程碑:        里程碑:
开发者能用      RAG 工作       闭环完整        生产就绪
虚拟 key       技能自动注入    Git 审批生效     稳定可靠
```

---

## 9. 风险评估

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| LiteLLM `/key/generate` API 参数不兼容 | 中 | 高 | Sprint 1 先用测试 key 验证 API，再接入 |
| Embedding 模型 `text-embedding-3-small` 需要 OpenAI key | 中 | 高 | 先验证 OpenAI key 已配置，或改用本地 embedding |
| PostgreSQL schema migration 影响现有数据 | 低 | 中 | 每次 migration 先备份，使用 ALTER TABLE 而非重建 |
| Qdrant 向量维度不匹配（切换模型时） | 低 | 高 | 切换 embedding 模型须重建 collection |
| RAG 注入导致 Token 超出 context window | 中 | 中 | 设置最大注入字符数限制，优先注入最相关的 |
| Git webhook 签名验证绕过 | 低 | 高 | 严格 HMAC 验证，非生产环境可 bypass |
