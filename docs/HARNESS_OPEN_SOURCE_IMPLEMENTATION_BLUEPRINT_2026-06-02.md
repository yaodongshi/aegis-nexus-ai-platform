# 开源 Harness 架构与实现蓝图（含 GitHub 代码路径）

更新日期：2026-06-02  
定位：回答“是否可直接抄 GitHub”，并给出可落地实现路径

## 1. 结论

- 可以借鉴开源架构与关键实现路径，但不建议直接抄整仓代码。
- 建议“接口兼容 + 设计复用 + 最小必要改写”模式。
- 原因：许可证边界、业务模型差异、治理流程差异、长期可维护性。

## 2. 可复用对象与不可复用对象

可复用：
- 运行时状态机
- 工具调度抽象
- 持久化执行与中断恢复模式
- 轨迹追踪数据结构

不可直接复用（需自建）：
- 组织治理模型（Team/Project/Policy/Approval）
- 网关策略与发布回滚机制
- 你们业务流程与权限边界

## 3. 开源候选与建议取材路径

## 3.1 LangGraph（优先）

建议取材：
- durable execution
- human-in-the-loop interrupt
- graph state persistence

用途：作为任务状态编排内核。

## 3.2 OpenAI Agents SDK（优先）

建议取材：
- guardrails
- sessions
- tracing
- sandbox agent

用途：作为多角色执行与工具调用框架。

## 3.3 OpenHands（参考）

建议取材：
- software-agent 运行模式
- 沙箱执行策略
- 开发任务回放机制

用途：强化工程任务执行体验。

## 3.4 CrewAI（选择性参考）

建议取材：
- Flow 编排风格
- Crew 与 Flow 组合模式

用途：业务流程可读性与编排简化。

## 4. 我们应该怎么“抄”

正确方式：
1. 抄结构，不抄耦合。
2. 抄接口抽象，不抄业务实现。
3. 抄状态机模型，不抄平台特定上下文。
4. 抄测试策略，不抄硬编码数据。

不建议：
- 直接复制大段业务逻辑到主仓。
- 忽略许可证条款与署名义务。
- 复制后不做契约与安全改造。

## 5. 目标架构（推荐）

- Layer A: Control Plane（你们现有平台，持续强化）
  - Policy / Approval / Audit / Capability Registry
- Layer B: Harness Runtime Adapter（新增）
  - 将外部运行时统一适配到你们事件协议
- Layer C: Execution Kernel（可替换）
  - LangGraph 或 OpenAI Agents SDK
- Layer D: Data Plane
  - LiteLLM + Qdrant

## 6. 代码落地路径（本仓）

建议新增模块：
- backend/app/harness/
  - runtime_adapter.py
  - plan_lock.py
  - role_executor.py
  - trace_bridge.py
- backend/app/routers/
  - harness.py
  - capability_runtime.py
- backend/app/schemas/
  - harness_events.py
  - plan_state.py
- backend/app/services/
  - strategy_rollout.py
  - strategy_evaluator.py

## 7. 三阶段实施路径

阶段 1（2 周）：
- 建立 harness adapter 与 plan lock。
- 接入基础 tracing。

阶段 2（2 周）：
- 增加策略灰度与回滚控制。
- 打通 capability contract。

阶段 3（4 周）：
- 上线自动评估与策略晋级。
- 完成经验模板沉淀与复用。

## 8. 验收标准

- 任务执行全链路可追踪、可重放。
- 任务状态只能由工具事件推进。
- 策略发布具备灰度、止损、回滚。
- 引擎可替换且业务层无侵入。
