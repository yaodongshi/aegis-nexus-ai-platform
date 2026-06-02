# 全流程傻瓜化配置与操作手册（从 0 到团队可用）

更新日期：2026-06-02  
目标：新手按本文一步一步操作，就能让团队用上 Key，并跑起自动进化闭环。

## 1. 你需要准备的东西

1. 一台能运行 Docker 的机器
2. 项目代码目录 `team_ai_platform`
3. 至少一个可用供应商 API Key（例如 OpenAI/DeepSeek 等）

## 2. 第 0 步：启动系统

```bash
cd team_ai_platform
bash scripts/start.sh
bash scripts/healthcheck.sh
```

打开页面检查：
- 前端：`http://localhost:3000`
- 管理后台：`http://localhost:3000/admin`

## 3. 第 1 步：管理员登录

1. 打开 `http://localhost:3000/admin`
2. 输入管理员 Token：`.env` 中 `TEAM_AI_PLATFORM_ADMIN_TOKEN`

## 4. 第 2 步：接入一个供应商（必须）

在“供应商管理”页签：
1. 填名称
2. 填类型
3. 填端点
4. 填 API Key
5. 点“新增供应商”
6. 点“同步网关列表”

完成后，平台才有可调用模型。

## 5. 第 3 步：发团队虚拟 Key（核心）

在“Key 管理”页签：
1. 标签：如“张三开发 Key”
2. 成员标识：如 `u_zhangsan`
3. 项目标识：如 `p_ai_platform`
4. 权限范围：`project:*`
5. 有效天数：`30`
6. 点击“生成 Key”
7. 复制 `key_secret` 发给成员

## 6. 第 4 步：成员接入（复制粘贴）

成员终端执行：

```bash
export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=<管理员发的key_secret>
```

可用性验证：

```bash
curl -sS http://localhost:8000/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## 7. 第 5 步：开启自动进化（程序自动跑）

启动自动工作流：

```bash
cd team_ai_platform
nohup scripts/evolution_auto_workflow.sh > /tmp/evolution_auto_workflow.log 2>&1 &
```

验证一次：

```bash
scripts/evolution_auto_workflow.sh --once
```

## 8. 第 6 步：日常运营（你只审批）

日常流程：
1. 成员在“闭环学习”上报任务复盘。
2. 程序自动生成草案并提交审批。
3. 管理员批准。
4. 程序自动 apply 生效。

审批命令：

```bash
# 查待审批
curl -sS "http://localhost:3000/api/approvals?limit=20&offset=0" \
  -H "X-Admin-Token: $TEAM_AI_PLATFORM_ADMIN_TOKEN"

# 批准
curl -sS -X POST "http://localhost:3000/api/approvals/<approval_id>/approve" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $TEAM_AI_PLATFORM_ADMIN_TOKEN" \
  -d '{"approver_id":"admin","reason":"approved"}'
```

## 9. 每日值班 5 步

1. `bash scripts/healthcheck.sh`
2. `curl http://localhost:3000/api/platform/runtime-health`
3. 查看 `/api/approvals` 是否有 pending
4. 批准必要审批单
5. 查看 `/api/skill-updates` 确认状态从 draft 变 applied

## 10. 故障处理（直接照做）

### 10.1 /api 返回 502

```bash
cd team_ai_platform
docker compose restart frontend
```

### 10.2 Invalid admin token

- 检查 `.env` 中 `TEAM_AI_PLATFORM_ADMIN_TOKEN`
- 确保请求头 `X-Admin-Token` 正确

### 10.3 自动流程没跑

```bash
ps -ef | rg evolution_auto_workflow | rg -v rg
tail -n 100 /tmp/evolution_auto_workflow.log
```

### 10.4 草案一直 draft

- 看是否存在对应审批单
- 看审批状态是否 approved
- 等待自动流程下一轮

## 11. 关键文件清单

- 主用户手册：`docs/USER_MANUAL.md`
- 自动进化审批手册：`docs/AUTO_EVOLUTION_LAST_APPROVAL_GUIDE.md`
- 本文档：`docs/FULL_IDIOT_PROOF_SETUP_AND_OPERATION.md`
- 自动流程脚本：`scripts/evolution_auto_workflow.sh`

## 12. 版本记录

- 2026-06-02 v1.0
  - 提供从部署、发 key、成员接入、自动进化到审批生效的完整傻瓜流程。
