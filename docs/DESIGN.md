# Team AI Platform — 系统设计文档

> 对齐声明（2026-05-19）：本文件为历史设计细节参考，当前执行基线请以 `AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md` 与 `DOCS_INDEX.md` 为准。

**版本**: v1.0  
**日期**: 2026-05-16  
**状态**: 历史参考（非当前主基线）

---

## 1. 系统目标

构建一个**统一的团队 AI 协作平台**，实现：

1. **对外统一接入**：对接全部主流 LLM 供应商，统一管理 API Key
2. **对内统一分发**：通过 LiteLLM 网关向团队成员发放虚拟 Key
3. **透明接入体验**：开发者使用任意 IDE 工具（Claude Code / opencode / Cursor / Continue.dev）与直连原厂体验完全一致
4. **技能共享闭环**：团队 Skill 和 RAG 知识库自动注入每次对话
5. **自我迭代治理**：技能更新经 Git PR 审批后合并生效，全团队自动受益

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 0: LLM 供应商层                                                │
│  OpenAI │ Anthropic │ Azure OpenAI │ Gemini │ DeepSeek │ 本地 LLM  │
└────────────────────────┬────────────────────────────────────────────┘
                         │ API Key 加密存储，config.yaml 同步
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 1: AI 网关 — LiteLLM (:4000)                                  │
│  • OpenAI 兼容 API（/v1/chat/completions, /v1/models, /v1/embeddings）│
│  • 虚拟 Key 鉴权 + 速率限制 + 配额                                    │
│  • 模型路由 / 成本归因 / 完整日志                                       │
│  • PostgreSQL 持久化（litellm_db）                                   │
└──────────────┬──────────────────────────────┬───────────────────────┘
               │ /key/generate + /key/delete   │ 使用量回调
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 2: 管控平台 — Backend (:8000) + Frontend (:3000)              │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐ │
│  │ 供应商管理    │ │ 虚拟 Key 管理 │ │ 用户/团队/项目管理           │ │
│  │ providers.py │ │ keys.py      │ │ api/v1/users, teams        │ │
│  └──────────────┘ └──────────────┘ └────────────────────────────┘ │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐ │
│  │ Skill 库      │ │ 技能审批闭环  │ │ 知识库 RAG                  │ │
│  │ skills.py    │ │ learning.py  │ │ api/v1/knowledge.py        │ │
│  │              │ │ approvals.py │ │                            │ │
│  └──────────────┘ └──────────────┘ └────────────────────────────┘ │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐ │
│  │ RAG 注入中间件 │ │ 观测中心      │ │ 开发者配置生成              │ │
│  │openai_compat │ │ sessions.py  │ │ runtime_config.py          │ │
│  │              │ │ auditlogs    │ │                            │ │
│  └──────────────┘ └──────────────┘ └────────────────────────────┘ │
└──────────┬──────────────────────────────────┬───────────────────────┘
           │ embedding API                    │ 向量检索
           ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 3: 向量存储 — Qdrant (:6333)                                   │
│  skill_collection       knowledge_collection                        │
│  技能向量索引             文档段落向量索引                               │
└─────────────────────────────────────────────────────────────────────┘
           ▲
           │  base_url: http://[team-ai-host]:4000/v1
           │  api_key: sk-virtual-[personal]
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 4: 开发者工作站（任意工具）                                       │
│  Claude Code │ opencode │ Cursor │ Continue.dev │ OpenAI SDK       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心数据模型

### 3.1 ProviderRecord（AI 供应商）

```python
class ProviderRecord:
    id: str                          # 内部 ID
    name: str                        # 展示名
    provider_type: str               # openai / anthropic / azure / google / deepseek
    base_url: str                    # API 端点
    api_key_masked: str              # 掩码显示（实际存于 provider_secrets）
    api_format: str                  # openai / anthropic / openai_responses
    scope: str                       # app / unified
    enabled: bool                    # 是否推送到 LiteLLM
    created_at: datetime
    updated_at: datetime
```

**同步机制**：`enabled=True` 的供应商在 CRUD 时自动调用 `_sync_providers_to_litellm_config()` 写入 `litellm/config.yaml` 并调用 LiteLLM `/model/new` API 实现热更新。

### 3.2 KeyRecord（虚拟 Key）

```python
class KeyRecord:
    id: str                          # 内部 ID
    key_hash: str                    # SHA256 哈希（不存明文）
    litellm_key_id: str              # [待实现] LiteLLM 分配的 key ID
    label: str                       # 用途标签
    user_id: str                     # 所属用户
    project_id: str                  # 所属项目（可选）
    scope: str                       # 授权模型范围（逗号分隔）
    expire_at: datetime              # 过期时间
    quota: int                       # Token 配额
    status: "active" | "revoked"
    created_at: datetime
    updated_at: datetime
```

**目标**：`issue_key()` 后立即调用 `LiteLLM POST /key/generate`，以 LiteLLM 返回的真实 `sk-xxx` 作为开发者使用的 key。

### 3.3 SkillRecord（技能）

```python
class SkillRecord:
    id: str
    name: str
    description: str
    system_prompt: str               # 注入到 LLM 的系统提示词
    category: str                    # 分类：code / debug / review / general
    tags: list[str]
    status: "active" | "archived"
    version: int                     # [待实现] 版本号
    qdrant_vector_id: str            # [待实现] Qdrant 中的向量 ID
    created_at: datetime
    updated_at: datetime
```

### 3.4 SkillUpdateRecord（技能更新提案）

```python
class SkillUpdateRecord:
    id: str
    task_run_id: str                 # 来源任务运行
    skill_id: str                    # 目标 Skill（None = 新建）
    proposed_skill_name: str
    proposed_system_prompt: str
    proposed_user_prompt_template: str
    rationale: str                   # 更新理由
    error_patterns: str              # 触发此更新的错误模式
    status: "draft" | "applied" | "synced" | "rejected"
    approval_id: str                 # [待实现] 关联的 ApprovalRecord.id
    git_repo_id: str                 # 关联的 Git 仓库
    git_commit_hash: str             # 关联的 commit
    git_pr_url: str                  # [待实现] PR/MR URL
    export_path: str
    created_at: datetime
    updated_at: datetime
```

### 3.5 KnowledgeRecord（知识文档）

```python
class KnowledgeRecord:
    id: str
    project_id: str
    title: str
    content: str
    format: str                      # markdown / text / code
    tags: list[str]
    status: "active" | "archived"
    version: int
    qdrant_chunk_ids: list[str]      # [待实现] 分块后 Qdrant 中的 ID 列表
    created_by: str
    created_at: datetime
    updated_at: datetime
```

### 3.6 SessionRecord（AI 会话）

```python
class SessionRecord:
    id: str
    user_id: str
    project_id: str
    title: str
    summary: str
    injected_skill_ids: list[str]    # [待实现] 本次注入的 Skill IDs
    injected_knowledge_ids: list[str] # [待实现] 本次注入的 Knowledge IDs
    rag_search_query: str            # [待实现] 触发 RAG 的查询
    status: "active" | "completed"
    created_at: datetime
    updated_at: datetime
```

---

## 4. 关键 API 设计

### 4.1 虚拟 Key 管理

```
POST /api/keys/issue
  Request: { label, user_id, project_id, scope, expires_days, quota }
  Response: { key_id, key_secret(LiteLLM真实sk), label, status, expire_at }
  副作用: → LiteLLM POST /key/generate

DELETE /api/keys/{key_id}
  副作用: → LiteLLM DELETE /key/delete

GET /api/keys/{key_id}/usage
  返回: 调用次数、Token 消耗（从 LiteLLM DB 查询）
```

### 4.2 Skill RAG 搜索与注入

```
GET /api/skills/search?query=xxx&limit=5
  模式: 优先向量搜索（Qdrant），降级词汇搜索

POST /v1/chat/completions  (openai_compat.py)
  拦截流程:
  1. 提取最后一条 user 消息内容
  2. 并行搜索: skill_collection + knowledge_collection (top_k=3+2)
  3. 构造 system 上下文块注入 messages[0]
  4. 记录 session（injected_skill_ids, injected_knowledge_ids）
  5. 转发到 http://litellm:4000/v1/chat/completions
```

### 4.3 知识库 RAG

```
POST /api/v1/knowledge/
  副作用:
  1. 分块（chunk_size=512, overlap=64）
  2. 调用 LiteLLM /v1/embeddings 获取向量
  3. 存入 Qdrant knowledge_collection
  4. 记录 qdrant_chunk_ids 到 KnowledgeRecord

GET /api/v1/knowledge/search?query=xxx&limit=5
  返回: 相关文档块 + 相似度分数
```

### 4.4 技能更新 Git 闭环

```
POST /api/task-runs/report
  提交任务运行报告（包含 proposed_skill_name + proposed_system_prompt）
  自动创建 SkillUpdateRecord(status=draft)

POST /api/skill-updates/{id}/apply
  管理员审批通过后执行:
  1. 更新 SkillRecord（或创建新 Skill）
  2. 重新 embedding → 更新 Qdrant 向量
  3. SkillUpdateRecord.status = applied

POST /api/skill-updates/git-webhook  [新增]
  接收 GitHub/GitLab webhook:
  1. 验证 webhook secret
  2. 提取 skills/*.md 变更文件
  3. 对每个变更文件创建 SkillUpdateRecord(status=draft)
  4. 触发 ApprovalRecord 创建（关联 skill_update_id）

POST /api/approvals/{id}/approve  [新增]
  审批人操作:
  1. ApprovalRecord.status = approved
  2. 自动调用 apply_skill_update(linked_skill_update_id)
```

### 4.5 开发者接入配置生成

```
GET /api/runtime-config/client?app=claude-code&gateway_url=xxx&api_key=xxx
  返回: ~/.claude/settings.json 配置内容

GET /api/runtime-config/client?app=opencode
  返回: ~/.opencode/settings.json 配置内容

GET /api/runtime-config/client?app=continue
  返回: .continue/config.json 配置内容

GET /api/runtime-config/client?app=cursor
  返回: .cursor/mcp.json 配置内容
```

### 4.6 模型列表透明化

```
GET /v1/models  (代理到 LiteLLM)
  目标: 返回所有已启用供应商的完整模型列表（等同于直连原厂）
  实现: GET http://litellm:4000/v1/models 并转发响应
```

---

## 5. 数据流详图

### 5.1 开发者调用 AI（RAG 注入流）

```
Developer IDE
  │ POST /v1/chat/completions
  │ Authorization: Bearer sk-virtual-abc123
  ▼
Backend :8000 (openai_compat.py)
  │ 1. 验证 Bearer token（转交 LiteLLM 验证）
  │ 2. 提取 last user message
  │ 3. 并行 Qdrant 搜索：skill_collection + knowledge_collection
  │    → 返回 top-3 skills + top-2 knowledge chunks
  │ 4. 构造注入块:
  │    system: "[团队技能: xxx]\n{system_prompt}\n\n[知识: yyy]\n{chunk}"
  │ 5. 记录 SessionRecord（异步）
  ▼
LiteLLM :4000
  │ 验证 sk-virtual-abc123 → 查数据库确认有效
  │ 路由到对应供应商
  │ 记录用量
  ▼
AI Provider (OpenAI / Anthropic / ...)
  │ 返回响应
  ▼
Backend :8000 → Developer IDE
```

### 5.2 技能更新闭环流

```
开发者修复 Bug
  │
  ▼
提交任务报告: POST /api/task-runs/report
  {
    tool_type: "claude_code",
    task_title: "修复用户认证空指针",
    summary: "...",
    proposed_skill_name: "Python 空值安全检查",
    proposed_system_prompt: "..."
  }
  │ 自动创建 SkillUpdateRecord(status=draft)
  ▼
审批队列（治理中心 UI）
  │ 审批人看到 diff（old_system_prompt vs proposed）
  │ 评论 / 批准 / 拒绝
  ▼
POST /api/approvals/{id}/approve
  │ 自动触发 apply_skill_update()
  │ → 更新 SkillRecord
  │ → 重新 embedding → Qdrant 更新
  │ → SkillUpdateRecord.status = applied
  ▼
全团队下次调用时 Qdrant 返回新向量 → 新技能自动注入
```

---

## 6. 基础设施配置（目标状态）

```yaml
# docker-compose.yml 环境变量（目标完整配置）
backend:
  environment:
    # 持久化
    TEAM_AI_PLATFORM_DB_DSN: postgresql://litellm:xxx@litellm_db:5432/litellm
    # 向量存储
    TEAM_AI_PLATFORM_QDRANT_URL: http://qdrant:6333
    # LiteLLM 内部地址
    LITELLM_INTERNAL_BASE_URL: http://litellm:4000
    # Embedding 模型（必须在 LiteLLM 中注册）
    TEAM_AI_PLATFORM_SKILL_EMBEDDING_MODEL: text-embedding-3-small
    # 管理认证
    TEAM_AI_PLATFORM_ADMIN_TOKEN: ${TEAM_AI_PLATFORM_ADMIN_TOKEN}
    # Git Webhook
    TEAM_AI_PLATFORM_WEBHOOK_SECRET: ${TEAM_AI_PLATFORM_WEBHOOK_SECRET}
    # 对外网关 URL（供 client config 生成使用）
    TEAM_AI_PLATFORM_GATEWAY_BASE_URL: http://[公网或内网IP]:4000/v1
```

---

## 7. 安全设计

| 层级 | 机制 | 说明 |
|------|------|------|
| 供应商 API Key | 加密存储于 `provider_secrets` dict（内存）/PostgreSQL | 不以明文传输，掩码展示 |
| 虚拟 Key | SHA256 哈希存储，只展示一次 | 丢失须重新发放 |
| LiteLLM 鉴权 | Bearer token 传透给 LiteLLM | LiteLLM 负责验证有效性 |
| 管理接口 | `require_admin_token` 中间件 | 所有 `/api/*` 写操作需 ADMIN_TOKEN |
| Git Webhook | HMAC-SHA256 签名验证 | 防伪造请求 |
| 配额控制 | LiteLLM 内置 + 平台层审批 | 防滥用 |
