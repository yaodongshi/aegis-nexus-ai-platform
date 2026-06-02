# Team AI Platform 运维与交接总文档（合并版）

更新日期：2026-06-02  
定位：部署、验证、提测、验收、用户接入统一入口

## 1. 文档来源（已合并）

本文件合并并替代以下文档：
- DELIVERY_SUMMARY_2026-06-02.md
- LITELLM_GATEWAY_INTEGRATION_GUIDE.md
- LITELLM_RAG_VECTOR_STORE_RUNBOOK.md
- TEST_HANDOFF_2026-06-02.md
- FINAL_ACCEPTANCE_NOTICE_2026-06-02.md
- user-guide.md
- user-guide-v2.md

## 2. 快速开始

```bash
cd team_ai_platform
bash scripts/start.sh
bash scripts/healthcheck.sh
bash scripts/apply_litellm_gateway.sh check
```

## 3. 环境变量最小集

- LITELLM_MASTER_KEY
- LITELLM_SALT_KEY
- TEAM_AI_PLATFORM_ADMIN_TOKEN
- OPENAI_API_KEY（如使用 OpenAI）
- LITELLM_INTERNAL_BASE_URL

说明：`.env` 仅本地使用，不提交仓库。

## 4. 最小可用验收

1. 健康检查
- `scripts/healthcheck.sh` 返回 0

2. 网关鉴权行为
- `/v1/models` 未带 key 返回 401（预期）
- `/v1/models` 带 master key 返回 200（预期）

3. 模型别名可见
- 至少包含 `chat-default` 与 `embed-default`

## 5. RAG 向量闭环操作

- 入口：`/api/v1/knowledge/*`
- 依赖：LiteLLM embedding + Qdrant
- 目标：实现 ingest -> embedding -> search -> evolution 链路

建议顺序：
1. 导入样本知识
2. 触发检索验证
3. 观察日志与指标
4. 验证回写策略

## 6. 提测与回传模板

提测包含：
- 版本号与提交号
- 测试范围
- 环境信息
- 用例清单
- 回滚方案

回传要求：
- 通过/失败用例列表
- 失败日志与复现步骤
- 阻塞项等级（P0/P1/P2）

## 7. 客户端接入

- 数据面：OpenAI-compatible API
- 控制面：`/api/v1/*`
- 优先接入方式：能力别名（而非写死具体模型）

## 8. 常见问题

- 模型列表 401：优先检查 key 与 header。
- 同步失败：检查 runtime 同步日志与配置审计文件。
- 检索为空：检查 embedding 是否可用、Qdrant 连接与 collection。

## 9. 归档策略

历史阶段文档统一进入 `docs/archive/*`，不再作为当前执行基线。
