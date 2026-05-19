# 🔌 RAG Data Import Strategy: Complete Supplement

**补充日期:** 2026-05-19  
**目的:** 解决"前期缺少数据，如何引导"的问题  
**参考:** RAG-Anything + LangChain + Qdrant 最佳实践

---

## 问题陈述

用户关注点：
> 关于日常工作 → RAG 自动学习，如果前期缺少数据我们应该也可以导入文档或者数据。

**核心需求:**
1. ✅ 日常工作自动学习（已有：git hooks）
2. ✅ 前期数据引导（**新增**：文档导入能力）
3. ✅ 轻量级（不建议从零开始，参考开源）

---

## 解决方案：三层数据导入

### Layer 1: Passive Auto-Collection (现有)
```
Git hooks → Commits, PRs, Issues
Chat → Slack, Teams 消息
System → Deployments, incidents, metrics

特点: 无需手动, 持续流入, 量大但质量参差
```

### Layer 2: Active Manual Import (新增 - Phase 0)
```
用户主动导入 → 文档、代码示例、参考资料
目的: 快速冷启动知识库

支持:
  - Web UI 上传 (drag & drop)
  - CLI 命令 (team ai knowledge upload)
  - API 集成 (第三方系统)
  - 批量导入 (CSV/JSON)
  - GitHub 自动抓取 (README, docs/)
```

### Layer 3: Scheduled Crawling (Phase 1+)
```
定期抓取 → 公开文档、wiki、博客
例子:
  - 公司内部 wiki
  - Confluence/Notion
  - 技术博客
  - GitHub 文档站点
```

---

## 推荐实现：LangChain + Qdrant 组合

### 为什么不选择 RAG-Anything？

| 对比项 | RAG-Anything | LangChain + Qdrant |
|--------|-------------|-------------------|
| 学习曲线 | 中等 | 较平坦 |
| 可定制性 | 中等 | 高 |
| 维护负担 | 中 | 低 |
| 生态支持 | 依赖项目状态 | 非常活跃 |
| 轻量级 | 否 | ✅ 是 |
| 与 Virtual Key 集成 | 需要适配 | 原生支持 |
| **推荐用途** | 需要完整平台 | **我们的选择** |

**为什么这样选？**
- LangChain: 文档加载器、文本分割已有最佳实践
- Qdrant: 开源、轻量、Docker 友好、无依赖
- 组合: 可最小化依赖，随着需要渐进扩展

---

## 快速启动：Week 1 数据导入方案

### 步骤 1: 准备工作 (1小时)

```bash
# 1. Docker Compose 启动 Qdrant
docker run -d \
  -p 6333:6333 \
  --name qdrant \
  qdrant/qdrant:latest

# 2. 安装 Python 依赖
pip install langchain sentence-transformers qdrant-client python-docx PyPDF2

# 3. 配置虚拟密钥 (前面 Milestone 0B 已有)
team auth login --type virtual-key
```

### 步骤 2: 导入现有文档 (2-3小时)

```bash
# Scenario 1: 从 GitHub 导入
team ai knowledge import-github \
  --owner company \
  --repo platform \
  --paths "docs/,README.md,ARCHITECTURE.md" \
  --tags "platform-core,v1"

# Scenario 2: 从本地导入
team ai knowledge upload ./docs/deployment-guide.pdf \
  --tags "deployment,guide"

# Scenario 3: 批量导入 CSV
cat > docs_to_import.csv << EOF
title,url,content,author,date,tags
"API Reference","https://...","{full content}","john","2024-01","api,reference"
"Deployment Guide","...","{full content}","jane","2024-01","deploy,guide"
EOF

team ai knowledge batch-import ./docs_to_import.csv \
  --tags "imported,q1-2024"
```

### 步骤 3: 验证数据质量 (30分钟)

```bash
# 检查导入状态
team ai knowledge info
# Output:
# Total entries: 527
# From git hooks: 45 (8%)
# From manual import: 482 (92%)
# Average quality: 0.84
# Search performance: 145ms

# 测试搜索
team ai knowledge search "how to deploy"
# 返回: 前 10 条相关文档 + 质量分数

# 检查重复率
team ai knowledge dedup-report
# 显示检测到的重复及处理结果
```

---

## 完整工作流：从导入到使用

```
Week 1: 冷启动阶段
  │
  ├─ Day 1: 整个团队导入现有文档
  │  └─ 目标: 500+ 质量条目
  │
  ├─ Day 2-3: Git hooks 启动
  │  └─ 自动收集新的 commits
  │
  └─ Day 4-5: 团队测试搜索
     └─ "这个问题我们以前处理过吗?"
        team ai knowledge search "null pointer"

Week 2+: 混合学习阶段
  │
  ├─ 自动收集: Git hooks + 新文档
  │
  ├─ 手动补充: 发现缺口 → 上传更多文档
  │
  └─ 系统优化: RAG 学会你的工作方式

Week 6+: 完整循环
  │
  ├─ 工作 → 自动收集
  │
  ├─ 模式识别 → 自动提议技能
  │
  └─ 团队反馈 → 系统自进化
```

---

## 数据量预估

### Phase 0 底线 (Week 3)

```
目标: 500+ 高质量知识条目

来源分布:
  - 手动导入 (Day 1)
    ├─ 公司 README × 5      → 50 条
    ├─ 部署指南 × 3         → 90 条
    ├─ API 文档 × 1         → 120 条
    ├─ 历史 issues × 100    → 150 条
    └─ Subtotal: ~410 条
  
  - Git hooks (Day 2-7)
    ├─ 50+ commits/day × 7  → ~100 条
    └─ Subtotal: ~100 条

总计: ~500 条 (满足条件 ✅)

质量分布:
  - 手动导入: avg 0.85 (高质量)
  - Git 自动: avg 0.65 (需要精炼)
```

### Phase 1 目标 (Week 6)

```
1000+ 条，包括:
  - 自动收集: 400 条
  - 手动补充: 200 条
  - 提议技能基础: 新增 400 条 (来自模式挖掘)
```

---

## 实现清单：Phase 0 Week 1

- [ ] **Day 1 (周一)**
  - [ ] 部署 Qdrant Docker
  - [ ] 实现 `team ai knowledge upload` 命令
  - [ ] 测试 PDF/DOCX 解析
  - [ ] 计划导入哪些文档

- [ ] **Day 2 (周二)**
  - [ ] 从 GitHub 导入 README + docs/
  - [ ] 上传历史文档 (deployment guides, API refs)
  - [ ] 实现质量评分逻辑
  - [ ] 验证 Qdrant 搜索性能

- [ ] **Day 3 (周三)**
  - [ ] 实现批量导入 API
  - [ ] 部署 deduplication 检查
  - [ ] 添加导入日志 & 监控
  - [ ] 性能测试

- [ ] **Day 4-5 (周四-五)**
  - [ ] Git hooks 部署
  - [ ] 团队培训
  - [ ] 测试端到端流程
  - [ ] 性能基准测试

---

## 集成点：与其他 Milestone 的关系

```
Milestone 0A (Week 1) - RAG Foundation
├─ Passive: Git hook auto-ingest
├─ Active: Document upload & import ✅ 本补充
└─ Unified: Qdrant + PostgreSQL

        ↓

Milestone 0B (Week 2) - Virtual Keys
├─ Auth: 用于文档导入的权限控制
└─ Scopes: read:knowledge, write:knowledge

        ↓

Milestone 0C (Week 3) - API Auth
└─ 保护所有导入端点

        ↓

Phase 1 (Week 4-6) - Pattern Mining
├─ Input: 充分的知识库 (来自 Active + Passive)
└─ Output: 技能提议
```

---

## API Reference：文档导入端点

### 1. 单文件上传

```http
POST /api/v1/knowledge/upload
Authorization: Bearer {virtual_key}
Content-Type: multipart/form-data

file: (binary)
tags: "deployment,guide"
title: "Deployment Guide" (optional)

Response (202 Accepted):
{
  "import_job_id": "job_20260519_abc123",
  "status": "processing",
  "estimated_time_seconds": 30
}
```

### 2. 批量导入

```http
POST /api/v1/knowledge/batch-import
Authorization: Bearer {virtual_key}
Content-Type: application/json

{
  "csv_url": "s3://bucket/docs.csv",
  "tags": ["team-docs", "q2-2024"],
  "skip_duplicates": true
}

CSV 格式:
title, content_url_or_inline, author, date, tags
"API Guide", "https://...", "john", "2024-01-15", "api,reference"
```

### 3. GitHub 导入

```http
POST /api/v1/knowledge/import-github
Authorization: Bearer {virtual_key}
Content-Type: application/json

{
  "owner": "company",
  "repo": "platform",
  "branch": "main",
  "paths": ["docs/", "README.md"],
  "tags": ["platform-core"]
}
```

### 4. 搜索知识库

```http
GET /api/v1/knowledge/search?query=deployment&limit=10
Authorization: Bearer {virtual_key}

Response:
{
  "query": "deployment",
  "results": [
    {
      "id": "kb_001",
      "content": "To deploy...",
      "quality_score": 0.92,
      "source": "api:upload",
      "source_url": "docs/deployment-guide.pdf",
      "tags": ["deployment", "guide"]
    }
  ]
}
```

---

## 安全考虑

### 访问控制

```
Virtual Key scopes:
  read:knowledge       → 可以搜索知识库
  write:knowledge      → 可以上传文档
  delete:knowledge     → 可以删除条目
  admin:knowledge      → 完全管理
```

### 数据隐私

```
- 上传前自动扫描 PII (邮箱、电话)
- 敏感文件标记 (internal, confidential)
- 审计日志: 谁导入了什么，何时
- 可选加密存储
```

---

## 参考资料

### 开源项目对比

| 项目 | 特点 | 适用场景 |
|------|------|--------|
| **RAG-Anything** | 完整平台，多格式支持 | 需要完整解决方案 |
| **LangChain** | 灵活框架，生态丰富 | **我们选择** |
| **LlamaIndex** | 轻量RAG，易集成 | 简单场景 |
| **Milvus** | 向量DB，可扩展 | 大规模场景 |

### 关键库

```python
# 文档加载
langchain.document_loaders  # PDF, DOCX, MD, 等

# 文本分割
langchain.text_splitter     # 智能分割

# 向量化
sentence_transformers       # 轻量级嵌入模型

# 向量存储
qdrant_client              # 开源向量 DB

# 数据库
sqlmodel                    # PostgreSQL ORM
```

---

## 下一步行动

### 这周 (Phase 0, Week 1)
1. [ ] 确认使用 LangChain + Qdrant 方案
2. [ ] 准备要导入的文档清单
3. [ ] 开始实现 `team ai knowledge upload`
4. [ ] 测试 PDF/DOCX 解析

### 下周 (Phase 0, Week 2)
1. [ ] 完成文档导入
2. [ ] 启用 Git hooks
3. [ ] 运行搜索性能测试
4. [ ] 团队验收测试

---

## 支持资源

- **LIGHTWEIGHT_RAG_DESIGN.md**: 完整技术设计 (5000+ 行)
- **IMPLEMENTATION_ROADMAP.md**: Milestone 0A 更新 (with upload API)
- **COMPLETE_SELF_EVOLUTION_SYSTEM_DESIGN.md**: Stage 1B 新增 (Active Data Import)

所有文档已更新。您现在拥有：
1. ✅ 自动学习方案 (Git hooks)
2. ✅ 手动导入方案 (文件上传)
3. ✅ 轻量级技术栈 (LangChain + Qdrant)
4. ✅ 完整实现指南 (Week 1 具体步骤)

**准备开始？让我们先从导入 5 个关键文档开始。**
