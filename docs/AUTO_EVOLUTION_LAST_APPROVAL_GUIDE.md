# 自动自我进化（仅最后人工审批）傻瓜手册

更新日期：2026-06-02  
适用人群：不懂代码也要把平台跑起来的管理员

## 1. 你要达到的目标

你只做最后一步“批准”，其他步骤全部自动发生：
1. 成员做完任务并上报复盘。
2. 系统自动生成 Skill 更新草案（draft）。
3. 程序自动把草案提交为审批单（pending）。
4. 你在审批页点“同意”（approved）。
5. 程序自动把已同意草案应用生效（apply）。

## 2. 一次性配置（只做一次）

### 2.1 启动平台

```bash
cd team_ai_platform
bash scripts/start.sh
bash scripts/healthcheck.sh
```

### 2.2 准备管理员 Token

确认 `.env` 中存在：
- `TEAM_AI_PLATFORM_ADMIN_TOKEN`

### 2.3 启动自动进化工作流（后台循环）

```bash
cd team_ai_platform
nohup scripts/evolution_auto_workflow.sh > /tmp/evolution_auto_workflow.log 2>&1 &
```

说明：
- 该进程每 30 秒巡检一次。
- 会自动提交审批单，但不会自动批准。
- 只有你批准后才会自动生效。

## 3. 每天怎么操作（超简版）

1. 打开管理后台：`http://localhost:3000/admin`
2. 进入“闭环学习”，让成员上报任务复盘。
3. 进入审批列表接口对应页面/脚本，处理 pending。
4. 你批准后，不需要再手动 apply，程序会自动 apply。

## 4. 管理员最后一步审批

你只需执行以下命令批准（可集成到前端按钮流程）：

```bash
# 1) 查看待审批
curl -sS "http://localhost:3000/api/approvals?limit=20&offset=0" \
  -H "X-Admin-Token: $TEAM_AI_PLATFORM_ADMIN_TOKEN"

# 2) 批准某个审批单（把 approval-xxx 换成真实ID）
curl -sS -X POST "http://localhost:3000/api/approvals/approval-xxx/approve" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $TEAM_AI_PLATFORM_ADMIN_TOKEN" \
  -d '{"approver_id":"admin","reason":"reviewed and approved"}'
```

批准后，自动工作流会在下一轮巡检时自动 apply 对应 skill update。

## 5. 验证是否已生效

```bash
# 查看 skill update 状态
curl -sS "http://localhost:3000/api/skill-updates?limit=20&offset=0" \
  -H "X-Admin-Token: $TEAM_AI_PLATFORM_ADMIN_TOKEN"
```

状态说明：
- `draft`：草案待审批
- `applied`：已生效
- `synced`：已同步到指定目标
- `rejected`：已拒绝

## 6. 常见问题

### 6.1 为什么有草案但没有审批单？

处理：
1. 检查自动工作流是否运行：
```bash
ps -ef | rg evolution_auto_workflow | rg -v rg
```
2. 查看日志：
```bash
tail -n 100 /tmp/evolution_auto_workflow.log
```

### 6.2 为什么我批准了但还没生效？

处理：
1. 等待一个巡检周期（默认 30 秒）。
2. 再查 `skill-updates` 状态是否变为 `applied`。

### 6.3 想停止自动流程

```bash
pkill -f evolution_auto_workflow.py
```

## 7. 关键脚本说明

- `scripts/evolution_auto_workflow.py`
  - 核心自动流程程序。
- `scripts/evolution_auto_workflow.sh`
  - 启动包装脚本（自动加载 `.env` 与 `.venv`）。

## 8. 升级后检查

升级或重启后执行：

```bash
cd team_ai_platform
scripts/evolution_auto_workflow.sh --once
```

返回类似：

```json
{"draft_updates": 0, "approval_submitted": 0, "approved_and_applied": 0}
```

表示程序可正常连通并执行。
