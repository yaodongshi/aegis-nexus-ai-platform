# AI-DevHub 私有化研发中枢总体方案（LiteLLM + Qdrant）

版本：v2.0（待审批）  
日期：2026-05-19  
适用范围：team_ai_platform 全量治理与实施

## 1. 文档目的

本方案以“产品经理 + 架构师 + 业务专家”联合视角，统一定义 AI-DevHub 的目标、能力边界、系统架构、实施路线、清理策略和验收标准。  
本次定稿以 LiteLLM + Qdrant 为唯一主线，Skill / Agent / MCP / RAG 全部围绕 LiteLLM 形成闭环。

## 2. 业务目标与成功标准

### 2.1 北极星目标

在企业私有化内网中，建设“可管控、可审计、可进化”的 AI 研发中枢：

- 所有 AI 请求统一走内网 LiteLLM 网关
- 所有研发知识统一沉淀到 Qdrant 向量库
- 所有规范通过 Skill + MCP 在生成前自动注入
- 所有行为可追溯到 key / user / agent / tool / session

### 2.2 12 周量化目标

- 网关收敛率：>= 95%（终端不直连外部模型）
- 合规拦截命中率：>= 90%（高风险规则场景）
- 技能复用率：>= 60%
- 平均问题修复时长缩短：>= 30%
- 研发知识沉淀增长：每周 >= 200 条可检索片段

## 3. 角色与价值

### 3.1 销售/顾问（需求前置）

- 收益：通过 Agent + Skill 快速形成结构化需求说明与实施草案
- 关键能力：行业模板、标准需求拆解、财务规则建议

### 3.2 开发（核心用户）

- 收益：编码时自动加载企业规范、历史修复策略、模块经验
- 关键能力：会话增强、技能推荐、冲突提案、自动导出技能包

### 3.3 架构/治理（平台 owner）

- 收益：统一模型入口、预算控制、审计追踪、策略治理
- 关键能力：虚拟密钥管理、模型与服务商治理、策略审批、运行态健康

### 3.4 运维/DevOps

- 收益：标准化拉取、重试、批处理、异常定位
- 关键能力：Hook 观测、失败清单导出、批次摘要、自动部署触发

## 4. 总体架构（目标态）

## 4.1 架构分层

- 接入与管控层（LiteLLM）
- 统一 API 网关
- 虚拟 Key 与配额控制
- 模型路由与回退
- 请求/响应日志回调

- 治理与编排层（FastAPI Control Plane）
- Provider / Model / Key / Policy / Approval 管理
- Skill 与 Agent 生命周期管理
- MCP Tool Registry 与权限策略
- 运行时配置编排（litellm config 生成与同步）

- 知识与检索层（Qdrant）
- 文档与代码片段向量化
- Metadata 过滤（module/framework/author/source）
- 技能检索、规范检索、历史修复检索

- 执行与反馈层（IDE/CLI/Hook）
- Cursor/Aider/Claude/OpenWebUI 统一接入
- Git Hook 事件与批量 Pull
- 失败重试、冲突提案、提案应用

## 4.2 闭环主路径

1. 研发请求进入 LiteLLM
2. LiteLLM 触发 Skill + MCP Tool 查询
3. Control Plane 从 Qdrant 检索并回填上下文
4. 模型生成结果返回客户端
5. 会话与结果写入日志与知识队列
6. 清洗/切片/Embedding 后写入 Qdrant
7. 新知识进入下一次生成上下文

## 4.3 会话知识与技能同步增强闭环（新增）

本节定义团队级“知识飞轮”增强机制：

- MCP Skill 包管理：通过 MCP 服务器统一上传/下载 Skill 包，作为团队技能分发唯一入口。
- 会话知识沉淀：开发过程中的高价值会话由网关侧汇总并进入 RAG。
- RAG 到 Skill 反哺：RAG 经过规则化总结后生成 Skill 更新建议。
- Skill 团队同步：Skill 通过“生成规则 MCP”执行全团队同步与版本发布。
- Agent 工作流生成：RAG 中的有效知识按规则自动生成或更新 Agent 工作流。
- CLI 知识采集：CLI 请求经网关统计后，对有效知识自动导入 RAG。

## 5. 关键能力设计（Skill / Agent / MCP / RAG）

### 5.1 Skill（规范与经验封装）

定义：可复用提示模板、规则清单、上下文注入策略。  

必备能力：

- Skill CRUD、版本、状态（draft/active/archived）
- Skill 检索（语义 + 标签）
- Skill 提案（来自 Hook / Task / Session）
- Skill 应用与回滚
- Skill 导出（claude-code/opencode 包）
- Skill MCP 上传/下载（统一包管理）
- Skill 团队规则同步（发布到团队默认技能集）

### 5.2 Agent（任务编排执行体）

定义：由 LiteLLM 驱动的执行编排单元，使用 Skill 与 MCP Tool 完成复合任务。  

必备能力：

- Agent 模板与实例（分析/编码/审查/部署）
- Agent-Tool 权限边界
- Agent 执行日志与指标（成功率/耗时/成本）
- Agent 结果回写知识库
- Agent 工作流自动生成（基于RAG规则）
- Agent 工作流持续优化（基于执行反馈）

### 5.3 MCP（工具协议总线）

定义：对内外工具能力的标准化暴露层，由 LiteLLM 统一调用。  

核心 Tool（首批）：

- query_odoo_standards(query_text)
- search_internal_knowledge(query, filters)
- get_openspec_template(module_name)
- trigger_opencode_deploy(env, module)
- upload_skill_bundle(target_team, bundle)
- download_skill_bundle(skill_id, version)
- generate_team_skill_sync_rules(team_id)
- sync_team_skills(team_id, rule_set_id)
- generate_agent_workflow_from_rag(scope, constraints)

治理要求：

- Tool Registry（版本、owner、风险等级）
- Tool 级权限策略（key / agent / role）
- Tool 调用审计（输入摘要/输出摘要/成本/失败原因）
- Tool 风险分级执行（只读/可写/部署级）

### 5.4 RAG（知识加工与检索）

定义：以 Qdrant 为中心的知识沉淀与检索系统。  

数据源：

- LiteLLM 会话日志
- CLI 网关请求统计摘要
- Git Hook 事件
- 技术文档与实施模板
- 缺陷工单与修复记录

加工流水线：

- 脱敏 -> 切片 -> 标签化 -> Embedding -> 入库
- 有效性评估 -> 规则总结 -> Skill候选生成 -> Agent工作流候选生成

检索策略：

- 基础语义检索 + Metadata 过滤
- 规则优先（Odoo 规范）
- 近期高成功案例加权

## 5.5 会话 -> RAG -> Skill -> Agent 飞轮规则（新增）

### 5.5.1 会话到 RAG

- 网关按会话聚合：问题、上下文、方案、结果、验证状态。
- 仅“有效知识”入库：通过规则校验（可复用、可验证、低敏感）。
- 入库最小标签：team_id、module、framework、source(cli/session/hook)、confidence。

### 5.5.2 RAG 到 Skill

- 规则引擎定期扫描高频知识簇并输出 Skill 候选。
- 候选 Skill 需包含：适用场景、禁用场景、示例输入输出、风险等级。
- 通过 MCP 规则工具触发团队同步发布。

### 5.5.3 RAG 到 Agent

- 当某类问题形成稳定流程后，自动生成 Agent 工作流草案。
- 草案包含：步骤图、工具依赖、回滚分支、成功判定。
- 运行数据回流 RAG，持续优化 Agent 工作流。

## 6. 产品信息架构（后台）

### 6.1 保留并强化（主线）

- 控制台（AI治理指标）
- 虚拟密钥
- 模型注册
- AI 服务商
- 技能平台
- 智能体
- 治理中心
- 观测中心
- 设置/个人中心

### 6.2 过渡保留（次主线）

- 知识库（升级为 Qdrant 资产视图）
- 代码仓库（保留为 Skill 同步来源）

### 6.3 清理/降级（非主线）

- 团队、项目、任务、插件：从一级导航移除，保留 API 兼容一段过渡期

## 7. 数据与安全治理

### 7.1 安全边界

- 禁止个人直连第三方模型
- 统一使用虚拟 key
- 高风险 Tool 需审批策略

### 7.2 审计模型

审计最小字段：

- user_id / key_id / agent_id / tool_name
- model / provider / token_usage / cost
- request_hash / response_hash / timestamp
- policy_hit / approval_id

### 7.3 隐私与合规

- 默认脱敏（IP/账号/密钥/客户名）
- 敏感上下文仅保存摘要与哈希
- 可配置保留周期与归档策略

## 8. 实施路线图

### Phase A（1-2 周）：主线收敛

- 后台导航收敛到 AI 主线
- 文档统一索引与版本治理
- 旧阶段文档归档

### Phase B（2-4 周）：闭环补齐

- MCP Tool Registry + 权限策略
- Agent 运行时指标与审计
- RAG 管线标准化
- MCP Skill 包上传/下载能力落地
- 会话知识入 RAG 与有效性规则落地

### Phase C（3-6 周）：进化增强

- Skill 自动提案与冲突处理增强
- 质量评估面板（召回率/命中率/采用率）
- 自动部署链路闭环
- RAG 规则总结自动生成 Skill 并团队同步
- RAG 自动生成 Agent 工作流并持续优化

## 9. 验收标准

### 9.1 功能验收

- Skill / Agent / MCP / RAG 全部可在 LiteLLM 链路下闭环跑通
- 控制台可查看关键治理指标与阻断告警
- 观测中心可完成批量运维闭环
- MCP 服务器可完成 Skill 上传/下载并可审计
- CLI 网关统计可导出有效知识并自动导入 RAG
- RAG 可驱动 Skill 更新与团队同步
- RAG 可驱动 Agent 工作流生成与优化

### 9.2 质量验收

- API 健康检查全部通过
- 文档索引可追溯到所有核心模块
- 关键路径均具备回滚与降级策略

## 10. 风险与应对

- 风险：遗留模块过多导致认知负担
  - 应对：一级导航收敛 + 兼容窗口 + 分期清退

- 风险：RAG 噪声高导致生成污染
  - 应对：引入分层标签、质量打分、低分隔离区

- 风险：MCP Tool 误用带来操作风险
  - 应对：分级授权 + 审批策略 + 强审计

## 11. 决策请求（审批项）

- 是否确认 LiteLLM + Qdrant 为唯一主线架构
- 是否确认“主线模块保留，通用协作模块降级”的产品策略
- 是否确认分三期实施并接受过渡期兼容策略

---

审批通过后，将进入执行版文档与任务清单（含 API 对齐矩阵、页面清理矩阵、灰度切换计划）。

补充执行协议：

- MCP_SKILL_RAG_AGENT_EVOLUTION_PROTOCOL.md
