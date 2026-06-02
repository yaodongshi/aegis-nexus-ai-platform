# P0 可执行任务清单（接口/页面/数据表/验收用例）

日期：2026-05-23  
目标：在 2 周内完成 P0 止血闭环，覆盖“新手可达、知识上传、导航收敛、网关配置落地、最小验证”。

---

## 0. 范围和完成定义

P0 只做 5 件事：
1. 创建 OpenSpec 变更骨架
2. 落地 LiteLLM 网关配置
3. 补齐环境变量与启动脚本
4. 编写实施与接入文档
5. 完成最小可用校验（MVP 验证）

完成定义（DoD）：
- 有可运行脚本
- 有可追踪配置
- 有接口级与页面级验收记录
- 有失败场景和回滚路径

---

## 1. 当前代码基线（用于定位改造点）

前端页面：
- frontend/src/pages/knowledge/index.tsx（当前仅文本新建，无文件上传）
- frontend/src/pages/settings/index.tsx（用户管理在 settings tab）
- frontend/src/pages/governance/index.tsx（有治理动作，但不是流程编排器）
- frontend/src/App.tsx（/users 重定向到 /settings，存在入口重复感知）

前端 API：
- frontend/src/lib/api.ts（/api/v1 与 /api 双基座）

后端 API：
- backend/app/api/v1/knowledge.py
- backend/app/api/v1/projects.py
- backend/app/api/v1/teams.py
- backend/app/main.py（所有路由挂载）

后端存储：
- backend/app/store.py（当前存在内存 + DB 混合路径）

架构契约：
- docs/V2_CONTROL_PLANE_API_CONTRACT.md
- docs/V2_DATA_MODEL_AND_MIGRATION_PLAN.md

---

## 2. 工作包 A：OpenSpec 变更骨架（D1）

## A1. 建立 change-id 和提案目录

任务：
- change-id：add-p0-usability-gateway-foundation
- 新建：
  - openspec/changes/add-p0-usability-gateway-foundation/proposal.md
  - openspec/changes/add-p0-usability-gateway-foundation/tasks.md
  - openspec/changes/add-p0-usability-gateway-foundation/specs/

验收：
- openspec validate add-p0-usability-gateway-foundation --strict 通过

## A2. 增量 spec 最小集合

建议新增/修改能力：
- knowledge-upload（新增）
- runtime-gateway-config（新增）
- onboarding-flow（新增）
- navigation-ia（修改）

每个 Requirement 必须包含至少 1 个 Scenario。

---

## 3. 工作包 B：LiteLLM 网关配置落地（D1-D3）

## B1. 配置生成与应用路径固化

涉及文件：
- backend/app/store.py（已存在 runtime config 能力，需校准字段）
- backend/app/routers/runtime_config.py（确认 apply/preview 输出）
- frontend/src/pages/settings/index.tsx（触发 apply）

接口清单：
- GET /api/v1/runtime/litellm-config
- POST /api/v1/runtime/litellm-config/apply
- GET /api/v1/runtime/client-config/{app}

任务：
- 明确输出目录（例如：team_ai_platform/litellm/runtime/）
- 产出 config.yaml + providers 映射
- 返回 apply 结果含：output_path、checksum、applied_at

验收用例：
- 用例 B1-1：preview 可返回可解析 YAML 片段
- 用例 B1-2：apply 后输出文件存在且可读
- 用例 B1-3：重复 apply 幂等（checksum 不变）

## B2. Provider 同步一致性

涉及文件：
- backend/app/store.py（providers -> litellm 映射）
- frontend/src/pages/providers/*（触发 sync）

任务：
- 建立 provider 字段最小映射（provider_id, model, api_base, api_key_ref, enabled）
- 失败 provider 不阻塞全局 apply（部分失败策略）

验收用例：
- 用例 B2-1：单 provider 可同步
- 用例 B2-2：一个 provider 失败时，返回 failed_items 列表且整体不中断

---

## 4. 工作包 C：知识上传入口 + 后端最小支持（D2-D6）

## C1. 前端上传入口

涉及文件：
- frontend/src/pages/knowledge/index.tsx
- frontend/src/lib/api.ts

任务：
- 新增上传按钮与文件选择
- 增加上传任务列表（pending/processing/success/failed）
- 允许手动重试失败任务

接口新增建议：
- POST /api/v1/knowledge/upload（multipart）
- GET /api/v1/knowledge/uploads?project_id=&status=
- POST /api/v1/knowledge/uploads/{upload_id}/retry

验收用例：
- 用例 C1-1：上传 txt/md 成功并进入文档列表
- 用例 C1-2：上传非法类型时返回明确错误
- 用例 C1-3：失败任务可重试并状态更新

## C2. 后端上传处理

涉及文件：
- backend/app/api/v1/knowledge.py
- backend/app/knowledge_schemas.py
- backend/app/store.py
- backend/app/main.py（新增路由注册）

数据表（P0 建议最小新增）：
- cp_knowledge_upload_job
  - upload_id (pk)
  - project_id
  - filename
  - content_type
  - status (pending/processing/success/failed)
  - error_message
  - created_by
  - created_at
  - updated_at

任务：
- 支持 txt/md/pdf 三类
- P0 先用同步入库 + 轻量任务状态（后续可异步化）
- 失败写 error_message

验收用例：
- 用例 C2-1：上传成功写入知识文档与上传任务表
- 用例 C2-2：解析失败时任务状态 failed 且 error_message 可见

---

## 5. 工作包 D：导航与入口收敛（D3-D4）

涉及文件：
- frontend/src/App.tsx
- frontend/src/layouts/MainLayout.tsx（如存在导航入口）
- frontend/src/pages/settings/index.tsx

任务：
- 主导航仅保留一个“用户与权限”入口
- /users -> /settings?tab=users 保留兼容跳转
- Settings 内 users tab 作为唯一用户管理承载

验收用例：
- 用例 D1：导航上不再出现重复入口
- 用例 D2：旧 URL /users 可正确落到 users tab

---

## 6. 工作包 E：新手可达路径（D4-D8）

涉及文件：
- frontend/src/pages/team/*
- frontend/src/pages/project/*
- frontend/src/pages/agent/index.tsx
- backend/app/api/v1/teams.py
- backend/app/api/v1/projects.py

任务：
- 新建团队后引导创建项目
- 新建项目后引导创建首个 agent
- 403/404 错误文案产品化（告诉用户下一步操作）

接口建议补充：
- GET /api/v1/onboarding/status
- POST /api/v1/onboarding/quickstart

验收用例：
- 用例 E1：新用户 5 分钟内跑通 Team->Project->Agent
- 用例 E2：无权限时提示“加入团队/切换团队/联系管理员”而非裸报错

---

## 7. 工作包 F：环境变量与启动脚本（D1-D3）

涉及文件（建议新增）：
- scripts/bootstrap_env.sh
- scripts/start_backend.sh
- scripts/start_frontend.sh
- scripts/check_p0.sh
- .env.example（补齐）

环境变量最小集：
- TEAM_AI_PLATFORM_DB_DSN
- TEAM_AI_PLATFORM_ADMIN_TOKEN
- LITELLM_MASTER_KEY
- LITELLM_BASE_URL
- QDRANT_URL
- OPENAI_API_KEY（或 provider 对应 key）

验收用例：
- 用例 F1：新环境执行 bootstrap 后可一键启动
- 用例 F2：缺失关键 env 时，脚本在启动前明确失败并提示缺哪个变量

---

## 8. 工作包 G：实施与接入文档（D5-D9）

涉及文件（建议新增）：
- docs/P0_IMPLEMENTATION_RUNBOOK_2026-05-23.md
- docs/P0_API_ACCEPTANCE_CASES_2026-05-23.md

文档必须覆盖：
- 本地/测试环境启动
- 网关 apply 与回滚
- 上传链路与故障排查
- 验收用例执行步骤

验收用例：
- 用例 G1：新同学按文档可在 30 分钟内跑通 P0

---

## 9. 最小可用校验（D9-D10）

## 9.1 API 校验清单

- [ ] /api/v1/runtime/litellm-config preview
- [ ] /api/v1/runtime/litellm-config/apply
- [ ] /api/v1/knowledge/upload
- [ ] /api/v1/knowledge/uploads
- [ ] /api/v1/knowledge/uploads/{id}/retry
- [ ] /api/v1/onboarding/status

## 9.2 前端校验清单

- [ ] 知识页可上传文件并看到状态
- [ ] /users 跳转 settings users tab
- [ ] 新手向导串起 Team->Project->Agent

## 9.3 观测校验清单

- [ ] 每次网关调用有 request_id
- [ ] 可记录 x-litellm-call-id 到平台日志
- [ ] 上传失败可在 UI 看到错误原因

---

## 10. 任务拆分与人天估算

- A OpenSpec 骨架：0.5 人天
- B 网关配置落地：2 人天
- C 知识上传链路：3 人天
- D 导航收敛：0.5 人天
- E 新手可达路径：2 人天
- F 脚本与环境：1 人天
- G 文档与验收：1 人天

合计：10 人天（1 个双周迭代可完成）

---

## 11. 风险与回滚

风险：
- 上传接口引入后端依赖变化
- 网关 apply 误覆盖线上配置
- 前端入口改动影响已有收藏链接

回滚：
- 所有新功能以 feature flag 控制
- apply 前备份现网 config，失败自动恢复
- /users 保留兼容跳转至少 2 个版本

---

## 12. 本周可直接开工项（今天起）

1. 先完成 A（OpenSpec 骨架）和 F（env + 脚本）
2. 并行推进 B（网关配置）和 C（上传接口后端）
3. 前端 D/C1 在后端接口 mock 好后立即接入
4. D+E+G 在周末前闭环，D10 完成最小验收
