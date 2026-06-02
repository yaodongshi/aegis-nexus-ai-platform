# Team AI Platform 说明书（2026-05-20）

## 一、平台功能归属与分层说明

### 1.1 核心分层
- **平台后端（FastAPI + PlatformStore）**：主控所有业务数据、RAG/Skill/Agent/模型注册、同步、配置、治理页API。
- **LiteLLM**：仅负责模型网关（模型注册/路由/调用），不存储RAG/Skill/Agent等主数据。
- **Qdrant**：向量存储，平台后端通过API管理，供RAG/检索用。
- **MCP Server**：JSON-RPC stdio/HTTP协议桥接，提供tools/resources/stack detection等能力。
- **前端治理页（React+Vite）**：平台可视化管理与运维入口。
- **Docker Compose**：多服务编排，统一启动/管理。
- **脚本/CLI**：一键初始化、E2E、向量库管理、MCP烟测等。

### 1.2 主要功能归属
| 功能                | 归属/入口文件                                 |
|---------------------|---------------------------------------------|
| 模型注册/同步       | backend/app/services/litellm_sync.py         |
| RAG/Skill/Agent管理 | backend/app/store.py                         |
| 向量库管理          | scripts/vector_store_management.sh           |
| MCP协议/HTTP桥      | backend/mcp_server/server.py, http_app.py    |
| 技术栈识别          | backend/mcp_server/stack.py                  |
| 客户端配置生成      | backend/app/routers/runtime_config.py        |
| E2E全链路测试       | scripts/e2e_full_business_pipeline.sh         |
| MCP烟测             | scripts/test_mcp_server_smoke.sh             |
| CLI初始化           | scripts/aegis, aegis                         |
| Compose服务编排     | docker-compose.yml                           |
| 前端治理页          | frontend/（React+Vite）                      |

## 二、启动与管理

### 2.1 一键启动（推荐）
```bash
# 进入项目根目录
cd /Users/yaodongshi/Documents/develop/odoo/odoo19ee/team_ai_platform
# 启动所有服务（需先配置好.env、依赖、Qdrant等）
docker-compose up -d
```

### 2.2 主要服务/脚本说明
- **后端API服务**：见 docker-compose.yml，服务名如 platform_backend
- **LiteLLM**：见 docker-compose.yml，服务名如 litellm
- **Qdrant**：见 docker-compose.yml，服务名如 qdrant
- **MCP Server**：见 docker-compose.yml，服务名如 team_ai_mcp
- **前端治理页**：见 docker-compose.yml，服务名如 platform_frontend
- **E2E/烟测脚本**：scripts/e2e_full_business_pipeline.sh、scripts/test_mcp_server_smoke.sh
- **向量库管理**：scripts/vector_store_management.sh
- **CLI工具**：scripts/aegis、aegis

### 2.3 典型运维操作
- **模型同步**：由后端自动同步到LiteLLM，无需手动操作
- **RAG/Skill/Agent管理**：通过治理页或API
- **向量库增删查**：运行 scripts/vector_store_management.sh
- **MCP协议/HTTP桥测试**：运行 scripts/test_mcp_server_smoke.sh
- **E2E全链路测试**：运行 scripts/e2e_full_business_pipeline.sh
- **客户端配置拉取**：访问 /api/runtime_config 端点
- **服务状态检查**：docker-compose ps
- **日志查看**：docker-compose logs -f <服务名>

### 2.4 依赖与环境
- Python >=3.11（建议用 .venv 虚拟环境）
- Node.js >=18（前端）
- Docker & docker-compose
- Qdrant >=1.5
- 详见 requirements.txt、package.json、docker-compose.yml

### 2.5 常见问题与解答
- **Q: LiteLLM为什么看不到RAG/Skill/Agent？**
  - A: LiteLLM只负责模型注册与路由，RAG/Skill/Agent主数据在平台后端与Qdrant。
- **Q: 平台如何闭环？**
  - A: 闭环指调用链闭环（平台后端→LiteLLM→Qdrant→平台后端），不是所有数据同库。
- **Q: 如何扩展MCP工具/资源？**
  - A: 参考 backend/mcp_server/tools/、resources/ 目录，按MCP协议实现。

---

## 三、验证与测试

### 3.1 E2E全链路测试
```bash
bash scripts/e2e_full_business_pipeline.sh
```

### 3.2 MCP协议/HTTP桥烟测
```bash
bash scripts/test_mcp_server_smoke.sh
bash scripts/test_mcp_server_http_integration.sh
```

### 3.3 向量库管理
```bash
bash scripts/vector_store_management.sh list
```

### 3.4 CLI初始化
```bash
bash scripts/aegis init
```

---

## 四、参考文档
- docs/CRAZY_ITERATION_EXECUTION_PLAN_2026-05-20.md
- README.md
- QUICK_TEST_GUIDE.md
- 各 scripts/ 下脚本注释

---

如需详细接口/脚本/配置说明，请查阅上述文件或直接提问。