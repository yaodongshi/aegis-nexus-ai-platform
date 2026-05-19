# Team AI Platform — 执行手册

> 对齐声明（2026-05-19）：本文件保留为阶段性执行记录，当前执行顺序与目标验收请以 `AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md` 为准。

**版本**: v1.0  
**日期**: 2026-05-16  
**状态**: 历史参考（非当前主基线）

---

## Sprint 1 执行指令（地基打通）

### S1-1: 配置 LiteLLM Embedding 模型

**文件**: `team_ai_platform/litellm/config.yaml`

```yaml
# 操作: 将现有文件内容替换为以下内容
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY

model_list:
  - model_name: text-embedding-3-small
    litellm_params:
      model: openai/text-embedding-3-small
      api_key: os.environ/OPENAI_API_KEY
```

**验证**: `docker compose restart litellm && curl -s http://localhost:4000/v1/models | python3 -m json.tool | grep text-embedding`

---

### S1-2 + S1-3 + S1-4: 虚拟 Key 桥接 LiteLLM

**文件**: `backend/app/schemas.py`  
**操作**: `KeyRecord` 新增 `litellm_key_id` 字段

```python
# 在 KeyRecord 的 key_hash 字段后添加:
litellm_key_id: str | None = None  # LiteLLM 分配的 key 标识
```

**文件**: `backend/app/store.py`  
**操作**: 修改 `issue_key()` 方法，在本地存储后调用 LiteLLM  
**定位**: 第 385 行附近 `def issue_key()`

```python
# 在 issue_key() 末尾（return 之前），追加 LiteLLM 调用逻辑:
# 1. 调用 LiteLLM POST /key/generate
# 2. 将返回的真实 sk-xxx 替换 key_secret
# 3. 将 litellm_key_id 存入 KeyRecord

# 修改 revoke_key() 同样追加 LiteLLM DELETE /key/delete 调用
```

**完整实现代码**（在 `issue_key()` 中替换 key_secret 生成逻辑后）:
```python
# 调用 LiteLLM 生成真实可用的 key
litellm_base = self._litellm_base_url()
litellm_master = self._litellm_master_key()
if litellm_base and litellm_master:
    try:
        import httpx as _httpx
        with _httpx.Client(timeout=10.0) as http_client:
            resp = http_client.post(
                f"{litellm_base}/key/generate",
                headers={"Authorization": f"Bearer {litellm_master}"},
                json={
                    "key_alias": f"{payload.label or 'key'}:{payload.user_id}:{key_id}",
                    "user_id": payload.user_id or "unknown",
                    "max_budget": float(payload.quota) / 1_000_000 if payload.quota else None,
                    "duration": f"{payload.expires_days}d" if getattr(payload, 'expires_days', None) else None,
                    "models": [s.strip() for s in payload.scope.split(",") if s.strip()] if payload.scope and payload.scope != "project:*" else [],
                    "metadata": {"team_ai_key_id": key_id, "platform": "team-ai"},
                },
            )
        if resp.status_code == 200:
            litellm_data = resp.json()
            real_key = litellm_data.get("key")
            litellm_key_id = litellm_data.get("key_id") or litellm_data.get("token_id")
            if real_key:
                key_secret = real_key  # 用 LiteLLM 的真实 key 替换本地生成的
    except Exception as exc:
        logging.getLogger(__name__).warning("LiteLLM key sync failed: %s", exc)
```

---

### S1-5: /v1/models 代理到 LiteLLM

**文件**: `backend/app/routers/openai_compat.py`  
**操作**: 在文件末尾追加新路由

```python
@router.get("/v1/models")
async def list_models(request: Request):
    """代理 /v1/models 到 LiteLLM，返回完整模型列表（等同于直连原厂体验）"""
    auth_header = request.headers.get("Authorization", "")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{_LITELLM_INTERNAL_BASE}/v1/models",
            headers={"Authorization": auth_header},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
```

---

### S1-6 + S1-7 + S1-8: 多工具客户端配置生成

**文件**: `backend/app/store.py`  
**操作**: 扩展 `SUPPORTED_CLIENT_APPS` 并添加渲染函数

```python
# 修改常量:
SUPPORTED_CLIENT_APPS: tuple[str, ...] = ("opencode", "claude-code", "continue", "cursor")

# 在 build_client_runtime_config() 的 if/elif 链中追加:
elif normalized_app == "claude-code":
    client_config = self._render_claude_code_client_config(
        base_url=base_url, api_key=effective_key, model_names=model_names
    )
elif normalized_app == "continue":
    client_config = self._render_continue_client_config(
        base_url=base_url, api_key=effective_key, model_names=model_names
    )
elif normalized_app == "cursor":
    client_config = self._render_cursor_client_config(
        base_url=base_url, api_key=effective_key, model_names=model_names
    )
```

**Claude Code 配置模板** (`~/.claude/settings.json`):
```python
@staticmethod
def _render_claude_code_client_config(*, base_url: str, api_key: str, model_names: list[str]) -> dict:
    return {
        "env": {
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_API_KEY": api_key,
        },
        "_comment": "将此内容合并到 ~/.claude/settings.json，重启 claude 生效",
        "_models_available": model_names,
    }
```

**Continue.dev 配置模板** (`~/.continue/config.json`):
```python
@staticmethod
def _render_continue_client_config(*, base_url: str, api_key: str, model_names: list[str]) -> dict:
    return {
        "models": [
            {
                "title": f"Team AI - {m}",
                "provider": "openai",
                "model": m,
                "apiBase": base_url,
                "apiKey": api_key,
            }
            for m in model_names[:6]  # Continue 推荐不超过 6 个
        ],
        "_comment": "将此 models 数组合并到 ~/.continue/config.json",
    }
```

**Cursor 配置模板** (`.cursor/mcp.json` + Settings > Models):
```python
@staticmethod
def _render_cursor_client_config(*, base_url: str, api_key: str, model_names: list[str]) -> dict:
    return {
        "_comment": "在 Cursor Settings > Models 中手动填入以下信息",
        "cursor_settings": {
            "openaiApiKey": api_key,
            "openaiBaseUrl": base_url,
        },
        "_models_available": model_names,
    }
```

---

### S1-9: 前端设置页更新

**文件**: `frontend/src/pages/settings/index.tsx`  
**操作**: 运行时配置 Tab 新增 4 个工具的配置生成按钮（claude-code / continue / cursor / opencode）

---

### S1-10: 验证 Sprint 1

```bash
# 1. 重建并启动
cd team_ai_platform
docker compose build backend && docker compose up --no-deps -d backend

# 2. 验证 embedding 可用
curl -s http://localhost:8000/api/skills/search-status | python3 -m json.tool
# 预期: "embedding_available": true

# 3. 发放 key 并验证可用性
ADMIN_TOKEN=$(docker compose exec backend python3 -c "import os; print(os.getenv('TEAM_AI_PLATFORM_ADMIN_TOKEN',''))")
KEY_RESP=$(curl -s -X POST http://localhost:8000/api/keys/issue \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"label":"test-dev","user_id":"dev01","scope":"gpt-4o","expires_days":30}')
TEST_KEY=$(echo $KEY_RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['key_secret'])")

# 4. 用 key 调用 LiteLLM（应成功）
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer $TEST_KEY" | python3 -m json.tool | head -20

# 5. 验证模型列表代理
curl -s http://localhost:8000/v1/models | python3 -m json.tool | head -20
```

---

## Sprint 2 执行指令（RAG 激活）

### S2-1: Knowledge 迁移到 PostgreSQL

**文件**: `backend/app/api/v1/knowledge.py`  
**操作**: 删除模块级 `_KNOWLEDGE: dict` 内存字典，改用 `PlatformStore` 方法

**新增 store 方法**（`store.py`）:
```python
def create_knowledge_doc(self, payload: KnowledgeCreateRequest, user_id: str) -> KnowledgeRecord
def list_knowledge_docs(self, project_id: str | None, q: str | None) -> list[KnowledgeRecord]
def get_knowledge_doc(self, doc_id: str) -> KnowledgeRecord | None
def update_knowledge_doc(self, doc_id: str, payload: KnowledgeUpdateRequest) -> KnowledgeRecord | None
def delete_knowledge_doc(self, doc_id: str) -> bool
def search_knowledge_semantic(self, query: str, limit: int = 5) -> list[KnowledgeChunkResult]
```

**PostgreSQL 表结构**:
```sql
CREATE TABLE IF NOT EXISTS knowledge_docs (
    doc_id TEXT PRIMARY KEY,
    project_id TEXT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    format TEXT DEFAULT 'markdown',
    tags JSONB DEFAULT '[]',
    status TEXT DEFAULT 'active',
    version INTEGER DEFAULT 1,
    qdrant_chunk_ids JSONB DEFAULT '[]',
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

---

### S2-2 + S2-3 + S2-4 + S2-5: Knowledge 向量化流水线

**文件**: `backend/app/store.py`  
**操作**: 在 `create_knowledge_doc()` 中追加 embedding 流水线

```python
def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """将文本按 token 近似长度分块（按字符数近似）"""
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks

def _embed_and_store_knowledge(self, doc_id: str, title: str, content: str) -> list[str]:
    """分块 → embedding → 存入 Qdrant knowledge_collection，返回 chunk_ids"""
    chunks = self._chunk_text(f"{title}\n\n{content}")
    chunk_ids = []
    
    base_url = self._litellm_base_url()
    master_key = self._litellm_master_key()
    if not base_url or not master_key:
        return chunk_ids
    
    client = self._get_qdrant_client()
    if not client:
        return chunk_ids
    
    COLLECTION = "team_ai_knowledge"
    # 确保 collection 存在（dim=1536 for text-embedding-3-small）
    self._ensure_qdrant_collection(client, 1536, collection_name=COLLECTION)
    
    with httpx.Client(timeout=30.0) as http:
        resp = http.post(
            f"{base_url}/v1/embeddings",
            headers={"Authorization": f"Bearer {master_key}"},
            json={"model": self._skill_embedding_model(), "input": chunks},
        )
    
    if resp.status_code != 200:
        return chunk_ids
    
    embeddings = [item["embedding"] for item in resp.json()["data"]]
    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
        chunk_id = f"{doc_id}_chunk_{i}"
        chunk_ids.append(chunk_id)
        points.append(qdrant_models.PointStruct(
            id=abs(hash(chunk_id)) % (2**63),
            vector=vector,
            payload={"doc_id": doc_id, "chunk_index": i, "text": chunk, "chunk_id": chunk_id},
        ))
    
    client.upsert(collection_name=COLLECTION, points=points)
    return chunk_ids
```

---

### S2-7: Knowledge 语义搜索端点

**文件**: `backend/app/api/v1/knowledge.py`

```python
@router.get("/search")
def search_knowledge(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    store: PlatformStore = Depends(get_store),
):
    """语义搜索知识库，返回最相关的文档块"""
    results = store.search_knowledge_semantic(query=query, limit=limit)
    return {"results": results, "total": len(results)}
```

---

### S2-8 + S2-9: RAG 注入中间件

**文件**: `backend/app/routers/openai_compat.py`  
**操作**: 在 `responses_to_completions()` 和新增的 chat completions 路由中添加 RAG 注入

**注入逻辑**（插入在 `completions_payload` 构造之前）:
```python
# --- RAG Skill + Knowledge 自动注入 ---
store = getattr(getattr(request.app, "state", None), "store", None)
if store is not None:
    # 提取用户查询文本
    user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            user_query = content if isinstance(content, str) else str(content)
            break
    
    if user_query.strip():
        context_blocks = []
        injected_skill_ids = []
        injected_knowledge_ids = []
        
        # 并行搜索 Skill + Knowledge
        skill_hits = store.search_skills(query=user_query, limit=3)
        knowledge_hits = store.search_knowledge_semantic(query=user_query, limit=2)
        
        for skill in skill_hits:
            if skill.system_prompt.strip():
                context_blocks.append(f"[团队技能: {skill.name}]\n{skill.system_prompt}")
                injected_skill_ids.append(skill.id)
        
        for hit in knowledge_hits:
            context_blocks.append(f"[知识库: {hit.title}]\n{hit.text}")
            injected_knowledge_ids.append(hit.doc_id)
        
        if context_blocks:
            inject_text = "\n\n---\n\n".join(context_blocks)
            # 注入到 system message
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] = f"{inject_text}\n\n---\n\n{messages[0]['content']}"
            else:
                messages.insert(0, {"role": "system", "content": inject_text})
```

---

### S2-14: 验证 Sprint 2

```bash
# 1. 重建
docker compose build backend && docker compose up --no-deps -d backend

# 2. 上传知识文档
curl -s -X POST http://localhost:8000/api/v1/knowledge/ \
  -H "Authorization: Bearer $USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"proj_1","title":"Python 最佳实践","content":"始终检查 None 值，使用 Optional 类型注解...","format":"markdown"}'

# 3. 搜索验证
curl -s "http://localhost:8000/api/v1/knowledge/search?query=空指针" | python3 -m json.tool

# 4. 通过 Claude Code 发问，检查日志中 RAG 注入
docker compose logs backend --tail=50 | grep "RAG\|injected\|skill_hit"
```

---

## Sprint 3 执行指令（技能治理闭环）

### S3-1 + S3-2: Approve/Reject 端点

**文件**: `backend/app/routers/approvals.py`

```python
@router.post("/{approval_id}/approve", response_model=ApprovalRecord)
def approve(
    approval_id: str,
    approver_id: str = Body(..., embed=True),
    store: PlatformStore = Depends(get_store),
    _: None = Depends(require_admin_token),
) -> ApprovalRecord:
    """审批通过：更新 ApprovalRecord 并触发关联的 SkillUpdate apply"""
    record = store.approve_approval(approval_id, approver_id=approver_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return record

@router.post("/{approval_id}/reject", response_model=ApprovalRecord)
def reject(
    approval_id: str,
    approver_id: str = Body(..., embed=True),
    reason: str | None = Body(default=None, embed=True),
    store: PlatformStore = Depends(get_store),
    _: None = Depends(require_admin_token),
) -> ApprovalRecord:
    record = store.reject_approval(approval_id, approver_id=approver_id, reason=reason)
    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return record
```

**store.py 新增方法**:
```python
def approve_approval(self, approval_id: str, approver_id: str) -> ApprovalRecord | None:
    record = self.get_approval(approval_id)
    if record is None or record.status != "pending":
        return None
    # 更新 ApprovalRecord
    record.status = "approved"
    record.approver_id = approver_id
    record.updated_at = datetime.now(UTC)
    # 如果 action 是 skill_update，触发 apply
    if record.action == "skill_update":
        skill_update = self.get_skill_update_by_approval(approval_id)
        if skill_update:
            self.apply_skill_update(skill_update.id)  # 含 re-embedding
    return record
```

---

### S3-5 + S3-6 + S3-7 + S3-8: Git Webhook 端点

**文件**: `backend/app/routers/learning.py`

```python
import hashlib
import hmac

@router.post("/api/skill-updates/git-webhook", status_code=status.HTTP_200_OK)
async def git_webhook(request: Request, store: PlatformStore = Depends(get_store)):
    """接收 GitHub/GitLab push/merge 事件，自动创建技能更新提案"""
    
    # 1. 验证 HMAC-SHA256 签名
    webhook_secret = os.getenv("TEAM_AI_PLATFORM_WEBHOOK_SECRET", "").strip()
    if webhook_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = await request.body()
        expected = "sha256=" + hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    else:
        body = await request.body()
    
    payload = json.loads(body)
    
    # 2. 仅处理 push 到 main/master 或 PR merge
    ref = payload.get("ref", "")
    if not (ref.endswith("/main") or ref.endswith("/master")):
        return {"status": "skipped", "reason": "not main branch"}
    
    # 3. 提取 skills/*.md 文件变更
    commits = payload.get("commits", [])
    pr_url = payload.get("pull_request", {}).get("html_url", "")
    author = (payload.get("pusher") or {}).get("name", "unknown")
    
    created = []
    for commit in commits:
        changed_files = commit.get("added", []) + commit.get("modified", [])
        for filepath in changed_files:
            if filepath.startswith("skills/") and filepath.endswith(".md"):
                skill_name = filepath.replace("skills/", "").replace(".md", "").replace("-", " ").replace("_", " ").title()
                # 从 commit message 提取理由
                rationale = commit.get("message", "Git 自动同步")
                
                # 创建 SkillUpdateRecord
                task_run = store.report_task_run(TaskRunReportRequest(
                    tool_type="other",
                    user_id=author,
                    task_title=f"Git 同步: {skill_name}",
                    summary=f"来自 Git commit {commit.get('id','')[:8]}",
                    proposed_skill_name=skill_name,
                    proposed_system_prompt=f"[从 Git 文件 {filepath} 同步，等待人工填写具体提示词]",
                ))
                # 自动创建审批记录
                approval = store.submit_approval(ApprovalSubmitRequest(
                    applicant_id=author,
                    action="skill_update",
                    resource_id=task_run.skill_update.id,
                    reason=f"Git commit: {rationale}",
                ))
                created.append({"skill": skill_name, "approval_id": approval.id})
    
    return {"status": "ok", "created": created}
```

---

### S3-9: Skill 版本号

**文件**: `backend/app/schemas.py`
```python
# 在 SkillRecord 中新增:
version: int = 1
```

**文件**: `backend/app/store.py`  
**操作**: `apply_skill_update()` 中触发 `skill.version += 1` 并 re-embedding

---

### S3-13: 验证 Sprint 3

```bash
# 1. 测试 webhook（模拟 GitHub push 事件）
curl -s -X POST http://localhost:8000/api/skill-updates/git-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "ref": "refs/heads/main",
    "pusher": {"name": "developer_a"},
    "commits": [{
      "id": "abc123",
      "message": "优化 Python 空值检查技能",
      "added": ["skills/python-null-safety.md"]
    }]
  }'

# 2. 确认审批队列中有待审批项
curl -s http://localhost:8000/api/approvals | python3 -m json.tool | grep pending

# 3. 审批通过
APPROVAL_ID=$(curl -s http://localhost:8000/api/approvals | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['id'])")
curl -s -X POST http://localhost:8000/api/approvals/$APPROVAL_ID/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approver_id": "admin"}'

# 4. 验证 Skill 版本递增
curl -s http://localhost:8000/api/skills | python3 -m json.tool | grep version
```

---

## Sprint 4 执行指令（生产加固）

### S4-1: RAG 缓存

**文件**: `backend/app/store.py`  
**操作**: 在 `search_skills()` 和 `search_knowledge_semantic()` 前加 TTL 缓存

```python
import functools
from cachetools import TTLCache

_rag_cache: TTLCache = TTLCache(maxsize=256, ttl=300)  # 5 分钟 TTL

def search_skills_cached(self, query: str, limit: int = 3) -> list[SkillRecord]:
    cache_key = f"skills:{query}:{limit}"
    if cache_key in _rag_cache:
        return _rag_cache[cache_key]
    result = self.search_skills(query=query, limit=limit)
    _rag_cache[cache_key] = result
    return result
```

---

### S4-3: Key 用量从 LiteLLM DB 查询

**文件**: `backend/app/store.py`

```python
def get_key_usage_from_litellm(self, litellm_key_id: str) -> dict:
    """直接查 litellm_db 获取准确用量数据"""
    if not self._db_enabled:
        return {}
    with self._connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_calls,
                SUM(total_tokens) as total_tokens,
                MAX(startTime) as last_used_at
            FROM "LiteLLM_SpendLogs"
            WHERE api_key = %s
        """, (litellm_key_id,))
        row = cur.fetchone()
    return {"total_calls": row[0] or 0, "total_tokens": row[1] or 0, "last_used_at": row[2]}
```

---

## 通用部署流程

每个 Sprint 完成后执行：

```bash
cd /Users/yaodongshi/Documents/develop/odoo/odoo19ee/team_ai_platform

# 1. 重建后端
docker compose build backend

# 2. 重启（仅后端，不影响 LiteLLM/Qdrant）
docker compose up --no-deps -d backend

# 3. 确认健康
curl -s http://localhost:8000/health
docker compose ps

# 4. 如果前端有变更，同时重建前端
docker compose build frontend && docker compose up --no-deps -d frontend
curl -s -o /dev/null -w "Frontend HTTP %{http_code}\n" http://localhost:3000
```

---

## 审批说明

本文档已完成，请审阅以下关键决策点：

### 决策点 1: LiteLLM Key 桥接策略
- **选项 A**（推荐）：`issue_key()` 直接调 LiteLLM `/key/generate`，返回 LiteLLM 的真实 `sk-` key
- **选项 B**：在 openai_compat 中间件层做 key 映射（延迟方案，灵活但复杂）
- **建议**：选项 A，实现简单，开发者拿到的 key 直接可用

### 决策点 2: Embedding 模型选择
- **选项 A**（推荐）：`text-embedding-3-small`（OpenAI，需 API key，效果好，成本低）
- **选项 B**：`nomic-embed-text`（本地部署，零成本，需要额外容器）
- **建议**：先用 A，后期可切换到 B

### 决策点 3: RAG 注入的上下文窗口保护
- 每次最多注入 3 个 Skill + 2 个 Knowledge 块
- 单个注入块最大字符数：1500
- 超出时优先保留相似度最高的
- **是否同意此限制？**

### 决策点 4: Git Webhook 激活时机
- **选项 A**：PR merge 到 main 时自动创建审批（需在 GitHub repo 配置 webhook）
- **选项 B**：开发者手动在平台 UI 提交（无需 webhook）
- **建议**：Sprint 3 同时支持两种方式

---

**请审批后回复"开始执行"，将立即从 Sprint 1 开始实现。**
