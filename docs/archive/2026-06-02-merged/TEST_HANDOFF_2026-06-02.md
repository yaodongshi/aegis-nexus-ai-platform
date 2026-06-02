# 测试交接单（2026-06-02）

## 版本基线

- 分支：`main`
- 提交：`786a632`
- 交付范围：LiteLLM 网关配置、启动脚本增强、最小可用校验与文档化。

## 测试通知模板（可直接发送）

```text
【提测通知】AI Platform LiteLLM 网关集成已完成最小可用闭环，请按测试交接单执行回归。

提测版本：main@786a632
测试文档：docs/TEST_HANDOFF_2026-06-02.md
关键报告：reports/min_check_2026-06-02.md

重点关注：
1) backend / gateway / qdrant / open-webui 基础可用性
2) LiteLLM 在未传 key 场景应返回 401（预期）
3) 配置 master key 后补跑 /v1/models 校验

回传内容：
- 用例通过/失败清单
- 失败时附请求参数、响应体与时间戳
- 复现步骤（最少 3 步）
```

## 测试前准备

```bash
cd team_ai_platform
bash scripts/start.sh
bash scripts/healthcheck.sh
```

## 必跑用例（P0）

### Case 1: Backend 健康检查

```bash
curl -i http://localhost:8000/health
```

期望：`HTTP 200`，body 包含 `{"status":"ok"}`。

### Case 2: LiteLLM 未带 key 的鉴权行为

```bash
curl -i http://localhost:4000/v1/models
```

期望：`HTTP 401`（这是预期行为，不是故障）。

### Case 3: Open WebUI 健康检查

```bash
curl -i http://localhost:9000/health
```

期望：`HTTP 200`，body 包含 `{"status":true}`。

### Case 4: Qdrant 健康检查

```bash
curl -i http://localhost:6333/healthz
```

期望：`HTTP 200`，body 包含 `healthz check passed`。

### Case 5: Gateway 健康检查

```bash
curl -i http://localhost:4000/health
```

期望：`HTTP 200`，body 包含 `{"status":"ok"}`。

## 条件用例（有密钥时执行）

如果本地已配置 `LITELLM_MASTER_KEY`：

```bash
export LITELLM_MASTER_KEY=<your_master_key>
bash scripts/apply_litellm_gateway.sh check
```

期望：`/v1/models` 可返回模型列表（非 401）。

## 故障分流

- backend 不通：先执行 `docker compose up -d backend` 后重试。
- litellm 返回 401：先确认是否故意未传 key；若需要模型列表，配置 `LITELLM_MASTER_KEY`。
- open-webui 启动慢：等待 30~60 秒后复测 `/health`。

## 回传格式

```text
[Case ID] PASS/FAIL
- Command:
- HTTP code:
- Response body:
- Timestamp:
- Notes:
```

## 参考资料

- `reports/min_check_2026-06-02.md`
- `docs/LITELLM_GATEWAY_INTEGRATION_GUIDE.md`
- `PLATFORM_HEALTH_CHECKLIST.md`
