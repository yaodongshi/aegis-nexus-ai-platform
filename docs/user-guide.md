# Team AI Platform 用户手册

> 版本：v1.0 · 适用于 team_ai_platform 当前主线版本

---

## 目录

1. [快速访问地址](#1-快速访问地址)
2. [管理员 Token 配置](#2-管理员-token-配置)
3. [添加 LLM 厂商 API Key](#3-添加-llm-厂商-api-key)
4. [重启 LiteLLM 使配置生效](#4-重启-litellm-使配置生效)
5. [生成内部虚拟 Key（用户分发）](#5-生成内部虚拟-key用户分发)
6. [在 Open WebUI 中使用](#6-在-open-webui-中使用)
7. [在 Codex CLI 中使用](#7-在-codex-cli-中使用)
8. [在 OpenCode 中使用](#8-在-opencode-中使用)
9. [在 Claude Code 中使用](#9-在-claude-code-中使用)
10. [常见问题](#10-常见问题)

---

## 1. 快速访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Provider 管理台 | http://localhost:8000/provider-console | 添加/管理 LLM 厂商 Key |
| API 文档（Swagger） | http://localhost:8000/docs | 完整接口文档 |
| LiteLLM 网关 | http://localhost:4000/v1 | 统一 OpenAI 兼容端点 |
| Open WebUI 聊天 | http://localhost:9000 | 团队聊天界面 |

---

## 2. 管理员 Token 配置

所有管理操作（添加厂商 Key、生成虚拟 Key）均需要 Admin Token 认证。

### 2.1 默认 Token

开发环境默认 Token：`test-admin-token-secret`

### 2.2 修改为生产 Token

编辑项目根目录 `.env` 文件：

```env
TEAM_AI_ADMIN_TOKEN=your-long-random-secret-here
```

然后重启 backend：

```bash
docker compose restart backend
```

### 2.3 在管理台界面输入 Token

访问 http://localhost:8000/provider-console，页面右上角输入 Admin Token 并点击「验证」。

---

## 3. 添加 LLM 厂商 API Key

### 方式一：通过 Web 管理台（推荐）

1. 打开 http://localhost:8000/provider-console
2. 输入 Admin Token，点击「验证」
3. 点击「+ 添加供应商」
4. 在弹窗中选择预设厂商（如 `deepseek`），系统会自动填充接口地址
5. 填写该厂商的 API Key
6. 点击「保存」

系统会自动将配置写入 LiteLLM，**重启 litellm 后**即可通过网关调用该厂商的模型。

---

### 方式二：通过 curl 命令行

**以 DeepSeek 为例：**

```bash
curl -s -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: test-admin-token-secret" \
  -d '{
    "name": "DeepSeek",
    "preset_key": "deepseek",
    "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx",
    "base_url": "https://api.deepseek.com/v1"
  }' | python3 -m json.tool
```

**以 OpenAI 为例：**

```bash
curl -s -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: test-admin-token-secret" \
  -d '{
    "name": "OpenAI",
    "preset_key": "openai",
    "api_key": "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx",
    "base_url": "https://api.openai.com/v1"
  }' | python3 -m json.tool
```

**其他厂商参考（修改 name / preset_key / api_key / base_url）：**

| 厂商 | preset_key | 默认 base_url |
|------|-----------|---------------|
| Anthropic | `anthropic` | https://api.anthropic.com |
| Google Gemini | `gemini` | https://generativelanguage.googleapis.com/v1beta |
| 智谱 AI | `zhipu` | https://open.bigmodel.cn/api/paas/v4 |
| 阿里百炼 | `aliyun_bailian` | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| Kimi (月之暗面) | `kimi` | https://api.moonshot.cn/v1 |
| 阶跃星辰 StepFun | `stepfun` | https://api.stepfun.com/v1 |
| MiniMax | `minimax` | https://api.minimax.chat/v1 |
| 豆包 (字节) | `doubao` | https://ark.cn-beijing.volces.com/api/v3 |
| SiliconFlow | `siliconflow` | https://api.siliconflow.cn/v1 |
| OpenRouter | `openrouter` | https://openrouter.ai/api/v1 |

> 完整预设列表：`GET /api/providers/presets`

---

### 3.1 发现并同步该厂商的全量模型

添加供应商后，可以让系统自动拉取该厂商所有可用模型：

```bash
# 先查询刚添加的供应商 ID
curl -s http://localhost:8000/api/providers \
  -H "X-Admin-Token: test-admin-token-secret" | python3 -m json.tool

# 替换 {provider_id} 为实际 ID
curl -s -X POST http://localhost:8000/api/providers/{provider_id}/discover-models \
  -H "X-Admin-Token: test-admin-token-secret" | python3 -m json.tool
```

---

## 4. 重启 LiteLLM 使配置生效

每次添加、修改或删除供应商后，需重启 LiteLLM 网关让新配置生效：

```bash
cd /path/to/team_ai_platform
docker compose restart litellm
```

验证模型列表是否更新：

```bash
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-team-master-change-me" | python3 -m json.tool
```

---

## 5. 生成内部虚拟 Key（用户分发）

虚拟 Key（格式：`sk-virtual-xxxxxxxxxxxx`）用于向团队成员分发访问权限，**无需暴露真实厂商 API Key**。

### 5.1 生成虚拟 Key

```bash
curl -s -X POST http://localhost:8000/api/keys/issue \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: test-admin-token-secret" \
  -d '{
    "label": "张三的开发 Key",
    "expires_days": 30
  }' | python3 -m json.tool
```

返回示例：

```json
{
  "id": "key_abc123",
  "key": "sk-virtual-a1b2c3d4e5f6g7h8",
  "label": "张三的开发 Key",
  "created_at": "2026-05-11T10:00:00Z",
  "expires_at": "2026-06-10T10:00:00Z"
}
```

> `key` 字段即为用户使用的虚拟 Key，**仅在创建时可见，请妥善保存**。

### 5.2 查看所有虚拟 Key

```bash
curl -s http://localhost:8000/api/keys \
  -H "X-Admin-Token: test-admin-token-secret" | python3 -m json.tool
```

### 5.3 撤销虚拟 Key

```bash
curl -s -X DELETE http://localhost:8000/api/keys/{key_id} \
  -H "X-Admin-Token: test-admin-token-secret"
```

---

## 6. 在 Open WebUI 中使用

### 6.1 首次注册

1. 访问 http://localhost:9000
2. 点击「Sign Up」注册账号（邮箱 + 密码）
3. 管理员在后台审批后即可登录

### 6.2 使用虚拟 Key 调用（API 方式）

Open WebUI 本身已直接连接 LiteLLM 网关，团队成员登录后**无需额外配置 Key**，直接在对话框选择模型即可。

若需要通过 OpenAI SDK/API 访问，配置如下：

```
API Base URL: http://localhost:9000/api
API Key:      使用 Open WebUI 账号登录后，在「设置 → 账户 → API Key」生成
```

---

## 7. 在 Codex CLI 中使用

[Codex CLI](https://github.com/openai/codex) 支持自定义 OpenAI 兼容端点。

### 7.1 环境变量方式（临时）

```bash
export OPENAI_API_KEY="sk-virtual-a1b2c3d4e5f6g7h8"
export OPENAI_BASE_URL="http://localhost:4000/v1"

codex "帮我写一个 Python 快速排序函数"
```

### 7.2 写入 shell 配置文件（持久）

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
# Team AI Platform
export OPENAI_API_KEY="sk-virtual-a1b2c3d4e5f6g7h8"
export OPENAI_BASE_URL="http://localhost:4000/v1"
```

然后 `source ~/.zshrc` 生效。

### 7.3 指定模型

```bash
codex --model "deepseek-deepseek-chat" "解释这段代码"
```

> 模型别名格式为 `{provider_key}-{model_id}`，如 `deepseek-deepseek-chat`。  
> 通过 `curl http://localhost:4000/v1/models -H "Authorization: Bearer sk-virtual-xxxx"` 查看可用模型列表。

---

## 8. 在 OpenCode 中使用

[OpenCode](https://github.com/opencode-ai/opencode) 使用配置文件 `~/.config/opencode/config.json`（或项目目录下 `opencode.json`）。

### 8.1 配置文件

```json
{
  "providers": {
    "team-ai": {
      "apiKey": "sk-virtual-a1b2c3d4e5f6g7h8",
      "baseURL": "http://localhost:4000/v1",
      "models": [
        {
          "id": "deepseek-deepseek-chat",
          "name": "DeepSeek Chat (via Team AI)"
        },
        {
          "id": "deepseek-deepseek-reasoner",
          "name": "DeepSeek R1 (via Team AI)"
        }
      ]
    }
  },
  "defaultProvider": "team-ai",
  "defaultModel": "deepseek-deepseek-chat"
}
```

### 8.2 命令行启动

```bash
opencode
```

OpenCode 会自动读取配置文件并使用团队 AI 网关。

---

## 9. 在 Claude Code 中使用

[Claude Code](https://docs.anthropic.com/claude-code) 默认连接 Anthropic 官方 API，通过以下方式接入 Team AI 网关。

### 9.1 环境变量方式

```bash
export ANTHROPIC_API_KEY="sk-virtual-a1b2c3d4e5f6g7h8"
export ANTHROPIC_BASE_URL="http://localhost:4000"

claude
```

> Team AI 网关的 LiteLLM 对 Anthropic SDK 提供了兼容层，`/v1/messages` 端点已自动适配。

### 9.2 写入 shell 配置文件

```bash
# ~/.zshrc
export ANTHROPIC_API_KEY="sk-virtual-a1b2c3d4e5f6g7h8"
export ANTHROPIC_BASE_URL="http://localhost:4000"
```

### 9.3 指定路由到本地部署的 Claude 模型

若通过 Team AI 网关路由 Anthropic 模型（需提前在管理台添加 Anthropic 厂商 Key）：

```bash
claude --model claude-3-7-sonnet-20250219 "你好"
```

若路由到其他厂商模型（如 DeepSeek），需要在 Claude Code 的 `--model` 参数中使用 LiteLLM 注册的别名：

```bash
# 注意：Claude Code 仅支持 Claude 协议模型，路由非 Claude 模型需在 LiteLLM 配置兼容层
claude --model anthropic-claude-3-7-sonnet-20250219 "帮我分析代码"
```

---

## 10. 常见问题

### Q1：添加供应商后 Open WebUI 仍然找不到新模型？

需要重启 LiteLLM 网关：

```bash
docker compose restart litellm
```

等待约 10 秒后，刷新 Open WebUI 模型列表。

---

### Q2：如何确认虚拟 Key 是否有效？

```bash
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-virtual-a1b2c3d4e5f6g7h8" | python3 -m json.tool
```

返回模型列表则 Key 有效。

---

### Q3：如何查看当前已注册的所有供应商和模型？

```bash
# 查看供应商
curl -s http://localhost:8000/api/providers \
  -H "X-Admin-Token: test-admin-token-secret" | python3 -m json.tool

# 查看 LiteLLM 路由中的模型
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-team-master-change-me" | python3 -m json.tool
```

---

### Q4：忘记 Admin Token 怎么办？

查看项目 `.env` 文件：

```bash
grep TEAM_AI_ADMIN_TOKEN .env
```

若未设置则使用默认值 `test-admin-token-secret`。

---

### Q5：虚拟 Key 和 LiteLLM Master Key 的区别？

| | 虚拟 Key (`sk-virtual-*`) | LiteLLM Master Key (`sk-team-*`) |
|---|---|---|
| 用途 | 分发给团队成员 | 管理员运维使用 |
| 权限 | 调用模型（受策略限制） | 完整 LiteLLM 管理权限 |
| 可撤销 | ✅ 可通过管理台撤销 | ❌ 需修改 .env 重启 |
| 存储位置 | PostgreSQL `backend_keys` 表 | `.env` 文件 |

---

*如需查看完整 API 文档，访问 http://localhost:8000/docs*
