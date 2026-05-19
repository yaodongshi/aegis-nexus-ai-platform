# 调研报告：LiteLLM 同类开源替代框架（2026-05-14）

## 目标

评估是否存在“和 LiteLLM 同级、且完全开源免费、自托管可用”的框架，用于团队统一 Key、模型授权、网关治理、Skill/RAG 集成。

## 评估维度

- 许可证是否为标准开源许可证（MIT/Apache-2.0 等）
- 是否可完全自托管并免费使用核心能力
- 是否具备统一 LLM 网关能力（多模型路由、重试、回退、负载）
- 是否具备团队治理能力（虚拟 key、模型白名单、配额/限流、审计）
- 是否适配你的目标形态（前端像 cc-switch，后端像 LiteLLM）

## 候选与结论

### 1) Portkey AI Gateway

- 仓库: https://github.com/Portkey-AI/gateway
- 许可证: MIT
- 开源性: 核心网关开源可自托管
- 优势:
  - 路由、回退、重试、守护规则能力强
  - OpenAI 兼容入口成熟
  - 对多 provider 和 agent 框架适配较好
- 风险/注意:
  - README 明确部分高级治理特性在 hosted/enterprise 版本
  - 若追求“全部治理功能纯开源自托管”，需逐项核实
- 结论:
  - 是 LiteLLM 之外最强的开源候选之一，但在企业治理功能上存在“开源与商业版本边界”。

### 2) One-API

- 仓库: https://github.com/songquanpeng/one-api
- 许可证: MIT（项目声明含署名保留要求）
- 开源性: 可自托管，社区使用广泛
- 优势:
  - 多模型聚合、令牌管理、分组、配额、模型访问限制等功能完整
  - 与 OpenAI 格式兼容，部署简单，适合快速落地
- 风险/注意:
  - 生态与国际标准化程度不如 LiteLLM/Envoy 体系
  - 项目维护节奏和企业级治理深度需自行评估
- 结论:
  - 在“统一 key + 聚合分发”场景性价比很高，是务实可用的纯开源方案。

### 3) Envoy AI Gateway

- 仓库: https://github.com/envoyproxy/ai-gateway
- 许可证: Apache-2.0
- 开源性: CNCF/Envoy 生态，完全开源
- 优势:
  - 云原生架构强，适合大规模生产与 K8s
  - 两层网关模式、全局限流、认证路由等能力先进
  - 多 provider 支持持续增强
- 风险/注意:
  - 偏基础设施工程，落地门槛高于 LiteLLM/One-API
  - 控制台、团队管理、虚拟 key 产品化体验需要自己补
- 结论:
  - 适合强平台团队；若你要“快速做产品化平台”，初期成本较高。

### 4) Helicone

- 仓库: https://github.com/Helicone/helicone
- 许可证: Apache-2.0
- 开源性: 核心开源，可自托管
- 优势:
  - 观测与分析能力强，网关能力也在增强
- 风险/注意:
  - 重点偏 observability，不是以“全治理控制面”为第一优先
- 结论:
  - 很适合做观测层，不建议单独作为你平台的主网关替代。

### 5) Open WebUI（对照排除）

- 仓库: https://github.com/open-webui/open-webui
- 许可证: Open WebUI License（含品牌保留条款）
- 结论:
  - 更偏 UI 平台，不是 LiteLLM 同类网关治理框架，不建议作为主数据平面。

### 6) Apache APISIX（对照补充）

- 仓库: https://github.com/apache/apisix
- 许可证: Apache-2.0
- 开源性: 完全开源
- 结论:
  - 作为通用 API Gateway 非常强，AI 网关能力在增强；但不是“开箱即用的 LLM 治理平台”，需要较多二开。

## 关键判断：有没有“完全替代 LiteLLM 且同级成熟”的纯开源免费框架？

结论是：有接近者，但没有一个在“成熟度 + 开箱治理 + 多模型生态 + 产品化完整度”上全面明显优于 LiteLLM。

- 若以产品成熟和落地效率优先：LiteLLM 仍是第一选择。
- 若以纯 MIT 网关能力优先：Portkey Gateway 可重点评估。
- 若以极简快速上线和成本优先：One-API 可作为强备选。
- 若以云原生基础设施长期演进优先：Envoy AI Gateway 可作为中长期路线。

## 推荐落地策略（与你当前目标匹配）

### 方案 A（推荐）

- 主数据平面: LiteLLM
- 观测层: Langfuse 或 Helicone（二选一，建议 Langfuse）
- 控制面: 你自研（用户/团队/虚拟 key/模型授权/Skill-RAG 注册）

理由:

- 与你的目标最吻合：前端兼容所有 CLI，后端统一治理，Skill/RAG 云端同步。
- 迭代速度快，风险可控。

### 方案 B（备选）

- 主数据平面: Portkey Gateway
- 控制面: 你自研
- 观测层: Langfuse

适用:

- 团队更偏好 MIT 协议并接受部分企业能力边界。

### 方案 C（中长期）

- 主数据平面: Envoy AI Gateway + APISIX 组合
- 控制面: 你自研

适用:

- 追求超大规模、多集群、多云统一管控，但初期工程成本高。

## 建议决策

短中期请保持 V2 架构不变：

- LiteLLM 作为主网关数据平面
- 你的 Cloud Control Plane 作为产品核心
- Skill/RAG 统一注册与发布
- 本地 MCP/Agent 保持本地优先

并在架构中保留“网关可插拔接口”，以便后续按成本/能力替换为 Portkey 或 Envoy。
