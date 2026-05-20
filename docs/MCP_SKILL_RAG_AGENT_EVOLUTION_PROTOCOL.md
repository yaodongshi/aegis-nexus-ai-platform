# MCP-Skill-RAG-Agent 循环进化协议（执行版）

更新日期：2026-05-19  
目标：循环进化、自我进化（目标不变）

> ⚠️ **现状校正（2026-05-20）**
> 本协议描述的是**目标架构**。截至 commit `8965c45`，文档中所有 "MCP" 字样**仅指 REST 端点 `/api/skill-sync/mcp/*` 的命名**，并不是 Anthropic Model Context Protocol。
> 真实 MCP server 进程、stdio/SSE 协议、`tools/list`/`resources/list` 原语**均未实现**。
> 完整差距分析与落地路线图请参见：[`ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md`](./ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md)。

## 1. 协议总览

本协议定义团队级 AI 研发进化链路：

- MCP 负责 Skill 包的上传、下载、发布与同步
- 会话与 CLI 请求通过网关沉淀有效知识到 RAG
- RAG 规则总结后反哺 Skill
- Skill 通过生成规则 MCP 完成全团队同步
- 有效知识进入 RAG 后自动生成 Agent 工作流并持续优化

## 2. 核心对象

- SkillBundle：可上传/下载的技能包（含版本、标签、规则）
- KnowledgeUnit：会话或 CLI 产生的有效知识单元
- RuleSet：从 RAG 总结得出的可执行规则集
- AgentWorkflow：由规则驱动的可执行工作流草案/版本

## 3. 标准流程

### 3.1 Skill 包生命周期（MCP）

1. 开发或治理人员通过 MCP 上传 Skill 包。
2. MCP 校验包结构、版本、签名、风险等级。
3. 通过审核后写入 Skill Registry 并可下载。
4. 通过 sync_team_skills 对团队默认技能集生效。

### 3.2 会话与 CLI 到 RAG

1. 网关聚合会话与 CLI 请求统计。
2. 规则引擎执行有效知识过滤：可复用、可验证、低敏感。
3. 脱敏、切片、Embedding 后写入 Qdrant。

### 3.3 RAG 到 Skill

1. 周期任务扫描高频知识簇。
2. 生成 Skill 候选与更新建议。
3. 通过生成规则 MCP 生成团队同步规则。
4. 自动或半自动发布到团队技能集。

### 3.4 RAG 到 Agent

1. 识别稳定重复流程（高命中、高成功）。
2. 自动生成 AgentWorkflow 草案。
3. 运行后回收指标并更新到 RAG。
4. 基于反馈持续优化工作流版本。

## 4. MCP Tool 规范

必备 Tool：

- upload_skill_bundle(target_team, bundle)
- download_skill_bundle(skill_id, version)
- generate_team_skill_sync_rules(team_id)
- sync_team_skills(team_id, rule_set_id)
- ingest_effective_knowledge(source, payload)
- summarize_rag_to_skill(scope)
- generate_agent_workflow_from_rag(scope, constraints)
- optimize_agent_workflow(agent_id, feedback_window)

## 5. 有效知识判定

满足以下条件进入 RAG：

- 可复用：至少覆盖一类明确场景
- 可验证：有执行结果或回归证据
- 低敏感：通过脱敏规则
- 可归因：可追溯到来源与责任主体

## 6. 指标体系

### 6.1 输入指标

- 会话采集量
- CLI 采集量
- 有效知识通过率

### 6.2 转化指标

- RAG 到 Skill 候选数
- Skill 团队同步成功率
- RAG 到 Agent 工作流生成数

### 6.3 结果指标

- 技能命中率
- Agent 工作流成功率
- 平均修复时长下降比例

## 7. 审计与安全

- 所有 MCP Tool 调用必须审计
- 高风险动作必须走审批策略
- 敏感内容只存摘要与哈希

## 8. 验收门槛

- MCP 可完成 Skill 包上传/下载与团队同步
- 会话与 CLI 有效知识自动导入 RAG
- RAG 可稳定产出 Skill 更新建议
- RAG 可生成 AgentWorkflow 且可优化迭代
