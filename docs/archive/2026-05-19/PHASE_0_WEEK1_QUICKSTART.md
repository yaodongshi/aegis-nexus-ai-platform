# Phase 0 Week 1 快速启动指南

**状态:** ✅ 代码实现完成  
**日期:** 2026-05-19  
**Milestone:** 0A - RAG Foundation  

---

## 📋 检查清单

### ✅ 已完成的代码

- [x] RAG Manager (`backend/app/core/rag_manager.py`) - 向量化、搜索、去重、质量评分
- [x] 数据库初始化 (`backend/app/core/db_init.py`) - PostgreSQL 表设计
- [x] 增强的知识 API (`backend/app/api/v1/knowledge_rag.py`) - 文件上传、搜索、导入
- [x] 依赖更新 (`backend/requirements.txt`) - RAG 所需的所有库
- [x] Git Hook 脚本 (`scripts/git-hook-post-commit.sh`) - 自动提交摄入
- [x] Hook 安装脚本 (`scripts/install-git-hooks.sh`) - 快速部署
- [x] Docker Compose Phase 0 配置 (`docker-compose.phase0.yml`) - 一键部署
- [x] 主应用集成 (`backend/app/main.py`) - 路由注册

---

## 🚀 快速启动 (5分钟)

### Step 1: 启动 Docker 服务

```bash
cd /Users/yaodongshi/Documents/develop/odoo/odoo19ee/team_ai_platform

# 启动所有服务
docker-compose -f docker-compose.phase0.yml up -d

# 检查状态
docker-compose -f docker-compose.phase0.yml ps
```

**预期输出:**
```
NAME                        STATUS
team_ai_postgres_phase0     Up (healthy)
team_ai_qdrant_phase0       Up (healthy)
team_ai_redis_phase0        Up (healthy)
team_ai_api_phase0          Up (healthy)
```

### Step 2: 验证 RAG API

```bash
# 健康检查
curl http://localhost:8000/health

# 获取知识库统计
curl http://localhost:8000/api/v1/knowledge/stats \
  -H "Authorization: Bearer admin-token-dev-phase0"

# 预期响应:
# {
#   "collection_name": "knowledge_base",
#   "vector_count": 0,
#   "embedding_dim": 384,
#   "distance_metric": "cosine",
#   "status": "operational"
# }
```

### Step 3: 上传测试文档

```bash
# 创建测试文档
cat > /tmp/test_doc.md << 'EOF'
# 部署指南

## 前置条件
- Docker 已安装
- Python 3.10+

## 步骤
1. 克隆仓库
2. 安装依赖
3. 配置环境变量
4. 启动服务

## 常见问题
Q: 如何禁用 Git hooks?
A: touch ~/.team/disable-git-hooks

EOF

# 上传文档
curl -X POST http://localhost:8000/api/v1/knowledge/upload \
  -H "Authorization: Bearer admin-token-dev-phase0" \
  -F "file=@/tmp/test_doc.md" \
  -F "project_id=test-project" \
  -F "tags=deployment,guide"

# 响应示例:
# {
#   "import_job_id": "job_20260519_120000_abc123",
#   "status": "processing",
#   "estimated_chunks": 3,
#   "check_status_url": "/api/v1/knowledge/import-status/job_20260519_120000_abc123"
# }
```

### Step 4: 测试语义搜索

```bash
# 等待 2-3 秒后测试搜索
sleep 3

curl "http://localhost:8000/api/v1/knowledge/search?query=如何启动服务&limit=5" \
  -H "Authorization: Bearer admin-token-dev-phase0"

# 预期返回相关文档
```

---

## 📥 批量导入文档

### 导入多个文档

```bash
# 创建多个测试文档
mkdir -p /tmp/docs_to_import

cat > /tmp/docs_to_import/api-guide.md << 'EOF'
# API 指南

## GET /api/v1/knowledge/search
搜索知识库

### 参数
- query: 搜索词
- limit: 返回数量
- min_quality: 最小质量分数

### 响应
返回匹配的知识条目列表
EOF

cat > /tmp/docs_to_import/troubleshooting.md << 'EOF'
# 故障排查

## 问题：连接超时
解决方案：检查网络连接

## 问题：Docker 无法启动
解决方案：检查端口占用
EOF

# 一次上传多个文件
for file in /tmp/docs_to_import/*; do
  echo "上传: $file"
  curl -X POST http://localhost:8000/api/v1/knowledge/upload \
    -H "Authorization: Bearer admin-token-dev-phase0" \
    -F "file=@$file" \
    -F "project_id=docs-seed" \
    -F "tags=documentation"
  sleep 1
done
```

---

## 🔗 安装 Git Hooks

### 安装到当前仓库

```bash
# 安装 hook
chmod +x scripts/install-git-hooks.sh
./scripts/install-git-hooks.sh .

# 配置虚拟密钥
mkdir -p ~/.team
cat > ~/.team/config.json << 'EOF'
{
  "virtual_key": "admin-token-dev-phase0",
  "api_url": "http://localhost:8000"
}
EOF
```

### 验证 Hook 工作

```bash
# 做一个测试提交
cd /Users/yaodongshi/Documents/develop/odoo/odoo19ee
echo "Test commit for RAG ingestion" > test_rag.txt
git add test_rag.txt
git commit -m "test: RAG auto-ingestion hook"

# 检查 hook 日志
tail -f ~/.team/git-hooks.log

# 应该看到类似日志:
# [2026-05-19 12:00:00] ✅ 提交已发送到 RAG (提交: abc123def456)
```

---

## 📊 第一周目标 (Success Criteria)

### Day 1-2: 基础设施
- [ ] Docker 服务全部运行
- [ ] 数据库表已创建
- [ ] API 健康检查通过
- [ ] Qdrant 可用

### Day 3-4: 数据导入
- [ ] 成功上传至少 3 个文档
- [ ] 知识库已有 10+ 条目
- [ ] 搜索延迟 <200ms
- [ ] 质量评分计算正确

### Day 5: Git Hooks
- [ ] Hook 脚本部署到 >90% 开发机
- [ ] 至少 50 个提交已自动摄入
- [ ] 去重率 >95%
- [ ] 最终：500+ 知识条目

---

## 🔍 监控和调试

### 查看 API 日志

```bash
docker logs team_ai_api_phase0 -f
```

### 连接到 PostgreSQL

```bash
docker exec -it team_ai_postgres_phase0 psql -U postgres -d team_ai_platform

# 查看知识库表
SELECT COUNT(*) FROM knowledge_base;
SELECT title, quality_score, source_type FROM knowledge_base LIMIT 5;
```

### 检查 Qdrant

```bash
# 查看集合信息
curl http://localhost:6333/collections/knowledge_base

# 查看向量数量
curl http://localhost:6333/collections/knowledge_base/count
```

### 检查 Redis

```bash
docker exec -it team_ai_redis_phase0 redis-cli

> KEYS *
> GET knowledge:*
```

---

## ⚠️ 常见问题

### Q: 如何重置数据库？

```bash
docker-compose -f docker-compose.phase0.yml down -v
docker-compose -f docker-compose.phase0.yml up -d
```

### Q: API 500 错误？

检查依赖是否安装：
```bash
docker exec team_ai_api_phase0 pip install -r requirements.txt
```

### Q: Qdrant 集合未创建？

手动初始化：
```bash
docker exec team_ai_api_phase0 python -m app.core.db_init
```

### Q: Git hook 未触发？

检查权限：
```bash
ls -la .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

### Q: 向量化很慢？

这是正常的 (first run)。检查 GPU：
```bash
docker exec team_ai_api_phase0 python -c "import torch; print(torch.cuda.is_available())"
```

---

## 📈 预期进展

```
Week 1 Progress:
Day 1 ├─ ✅ Docker 启动
      ├─ ✅ 数据库初始化
      └─ ✅ API 运行

Day 2 ├─ ✅ 首批文档导入 (50+)
      ├─ ✅ 搜索功能验证
      └─ ✅ 质量评分确认

Day 3 ├─ ✅ 更多文档上传 (200+)
      ├─ ✅ 去重测试
      └─ ✅ 性能基准测试

Day 4 ├─ ✅ Git hook 部署
      ├─ ✅ 自动摄入运行
      └─ ✅ 团队测试

Day 5 ├─ ✅ 最终验收 (500+ 条目)
      ├─ ✅ 性能优化
      └─ ✅ 文档完成

Result: ✅ Milestone 0A 完成
```

---

## 🎯 下一步 (Milestone 0B)

完成 Milestone 0A 后，开始：

- **Week 2:** Virtual Keys + CLI 实现
- **Week 3:** API 认证系统
- **Week 4+:** Pattern Mining + Skills Generation

---

## 📞 支持

遇到问题？

1. 检查日志: `docker logs team_ai_api_phase0`
2. 查看调试指南: 本文档上面的部分
3. 重置环境: `docker-compose -f docker-compose.phase0.yml down -v && up -d`

---

**准备好了吗？现在就开始！** 🚀
