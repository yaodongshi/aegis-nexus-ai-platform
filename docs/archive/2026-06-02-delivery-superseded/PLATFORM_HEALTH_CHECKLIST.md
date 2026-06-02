# Team AI Platform 当前环境一次性体检清单（2026-05-20）

本清单用于快速自查平台各关键能力、依赖、服务、数据、接口、脚本、测试等是否齐全可用。

---

## 1. 依赖与环境
- [x] Python >=3.11（建议 .venv 虚拟环境，已激活）
- [x] Node.js >=18（前端构建）
- [x] Docker & docker-compose
- [x] Qdrant >=1.5
- [x] requirements.txt 已安装
- [x] package.json 已安装

## 2. 关键服务
- [x] platform_backend（后端API服务）
- [x] litellm（模型网关）
- [x] qdrant（向量存储）
- [x] team_ai_mcp（MCP Server）
- [x] platform_frontend（治理页）
- [x] 所有服务 docker-compose ps 状态为 healthy/up

## 3. 主要脚本/工具
- [x] scripts/e2e_full_business_pipeline.sh（E2E全链路测试）
- [x] scripts/test_mcp_server_smoke.sh（MCP stdio烟测）
- [x] scripts/test_mcp_server_http_integration.sh（MCP HTTP烟测）
- [x] scripts/vector_store_management.sh（向量库管理）
- [x] scripts/aegis、aegis（CLI初始化）

## 4. 主要接口/端点
- [x] /api/runtime_config（客户端配置拉取）
- [x] /api/skill、/api/agent、/api/rag（主数据管理）
- [x] /api/model（模型管理）
- [x] /api/vector（向量库管理）
- [x] /api/mcp（MCP协议桥）

## 5. 数据与配置
- [x] .env 配置齐全
- [x] Qdrant 数据库可连接
- [x] LiteLLM STORE_MODEL_IN_DB=True
- [x] 各服务日志可查

## 6. 测试与验证
- [x] E2E全链路脚本通过
- [x] MCP stdio/HTTP烟测通过
- [x] 向量库管理脚本通过
- [x] CLI初始化无报错
- [x] 前端治理页可访问
- [x] 运行期审计文件已加入 .gitignore，仓库干净

## 7. 文档与可追溯性
- [x] README.md、PLATFORM_MANUAL.md、CRAZY_ITERATION_EXECUTION_PLAN_2026-05-20.md、QUICK_TEST_GUIDE.md 齐全
- [x] scripts/ 下脚本均有注释
- [x] 关键变更已 git commit/push

---

如有未打勾项，请按说明书逐项排查修复。