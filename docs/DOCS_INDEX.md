# Team AI Platform 文档索引（合并版）

更新日期：2026-06-02  
适用架构：LiteLLM + Qdrant + 可插拔 Harness Runtime

## 1. 当前执行基线（优先阅读）

- MASTER_ARCHITECTURE_ANALYSIS_AND_TARGET_2026-06-02.md
  - 架构现状、边界、目标架构与演进路线
- MASTER_EXECUTION_PLAN_2026-06-02.md
  - 分阶段任务、验收、风险与 DoD
- MASTER_OPERATIONS_AND_HANDOFF_2026-06-02.md
  - 部署、提测、验收、用户接入统一入口
- USER_MANUAL.md
  - 统一用户手册（后续持续迭代）
- BUSINESS_ARCH_TECH_ROUTE_MATRIX_TOPOLOGY.md
  - 业务架构、技术路线、矩阵与拓扑统一文档
- HARNESS_OPEN_SOURCE_IMPLEMENTATION_BLUEPRINT_2026-06-02.md
  - 开源 Harness 取材路径与本仓落地蓝图
- HARNESS_RUNTIME_MIGRATION_RUNBOOK_2026-06-02.md
  - Harness Runtime 迁移步骤、发布检查与回滚演练入口
- HARNESS_FINAL_ACCEPTANCE_REVIEW_2026-06-02.md
  - Harness Runtime 最终验收评审结论（架构/产品）

## 2. 保留的专题文档（仍有效）

- HARNESS_OPEN_SOURCE_ASSESSMENT_2026-06-02.md
- HARNESS_OPEN_SOURCE_LICENSE_COMPLIANCE_CHECKLIST_2026-06-02.md

## 3. 归档目录（历史文档）

- archive/2026-06-02-merged/
  - ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md
  - ARCHITECTURE_TECH_ROUTE_UPGRADE_2026-05-20.md
  - PRODUCTIZATION_REMEDIATION_PLAN_7_ISSUES_2026-05-20.md
  - SELF_EVOLVING_CONTROL_PLANE_REUSE_STRATEGY_2026-05-20.md
  - LITELLM_CAPABILITY_BOUNDARY_REPORT_2026-05-20.md
  - ITERATION_PLAN.md
  - CRAZY_ITERATION_EXECUTION_PLAN_2026-05-20.md
  - P0_EXECUTION_TASKLIST_2026-05-23.md
  - DELIVERY_SUMMARY_2026-06-02.md
  - LITELLM_GATEWAY_INTEGRATION_GUIDE.md
  - LITELLM_RAG_VECTOR_STORE_RUNBOOK.md
  - TEST_HANDOFF_2026-06-02.md
  - FINAL_ACCEPTANCE_NOTICE_2026-06-02.md
  - user-guide.md
  - user-guide-v2.md

## 4. 清理说明（本轮）

- 已删除主目录历史专题文档 12 份，保留可追溯历史于 `docs/archive/*`。
- 用户手册统一收敛到 `USER_MANUAL.md`，后续不再新增平行 user-guide。
- 业务架构与技术路线统一收敛到 `BUSINESS_ARCH_TECH_ROUTE_MATRIX_TOPOLOGY.md`。

## 5. 历史归档目录

- archive/2026-05-19/
- archive/2026-06-02-delivery-superseded/

## 6. 文档治理规则

- 主目录只保留当前执行基线与高价值专题文档。
- 同主题新增文档优先合并到已有主文档，避免平行文档扩散。
- 阶段性报告与临时执行单默认归档。
- 所有架构与执行变更必须同步 OpenSpec 变更与任务清单。
