# Team AI Platform 文档索引（对齐版）

更新日期：2026-05-19  
适用架构：LiteLLM + Qdrant（Skill / Agent / MCP / RAG 闭环）

## 1. 主文档（优先阅读）

- AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md
  - 产品、架构、业务一体化主方案
  - 目标、能力边界、路线图、验收标准
- API_AND_FEATURE_CLEANUP_MATRIX.md
  - 功能与 API 收敛/过渡/下线矩阵
  - 前后端清理节奏与验收标准
- COMPATIBILITY_MODULE_DECOMMISSION_TIMELINE.md
  - 兼容模块分阶段下线时间表
  - Phase A/B/C 执行与验收窗口
- MCP_SKILL_RAG_AGENT_EVOLUTION_PROTOCOL.md
  - MCP-Skill-RAG-Agent 循环进化执行协议
  - 会话/CLI 知识入 RAG 与团队同步规则

## 2. 活跃设计文档（当前仍有效）

- DESIGN.md
- EXECUTION.md
- ITERATION_PLAN.md
- FRONTEND_RAG_SKILL_SEPARATION.md
- LIGHTWEIGHT_RAG_DESIGN.md
- RAG_DATA_IMPORT_STRATEGY.md
- V2_CONTROL_PLANE_API_CONTRACT.md
- V2_DATA_MODEL_AND_MIGRATION_PLAN.md
- VIRTUAL_KEY_CLI_IMPLEMENTATION_SPEC.md
- user-guide.md
- user-guide-v2.md

## 3. 归档文档（历史参考，不作为当前执行基线）

归档目录：archive/2026-05-19/

已归档（原因：阶段性总结、历史选型、重复叙述）：

- COMPLETE_ITERATION_GUIDE.md
- COMPLETE_SELF_EVOLUTION_SYSTEM_DESIGN.md
- GATEWAY_ALTERNATIVES_RESEARCH_20260514.md
- IMPLEMENTATION_ROADMAP.md
- SOLUTION_A_COMPLETE_DESIGN.md
- ../../docs/archive/2026-05-19/DASHBOARD_ANALYSIS_SUMMARY.md
- ../../docs/archive/2026-05-19/EXECUTION_REPORT_2026_05_19.md
- ../../docs/archive/2026-05-19/PHASE_0_EXECUTION_AUTHORIZATION.md
- ../../docs/archive/2026-05-19/PHASE_0_WEEK1_EXECUTION_REPORT.md
- ../../docs/archive/2026-05-19/PHASE_0_WEEK1_QUICKSTART.md
- ../../docs/archive/2026-05-19/PHASE_1_5_SUMMARY.md
- ../../docs/archive/2026-05-19/STATUS_READY_TO_DEPLOY.md

## 4. 文档治理规则

- 新增架构级文档必须先在主方案中登记。
- 新增接口文档必须与 API 合同文档同步。
- 阶段性报告默认进入 archive，不进入主目录。
- 主目录只保留“当前可执行”文档。
