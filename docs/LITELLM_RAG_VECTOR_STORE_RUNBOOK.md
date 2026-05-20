# LiteLLM + RAG 向量库闭环运行手册

更新日期：2026-05-20

## 1. 目标

把 Team AI Platform 的 RAG 能力与 LiteLLM embedding 能力闭环，形成可执行的三类动作：
- Create Vector Store
- Manage Vector Stores
- Test Vector Store

本手册对应交付：
- 配置样例: `config/vector_store.example.yaml`
- 执行脚本: `scripts/vector_store_management.sh`

## 2. 架构闭环

```
Data Source (upload/git/session)
    -> Team AI Platform backend (/api/v1/knowledge/*)
    -> LiteLLM /v1/embeddings (text-embedding-v3)
    -> Qdrant collection (vector store)
    -> semantic search /api/v1/knowledge/search
    -> skill / agent evolution
```

关键职责：
- LiteLLM：统一 embedding 接口与密钥治理
- Qdrant：向量存储与 ANN 检索
- Team AI Platform：业务上下文、权限、审计、闭环动作编排

## 3. 前置条件

1. 服务在线
- LiteLLM: `http://localhost:4000`
- Qdrant: `http://localhost:6333`
- Platform frontend gateway: `http://localhost:3000`

2. 环境变量
- `LITELLM_MASTER_KEY`
- 可选：`QDRANT_URL`, `LITELLM_BASE_URL`, `EMBEDDING_MODEL`

3. 配置基线
- 复制 `config/vector_store.example.yaml` 为你自己的运行配置（如 `config/vector_store.yaml`）

## 4. Create Vector Store

创建向量集合（默认 1024 维，Cosine）：

```bash
cd team_ai_platform
bash scripts/vector_store_management.sh create knowledge_base 1024 Cosine
```

查看集合列表：

```bash
bash scripts/vector_store_management.sh list
```

## 5. Manage Vector Stores

查看集合统计：

```bash
bash scripts/vector_store_management.sh stats knowledge_base
```

写入文本点（自动通过 LiteLLM 生成 embedding）：

```bash
export LITELLM_MASTER_KEY=sk-your-key
bash scripts/vector_store_management.sh upsert-text knowledge_base doc_1 \
  "how to rotate hook secret" '{"source":"manual","team":"platform"}'
```

语义检索：

```bash
bash scripts/vector_store_management.sh search knowledge_base "rotate hook secret" 5
```

删除集合：

```bash
bash scripts/vector_store_management.sh delete knowledge_base
```

## 6. Test Vector Store

一键烟测（create + upsert + search + stats）：

```bash
export LITELLM_MASTER_KEY=sk-your-key
bash scripts/vector_store_management.sh test knowledge_base
```

成功判断：
- upsert 返回 `status: ok`
- search 返回至少 1 条结果
- stats 中 `points_count` 增加

## 7. 与平台知识接口闭环

除了直接管理 Qdrant，也应通过平台 API 完成业务闭环：

1. 上传文档入库
```bash
curl -X POST "http://localhost:3000/api/v1/knowledge/upload" \
  -H "Authorization: Bearer <user_or_admin_token>" \
  -F "file=@README.md" \
  -F "project_id=default" \
  -F "tags=runbook,vector"
```

2. 语义搜索
```bash
curl "http://localhost:3000/api/v1/knowledge/search?query=vector%20store&limit=5" \
  -H "Authorization: Bearer <user_or_admin_token>"
```

3. 查看统计
```bash
curl "http://localhost:3000/api/v1/knowledge/stats" \
  -H "Authorization: Bearer <user_or_admin_token>"
```

## 8. 运维建议

1. 统一 embedding 模型维度
- 若使用 `text-embedding-v3`，集合向量维度需保持 `1024`。

2. 集合命名规范
- 建议 `<team>_<domain>_<env>`，例如 `platform_docs_prod`。

3. 数据生命周期
- 定期清理低质量数据（quality_score 低）
- 对导入任务做批次标签，便于回滚

4. 安全
- 不在脚本内硬编码主密钥
- 使用环境变量注入 `LITELLM_MASTER_KEY`

## 9. 下一步（继续疯狂迭代）

- 增加 `vector store` 后端 API（collection CRUD + scoped ACL），从脚本迁移到平台原生管理页面。
- 将 `scripts/e2e_full_business_pipeline.sh` 增加向量库 create/manage/test 断言。
- 将知识入库质量阈值与 team rules 联动，自动控制可见性与召回范围。
