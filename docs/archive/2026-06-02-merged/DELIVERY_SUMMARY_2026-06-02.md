# 交付总览（2026-06-02）

## 目标

本文件用于替代分散的交付说明，作为当前版本唯一入口。

## 当前验收基线

- 分支：main
- 最新提交：56ce0af（后续若有变更以 git log 为准）

## 必看文档（按阅读顺序）

1. 验收结论与回传模板
   - FINAL_ACCEPTANCE_NOTICE_2026-06-02.md
2. 测试交接执行单
   - TEST_HANDOFF_2026-06-02.md
3. 最小可用验证证据
   - ../reports/min_check_2026-06-02.md
4. 网关接入与运维
   - LITELLM_GATEWAY_INTEGRATION_GUIDE.md

## 关键运行命令

```bash
cd team_ai_platform
bash scripts/start.sh
bash scripts/healthcheck.sh
bash scripts/apply_litellm_gateway.sh check
```

## 文档减量说明

以下旧文档已归档，不再作为一线交付入口：

- archive/2026-06-02-delivery-superseded/PLATFORM_HEALTH_CHECKLIST.md
- archive/2026-06-02-delivery-superseded/PLATFORM_MANUAL.md
- archive/2026-06-02-delivery-superseded/PLATFORM_USER_GUIDE.md

## OpenSpec 归档说明

已归档的已完成变更（2026-06-02）：

- update-litellm-qdrant-alignment-v2
- update-admin-platform-overview
- update-key-ownership-management
- update-learning-loop-skill-sync
- update-litellm-gateway-ops
- update-unified-admin-entry

未归档（未完成）变更：

- update-skill-gitops-rag-autoloop
- add-complete-admin-management-platform
- update-solution-a-complete-design
