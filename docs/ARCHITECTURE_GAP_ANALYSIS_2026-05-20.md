# 架构现状分析与差距报告（CLI / Git / RAG / Skill / Agent / MCP）

> 更新日期：2026-05-20  
> 范围：回应 7 个真实问题；逐项给出**现状结论 + 代码证据 + 差距 + 落地建议**。  
> 备注：本文是对 [`MCP_SKILL_RAG_AGENT_EVOLUTION_PROTOCOL.md`](./MCP_SKILL_RAG_AGENT_EVOLUTION_PROTOCOL.md) 等历史协议文档的**现状校正版**。历史文档描述的是设计目标，本文描述截至当前 commit `8965c45` 的真实落地。

---

## 0. TL;DR — 一张图说清现状与缺口

```
            ┌─────────────────────────────────────────────────────────────┐
            │                Team AI Platform (control plane)              │
            │                                                              │
   CLI ──▶  │  REST  ─┬─▶ Git Repo Mgr ─▶ pull_git_repo_skills() ─┐       │
   IDE ──?  │         ├─▶ Hook Receiver (HMAC) ────────────────┐  │       │
            │         ├─▶ RAG ingest ──▶ Qdrant                │  │       │
            │         ├─▶ Task-Run + Skill Update Apply        │  │       │
            │         ├─▶ Evolution: rag→skill / rag→agent     │  │       │
            │         └─▶ "MCP" REST endpoints (CRUD only)     │  │       │
            │             ▼                                    ▼  ▼       │
            │           SkillBundle/TeamRule store        SkillRecord     │
            │                                                              │
            └──────────────────┬─────────────────────────────────┬─────────┘
                               │                                 │
                               │   ✗ no LiteLLM push             │   ✗ no MCP server process
                               ▼                                 ▼
                       LiteLLM gateway                  Real MCP (stdio/SSE)
                       (only master_key)                NOT IMPLEMENTED
```

| 能力 | 现状 | 完成度 |
|------|------|--------|
| Git 仓库 **后端** CRUD + Pull + Hook | ✅ 已落地 | 100% |
| Git 仓库 **前端** 列表 / Pull / Activate | ✅ 已落地 | 90%（缺 "新建" 表单与 Probe 按钮） |
| Skill ↔ LiteLLM 模型同步 | ❌ 未实现 | 0% |
| **真实 MCP server 进程**（stdio / SSE，遵循 modelcontextprotocol） | ❌ 不存在 | 0% |
| MCP 命名的 REST 端点（bundle/rules）| ✅ 数据 CRUD | 100%（**但不是 MCP 协议**） |
| IDE / CLI 客户端配置生成（`.cursor/mcp.json`, `.claude/...`, `.continuerc`） | ⚠️ 仅 opencode | 30% |
| 技术栈自动识别（`pyproject.toml` / `package.json` / `go.mod` → 推荐 skill） | ❌ 未实现 | 0% |

---

## 1. 问题逐条解答

### Q1：测试完成后，从哪里手动添加绑定的 Skill 代码仓库？

**结论**：目前**只能通过 REST/脚本添加**，前端 UI 还没有"新建仓库"按钮。

- 已有的 UI 入口：[`frontend/src/pages/governance/index.tsx`](../frontend/src/pages/governance/index.tsx) 的 `Learning` 标签页 → 列表展示 + Pull & Ingest + Activate + Hook Secret 管理。
- 缺失：表单组件 `<GitRepoCreateForm>` 还未实现。
- 替代手段：
  ```bash
  curl -X POST http://localhost:3000/api/git-repos \
    -H "X-Admin-Token: $ADMIN_TOKEN" -H 'Content-Type: application/json' \
    -d '{"name":"my-team-skills","path":"/app/backend/repos/my-team-skills","branch":"main","make_active":true}'
  ```
  注意 `path` 必须是 **backend 容器内能看到的路径**（详见 §3）。

**计划**：在 Governance 页面新增 "Add Repository" Modal，调用现有 `POST /api/git-repos`；同时把 `Probe` 按钮加在每行操作栏。

---

### Q2：为什么 LiteLLM 平台上看不到同步过去的 Skill / Agent / MCP 绑定？

**结论**：**截至当前提交，平台 → LiteLLM 的 Skill / Agent / MCP 同步链路尚未实现。**

证据：
- [`litellm/config.yaml`](../litellm/config.yaml) 只配置了 `master_key`，**完全没有 `model_list` 引用 skill/agent**。
- [`scripts/apply_litellm_gateway.sh`](../scripts/apply_litellm_gateway.sh) 只调用 `/api/v1/runtime/litellm-config/apply` 做**配置渲染预览**，没有 POST 到 LiteLLM 的 `/model/new`。
- backend 中**没有**任何代码引用 LiteLLM admin API 路径（`/model/new`、`/key/generate` 之外的 skill 注入逻辑）。

**为什么 LiteLLM 不该看到 "Skill"**：LiteLLM 是**模型路由层**，它的领域是 `model_name`、`api_key`、`rate_limit`。Skill / Agent / MCP 不是模型，**它们不应该出现在 LiteLLM 控制台**。它们应该出现在：
- 平台前端的 **Skill Library** / **Agent Workflows** 页面（已有）
- IDE 客户端的本地配置（`.claude/skills/`、`.cursor/mcp.json`） — 通过 MCP server 加载

正确的同步关系是：
```
Skill / Agent / MCP bundle  ──▶  平台 store  ──▶  MCP server  ──▶  IDE / CLI
模型 (provider/model_name)   ──▶  平台 store  ──▶  LiteLLM      ──▶  统一调用
```

平台与 LiteLLM 之间真正需要同步的是 **模型**（provider→model_list），不是 skill。

---

### Q3：MCP 服务器作用是什么？我们现在架构有实现吗？

**MCP 的本质**：MCP (Model Context Protocol) 是 Anthropic 在 2024 推出的开放协议，让 LLM 客户端（Claude Desktop、Claude Code、Cursor、Continue、Cline 等）以**统一方式**接入外部上下文与工具。一个 MCP server 暴露三种能力：

| MCP 原语 | 用途 | 对应到本平台 |
|----------|------|--------------|
| `tools/list` + `tools/call` | 让 LLM 调用函数 | 触发 `report_task_run`、`pull_repo`、`apply_skill_update` 等 |
| `resources/list` + `resources/read` | 让 LLM 读取上下文 | 加载 Skill 系统提示、RAG 检索片段、团队规则 |
| `prompts/list` + `prompts/get` | 提供可复用 prompt 模板 | 团队级 system prompt / 工作流模板 |

**与 LiteLLM 的区别**：
- LiteLLM = **南向**统一（一个接口对接所有 LLM 厂商）
- MCP    = **北向**统一（一个接口让所有 IDE / CLI 接入我们的能力）
- 两者**不冲突、互补**。IDE → MCP server (本平台) → LiteLLM → LLM provider。

**当前架构是否实现 MCP？**：❌ **没有真实 MCP server 进程**。
- 工作区 grep `@modelcontextprotocol/sdk` / `mcp.server` / `fastmcp` / `tools/list` → 零命中。
- `/api/skill-sync/mcp/*` 只是 **REST 路径用了 mcp 这个名字**，handler 内部全是 `store.upload_skill_bundle()` 之类的 store CRUD，没有任何 MCP JSON-RPC 报文。

**推荐实现路径**（详见 §4 落地建议）：
1. 用 Python `mcp` 官方包或 `fastmcp`，在 `backend/mcp_server/` 下新建独立进程
2. 暴露 4 个 Tool（`list_skills`、`get_skill_prompt`、`search_rag`、`report_task_run`）+ 2 个 Resource（`skill://`、`rag://`）
3. 通过 stdio + SSE 双协议供 IDE 接入

---

### Q4：Team AI Platform 中的"代码仓库管理"实际关联了哪些有用功能？

**你反馈的真实体验（已确认）**：

- 菜单入口有（Governance -> 学习闭环运维），但默认常见为"空列表"。
- 页面没有"新增 Git 仓库"表单，导致仓库列表为空时无法在 UI 内完成初始化。
- MCP-Skill-RAG-Agent 区域要求手填 `Team ID`，且无团队下拉选择器；当用户不知道可用 `team_id` 时，会被拦在第一步。

**为什么会出现"有菜单但没数据"**：

- `gitRepos` 数据来自 `GET /api/git-repos`，未创建过仓库时返回空数组，页面只显示"未配置 Git 仓库"。
- 当前治理页没有调用 `POST /api/git-repos` 的入口，所以无法在该页完成从 0 到 1。
- Team 相关动作（上传 bundle / 生成规则 / 应用规则 / 入库）都依赖 `teamId` 输入框的手工填写，没有默认团队与选择器。

**当前实际数据流（后端已实现）**：

```
1. POST /api/git-repos                 → 创建 GitRepoRecord
2. POST /api/git-repos/{id}/pull       → git pull + 递归扫描 *.skill.json
3. _ingest_skill_from_repo_payload()   → SkillRecord 新增 / 更新 / 冲突
   └─ 冲突 → SkillUpdateRecord (status='conflict')
4. Git post-commit hook → /api/skill-sync/hooks/report (HMAC)
   └─ 记录 SkillHookEventRecord (repo_id, commit_sha, changed_files)
5. /api/skill-updates/{id}/apply       → 把冲突/草案推进为正式 skill
```

证据：[`backend/app/store.py`](../backend/app/store.py) 的 `pull_git_repo_skills()` 实际会 `rglob("*.skill.json")` 并产出 skill record。

**当前未打通的环节（缺口）**：

- ❌ 前端缺 `Add Repository` 表单（导致仓库为空时，用户无法初始化列表）。
- ❌ 前端缺团队选择器（只能手填 `team_id`，可用值不可见）。
- ❌ Skill 落地后**没有**自动推送到 LiteLLM / MCP / IDE。
- ❌ 没有把仓库里的 `.cursor/`, `.continue/`, `.claude/` 配置也作为团队规则来源。
- ❌ 没有把 commit author → user_id 关联，无法做"个人 skill 私有 vs 团队公有"。

**修正后的结论**：

代码仓库管理在后端是可用的 GitOps 能力，但前端当前停在"查看/拉取"阶段，缺初始化入口和团队上下文选择，导致你看到的现象是"菜单存在但无法自助落地"。优先级最高的修复应是：

1. Governance 增加 `Add Repository` Modal（name/path/branch/auto_commit/make_active）。
2. Governance 增加团队下拉（数据源 `GET /api/v1/teams`），并把 `team_id` 与动作按钮联动。
3. 在空态区域给出一键引导（"先创建团队 -> 再添加仓库 -> 再 Pull & Ingest"）。

---

### Q5：本地 CLI 如何绑定 MCP 服务器，达到 Skill 与可共享内容的共享？

**目标状态**（当 MCP server 落地后）：

```jsonc
// ~/.cursor/mcp.json  或  ~/.claude.json
{
  "mcpServers": {
    "team-ai-platform": {
      "command": "uvx",
      "args": ["aegis-team-mcp"],
      "env": {
        "TEAM_AI_API_BASE": "http://localhost:3000",
        "TEAM_AI_ADMIN_TOKEN": "sk-admin-…",
        "TEAM_AI_USER_ID": "yaodongshi"
      }
    }
  }
}
```

IDE 启动后，MCP server 子进程会：
1. 拉取 `GET /api/skills?status=active` 列表 → 暴露为 `resources/list` 项
2. 拉取 `GET /api/evolution/rag-to-agent/workflows` → 暴露为 `prompts/list` 项
3. 暴露 `tools/call report_task_run` → 自动调用 `/api/task-runs/report`
4. 暴露 `tools/call search_rag` → 调用 `/api/v1/knowledge/search`

**当前阶段的替代方案**（在 MCP server 上线之前）：
- 使用 `scripts/install_skill_hook.sh` 把 post-commit hook 装到本地仓库 → 仍然能让平台收到 commit 事件
- 用 `scripts/report_task_run.sh` 手动报送任务 → RAG 累积
- 客户端配置仍需手动写 `.claude/skills/` 文件

---

### Q6：MCP 是否可以根据 CLI 所处本地项目的技术栈，自动加载对应 skill？

**理论上完全可以**。MCP server 在启动时知道自己的 CWD：

```python
# pseudo
def detect_stack(cwd: Path) -> list[str]:
    stacks = []
    if (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists():
        stacks.append("python")
    if (cwd / "package.json").exists():
        stacks.append("nodejs")
    if (cwd / "go.mod").exists():
        stacks.append("go")
    if (cwd / "Cargo.toml").exists():
        stacks.append("rust")
    if (cwd / "__manifest__.py").exists():
        stacks.append("odoo")
    if (cwd / ".cursor").is_dir() or (cwd / ".claude").is_dir():
        stacks.append("ai-assisted")
    return stacks
```

然后调用 `GET /api/skills/search?query=python+refactor&tags=python` 把匹配的 skill 注入到 `resources/list`。

**当前实现状态**：❌ 完全没有。grep `detect_stack` / `tech_stack` / `pyproject` → 零命中。

**落地计划**：作为 MCP server 第一版的 P0 特性（详见 §4 路线图 M1）。

---

### Q7：架构差距汇总

| # | 现状 | 应有状态 | 差距 |
|---|------|----------|------|
| 1 | UI 只能列表/Pull/Activate 仓库 | UI 可新建/编辑/probe/pull/delete + 表单校验 | 缺 `<GitRepoCreateForm>` 与 `Probe` 按钮 |
| 2 | LiteLLM 只配 `master_key` | LiteLLM 的 model_list 由平台 store 自动同步 | 缺 `sync_models_to_litellm()` 实现 |
| 3 | "MCP" 只是 REST 路径名 | 独立 MCP server 进程，stdio + SSE | **缺整个 MCP server 实现** |
| 4 | 仓库 pull 只产出 skill | 同时索引 `.cursor/`、`.continue/`、AGENTS.md 等 | 缺多目标 ingestor |
| 5 | CLI 通过 REST + git hook 同步 | IDE 通过 MCP 自动绑定与同步 | 缺 MCP server + 客户端配置生成器 |
| 6 | 无技术栈识别 | MCP server 启动时自动 detect_stack | 待 MCP server 落地后即可实现 |

---

## 2. 名词澄清（避免概念漂移）

| 名词 | 平台内含义（截至 2026-05-20）| 是否符合行业标准 |
|------|-----------------------------|-----------------|
| **Skill** | 一段可复用的 `system_prompt` + 元数据 + 标签，存于 `SkillRecord` | ✅ 标准 |
| **Skill Bundle** | 团队级 Skill 打包（含 manifest + 多个 prompt），存于 `SkillBundleRecord` | ✅ 标准 |
| **Agent Workflow** | 由 RAG 自动生成的多步骤计划（`steps: [...]`） | ✅ 标准 |
| **MCP** | **当前仅指**`/api/skill-sync/mcp/*` REST 端点 | ❌ **与官方 MCP 协议无关** |
| **LiteLLM gateway** | 统一 LLM 调用入口，配置 model_list / virtual key | ✅ 标准 |
| **Git Repo (in platform)** | 团队 Skill 的 GitOps 源，本地路径 + 分支 + auto_commit | ✅ 标准 |

**建议**：把现有 `/api/skill-sync/mcp/*` 端点**重命名为** `/api/skill-sync/team-bundles/*`，避免与未来真实 MCP 路径冲突；保留旧路径 6 个月 deprecation 期。

---

## 3. 容器路径与挂载的坑（已踩过）

`docker-compose.yml` 中 backend 只挂载：
```yaml
volumes:
  - ./backend:/app/backend
  - ./litellm:/app/litellm
```

→ 任何注册到平台的 Git 仓库**必须放在 `./backend/...` 子树下**，否则 `path_exists=false`。

E2E 脚本已经采用：
- 主机路径：`backend/.aegis_e2e_repo/testskill`
- 注册到平台用：`/app/backend/.aegis_e2e_repo/testskill`

**长期方案**：把 git 仓库挂载点提到一级目录，例如：
```yaml
volumes:
  - ./skills-repos:/data/skills-repos  # 专门给业务团队 skill 仓库用
```

并在前端"新建仓库"表单中提示 `path` 必须以 `/data/skills-repos/` 开头。

---

## 4. 落地建议路线图

### M1（本周可启动，1-2 天）— 闭合"前端能管理仓库"

- [ ] `frontend/src/pages/governance/index.tsx` 新增 "Add Repository" Modal（name / path / branch / auto_commit / make_active）
- [ ] 新增每行 `Probe` 按钮，调 `/api/git-repos/{id}/probe`
- [ ] `Edit` 按钮 → `PATCH /api/git-repos/{id}`
- [ ] 后端 `pull_git_repo_skills` 返回详情中加入 `imported_skill_names: list[str]`，便于前端展示

### M2（2-3 天）— 平台 → LiteLLM 模型同步真实落地

- [ ] `backend/app/services/litellm_sync.py`：根据 store 的 `providers + models` 生成 LiteLLM `model_list`
- [ ] 写入 `litellm/config.yaml` 并触发 LiteLLM 热加载（POST `/config/reload`）
- [ ] 或改走 LiteLLM admin REST `POST /model/new`
- [ ] CI 与 `apply_litellm_gateway.sh` 串联

### M3（3-5 天，本里程碑的核心）— 真实 MCP server

- [ ] `backend/mcp_server/` 新模块（独立 Python 进程，依赖 `mcp` 官方包或 `fastmcp`）
- [ ] 实现 4 个 Tool：`list_skills` / `get_skill_prompt` / `search_rag` / `report_task_run`
- [ ] 实现 2 个 Resource：`skill://<id>` / `rag://<doc_id>`
- [ ] 实现 `detect_stack(cwd)` → 自动过滤 skills
- [ ] 同时支持 stdio（本地）+ SSE（远程团队共享）双协议
- [ ] docker-compose 增加 `team-ai-mcp` 服务

### M4（2 天）— 客户端配置生成器

- [ ] `GET /api/v1/runtime/client-config/cursor` → 输出 `.cursor/mcp.json`
- [ ] `GET /api/v1/runtime/client-config/claude-code` → 输出 `.claude.json`
- [ ] `GET /api/v1/runtime/client-config/continue` → 输出 `.continuerc`
- [ ] CLI 命令 `aegis init` → 在当前仓库写入对应配置

### M5（3 天）— 团队 GitOps 完整闭环

- [ ] 仓库 pull 时除 `*.skill.json` 外，同时索引 `AGENTS.md`、`.cursor/rules/`、`CLAUDE.md` 作为 KnowledgeUnit
- [ ] commit author → platform user 绑定
- [ ] 个人 skill vs 团队 skill 权限模型

---

## 5. 历史文档修订说明

以下历史文档需要在头部加 "现状校正" 段：

1. `docs/MCP_SKILL_RAG_AGENT_EVOLUTION_PROTOCOL.md` — 加 banner：**当前 MCP 仅指 REST 端点命名，无真实 MCP server，详见本报告 §1.Q3**
2. `docs/AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md` — 加 banner：**LiteLLM ↔ Skill 同步未实现，详见本报告 §1.Q2**
3. `docs/ITERATION_PLAN.md` — 把"客户端配置生成 30%"细化为四个目标分别打分
4. `README.md` — 在 "Real Business E2E" 章节下方加一节 "What MCP means here (现状说明)"
