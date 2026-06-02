# Team AI Platform 架构总文档（合并版）

更新日期：2026-06-02  
定位：架构现状分析 + 技术路线升级 + 产品化整改 + 复用策略 + 能力边界

## 1. 文档来源（已合并）

本文件合并并替代以下文档：
- ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md
- ARCHITECTURE_TECH_ROUTE_UPGRADE_2026-05-20.md
- PRODUCTIZATION_REMEDIATION_PLAN_7_ISSUES_2026-05-20.md
- SELF_EVOLVING_CONTROL_PLANE_REUSE_STRATEGY_2026-05-20.md
- LITELLM_CAPABILITY_BOUNDARY_REPORT_2026-05-20.md

## 2. 当前架构现实（As-Is）

### 2.1 你们已经具备的能力

- 控制面 API 基础能力：sessions、policies、approvals、learning、v2 key policy。
- 网关治理能力：LiteLLM 配置渲染、同步、校验、回滚审计。
- 知识闭环能力：RAG ingest、workflow 生成与优化、动作模板与 replay。
- 向量能力：Qdrant 已接入并参与知识检索路径。

### 2.2 你们当前主要缺口

- 缺少强约束执行状态机（任务“物理锁”）。
- 缺少角色解耦运行时（planner / executor / evaluator）。
- 缺少自动灰度比较与策略晋级机制。
- 缺少统一跨层追踪标准（前端、后端、网关）。
- 文档长期存在“目标态与现状态混写”问题，执行成本偏高。

## 3. 对 LiteLLM 的边界判断

LiteLLM 定位是网关层，不是业务控制面。

LiteLLM 应复用：
- 多模型接入与路由
- virtual key / team / user 访问控制
- 配额预算与调用日志
- 统一 API 兼容层

必须由你们自建并长期沉淀：
- 组织治理对象模型（Team/Project/Policy/Approval）
- 变更审批、发布、回滚流程
- 自进化策略引擎与经验沉淀
- 业务化工作台与可追责协作链路

## 4. 架构目标（To-Be）

采用“双层架构”：

- 控制层（Control Plane，自建）：
  - 策略、审批、发布、审计、能力别名（API 虚拟化）
- 执行层（Harness Runtime，可引入开源）：
  - 工作流编排、工具调度、状态持久化、HITL

## 5. API 虚拟化目标

目标：业务侧只面对稳定能力合同，不直接面向具体模型与供应商。

关键机制：
- 虚拟能力别名：chat-default、embed-default、reasoning-default
- 版本化能力合同：输入/输出 schema + SLA + 预算策略
- 能力级策略挂载：审批、限流、熔断、回滚

## 6. 演进路线（先进且可扩展）

### 阶段 A（2-4 周）：控制面稳定化 + Harness 接入

- 保留现有后端为唯一真理源。
- 引入开源运行时内核（LangGraph 或 OpenAI Agents SDK）。
- 打通执行前校验：环境、代码、任务三段检查。

### 阶段 B（2-4 周）：任务物理锁 + 可验证完成标准

- 新增 Task Plan Lock（严格状态机）。
- 禁止模型自由宣告“完成”，仅工具事件可更新状态。
- 自动回滚到最近可验证状态并记录轨迹。

### 阶段 C（4-8 周）：自动进化闭环

- 以成功率、延迟、成本、回滚率作为目标函数。
- 小流量 A/B 灰度自动比较策略。
- 策略晋级/降级自动化并沉淀经验模板。

## 7. 核心技术原则

- 先强约束，再自动化。
- 先能力合同，再模型自由。
- 先可回滚，再大规模放量。
- 所有关键写操作必须审计可追溯。

## 8. 验收标准

- 能力别名对外可稳定调用，业务不感知底层模型切换。
- 任意任务都可追溯执行轨迹，且可重放。
- 策略发布支持灰度、自动回滚、差异审计。
- 主要执行链路具备可观测指标与告警阈值。
