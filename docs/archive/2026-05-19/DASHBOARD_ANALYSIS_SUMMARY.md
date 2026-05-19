# Team AI Platform 仪表板与治理数据分析总结

## 📍 一、仪表板代码位置与结构

### 前端位置
| 页面 | 路径 | 功能 |
|-----|------|------|
| **主仪表板** | `frontend/src/pages/dashboard/index.tsx` | 业务统计 + 服务健康 |
| **治理中心** | `frontend/src/pages/governance/index.tsx` | 策略管理 + 审批工作流 |
| **虚拟密钥** | `frontend/src/pages/keys/index.tsx` | 密钥发放与管理 |
| **模型管理** | `frontend/src/pages/models/index.tsx` | 模型注册与配置 |
| **服务商** | `frontend/src/pages/providers/index.tsx` | AI 提供商配置 |
| **观测中心** | `frontend/src/pages/observe/index.tsx` | 日志 + 会话 + 审计 |

### 后端位置
```
/backend/app/
├── routers/
│   ├── platform.py          ← 平台概览 API
│   ├── keys.py              ← 虚拟密钥管理（已含使用统计）
│   ├── models.py            ← 模型注册管理
│   ├── providers.py         ← AI 服务商管理
│   ├── policies.py          ← 治理策略
│   └── approvals.py         ← 审批工作流
├── schemas.py               ← 所有数据模型定义
└── store.py                 ← 核心数据存储（key_usage_stats 等）
```

---

## 📊 二、当前仪表板显示的内容

### 主仪表板 (Dashboard)
**统计卡片**:
- 我的团队（team 数量）
- 项目总数
- 任务总数
- 知识库文档数

**服务健康监控**:
- 有效密钥数 / 总密钥数
- AI 会话数
- 技能库数
- LiteLLM 网关已注册模型数

**服务探针** (4 个核心服务):
- Backend (8000)
- LiteLLM Gateway (4000)
- Open WebUI (8080)
- Qdrant 向量库 (6333)

**快速入口**: 导航到各模块

---

## 🔌 三、API 端点清单

### 虚拟密钥 API (`/api/keys/*`)
```bash
# 已实现 ✅
GET  /api/keys                      # 列表密钥
POST /api/keys/issue                # 发放密钥
DELETE /api/keys/{key_id}           # 撤销密钥
GET  /api/keys/{key_id}/audit-log   # 审计日志 ⭐ 已有
GET  /api/keys/{key_id}/usage       # 使用统计 ⭐ 已有

# 查询参数：limit, offset, user_id, project_id, status, q
```

### 模型 API (`/api/models/*`)
```bash
GET  /api/models                      # 列表（支持过滤）
POST /api/models                      # 注册单个
POST /api/models/batch-register       # 批量注册
GET  /api/models/aliases              # 列表别名
```

### 服务商 API (`/api/providers/*`)
```bash
GET  /api/providers                   # 列表服务商
POST /api/providers                   # 创建服务商
POST /api/providers/{id}/discover-models  # 探测模型
POST /api/providers/sync-gateway      # 同步到网关
```

### 治理 API
```bash
GET  /api/policies                    # 列表策略
POST /api/policies                    # 创建/更新策略
GET  /api/approvals                   # 列表审批
POST /api/approvals/submit            # 提交审批
```

### 平台概览 API (`/api/platform/*`)
```bash
GET  /api/platform/overview           # 整体统计 ⭐ 管理员权限
```

---

## 📈 四、已有的可用数据字段

### 1️⃣ 虚拟密钥使用统计 (KeyUsageStats)
**端点**: `GET /api/keys/{key_id}/usage`

```json
{
  "key_id": "string",
  "total_calls": 1500,                  // ✅ 总调用次数
  "total_tokens_used": 250000,          // ✅ 消耗令牌总数
  "calls_by_model": {                   // ✅ 按模型分类
    "gpt-4": 150,
    "gpt-3.5-turbo": 1350
  },
  "tokens_by_model": {                  // ✅ 按模型令牌分类
    "gpt-4": 100000,
    "gpt-3.5-turbo": 150000
  },
  "first_used_at": "2025-05-10T10:00:00Z",  // ✅ 首次使用
  "last_used_at": "2025-05-17T14:30:00Z",   // ✅ 最后使用
  "usage_by_hour": {                    // ✅ 按小时统计（部分支持）
    "2025-05-17 14:00": 45
  }
}
```

### 2️⃣ 虚拟密钥审计日志 (KeyAuditLog)
**端点**: `GET /api/keys/{key_id}/audit-log`

```json
{
  "entries": [
    {
      "timestamp": "2025-05-17T14:30:00Z",
      "action": "used",                   // ✅ issued|used|revoked|expired
      "user_id": "admin",
      "model_id": "gpt-4",
      "tokens_used": 500,
      "details": {}
    }
  ]
}
```

### 3️⃣ 虚拟密钥记录 (KeyRecord)
**端点**: `GET /api/keys`

```json
{
  "id": "key_abc123",
  "label": "Production API",
  "user_id": "admin",
  "project_id": "proj_xyz",
  "scope": "project:*",
  "quota": 100000,                      // ✅ 调用配额
  "expire_at": "2025-06-16T00:00:00Z",  // ✅ 过期时间
  "status": "active",                   // ✅ active|revoked
  "created_at": "2025-05-10T00:00:00Z"
}
```

### 4️⃣ 模型记录 (ModelRecord)
**端点**: `GET /api/models`

```json
{
  "id": "gpt-4",
  "provider": "openai",
  "name": "GPT-4",
  "context_window": 128000,             // ✅ 上下文窗口
  "cost_tier": "high",                  // ✅ 成本层级
  "availability": "active",
  "labels": {
    "tier": "pro",
    "real_model_id": "gpt-4-turbo"
  }
}
```

### 5️⃣ 平台概览 (PlatformOverview)
**端点**: `GET /api/platform/overview`

```json
{
  "providers_total": 5,                 // ✅ 总服务商数
  "providers_enabled": 4,               // ✅ 启用的服务商
  "keys_total": 42,                     // ✅ 总密钥数
  "keys_active": 38,                    // ✅ 活跃密钥
  "keys_revoked": 4,                    // ✅ 已撤销密钥
  "skills_total": 28,                   // ✅ 技能数
  "sessions_total": 156,                // ✅ 会话总数
  "policies_total": 12,                 // ✅ 策略总数
  "approvals_total": 48,                // ✅ 审批总数
  "approvals_pending": 5,               // ✅ 待处理审批
  "gateway_models_total": 250,          // ✅ 网关模型数
  "service_status": [                   // ✅ 服务健康
    {
      "name": "backend",
      "reachable": true,
      "detail": "HTTP 200"
    }
  ]
}
```

---

## 🎯 五、缺失的治理统计指标

### ⭐⭐⭐ 高优先级

#### 1. **成本统计** (最缺失！)
```
GET /api/keys/{key_id}/cost-stats
└─ total_cost_usd
└─ cost_by_model {gpt-4: $12.50}
└─ cost_by_date  {2025-05-17: $1.45}
```

#### 2. **按提供商成本分解**
```
GET /api/providers/{provider_id}/cost-stats
├─ total_cost_usd
├─ input_cost / output_cost
└─ model_costs breakdown
```

#### 3. **实时成本仪表板**
```
增强 GET /api/platform/overview
├─ total_cost_usd_month
├─ total_cost_usd_today
├─ cost_trend_7d [45.2, 44.1, ...]
├─ cost_by_provider {OpenAI: $800}
└─ cost_by_key {top 5}
```

### ⭐⭐ 中优先级

#### 4. **时间序列使用数据**
```
GET /api/keys/{key_id}/usage-timeline
├─ period: "2025-05-17 14:00"
├─ calls: 45
├─ tokens: 12500
├─ latency_ms: 850
└─ error_rate: 0.02
```

#### 5. **模型使用排行**
```
GET /api/models/usage-ranking
└─ rankings: [
    {rank: 1, model: "gpt-4", calls: 15000, cost: $500, users: 42}
  ]
```

#### 6. **配额消耗状态**
```
GET /api/keys/{key_id}/quota-status
├─ quota_limit: 100000
├─ quota_used: 65000
├─ quota_remaining: 35000
├─ daily_quota / daily_used
└─ projected_depletion_at
```

#### 7. **月度报告**
```
GET /api/reports/monthly/2025/05
├─ total_api_calls
├─ total_cost
├─ top_consumers
├─ models_by_usage
└─ daily_breakdown
```

### ⭐ 低优先级

#### 8. **合规性统计**
```
GET /api/governance/compliance-stats
├─ policies.violations
├─ approvals.avg_time
└─ policies.by_type
```

#### 9. **超额告警检测**
```
GET /api/platform/quota-alerts
├─ critical []     # 今天会超配额
└─ warning []      # 使用超过 80%
```

---

## 💡 六、建议的前端改进

### 仪表板页面增强
**新增统计卡片** (在现有 4 个基础上):
- 📊 **今日 API 调用次数** (realtime)
- 💰 **本月消费成本** (USD)
- ⏱️ **平均响应延迟** (ms)
- ❌ **错误率** (%)

**新增图表**:
- 📈 7 天成本趋势线
- 🥧 模型使用饼图
- 📊 密钥配额进度条

### 新建页面（推荐）
```
/pages/costs/          ← 成本中心（成本统计、按模型/提供商分类）
/pages/alerts/         ← 监控告警（配额告警、成本告警、错误告警）
/pages/reports/        ← 报告（月度报告、导出功能）
```

---

## 🔧 七、后端实现建议

### 核心数据模型（新建）
```python
# 成本统计
class CostStats(BaseModel):
    key_id: str
    total_cost_usd: float
    cost_by_model: dict[str, float]
    cost_by_date: dict[str, float]
    input_tokens_cost: float
    output_tokens_cost: float

# 配额状态
class QuotaStatus(BaseModel):
    key_id: str
    quota_limit: int
    quota_used: int
    quota_remaining: int
    projected_depletion_at: datetime | None
```

### 新增后端方法（store.py）
```python
# 成本计算
def calculate_cost(tokens_in, tokens_out, model_id)
def get_key_cost_stats(key_id, period="month")
def get_provider_cost_stats(provider_id)

# 配额追踪
def get_quota_status(key_id)
def check_quota_exceeded(key_id)
def get_quota_alerts()

# 报告
def generate_monthly_report(year, month)
def get_usage_timeline(key_id, start_date, end_date, granularity)
```

### 新增路由文件
```
/backend/app/routers/costs.py          ← 成本相关 API
/backend/app/routers/reports.py        ← 报告生成 API
/backend/app/routers/alerts.py         ← 告警和监控 API
```

---

## ⏰ 八、实现优先级与估时

| 功能 | 复杂度 | 优先级 | 后端/前端 | 估时 |
|-----|-------|--------|----------|------|
| 成本计算与统计 | 中 | ⭐⭐⭐ | 后端 | 4h |
| 仪表板成本卡片 | 低 | ⭐⭐⭐ | 前端 | 1h |
| 成本中心页面 | 中 | ⭐⭐⭐ | 前端 | 4h |
| 时间序列使用数据 | 中 | ⭐⭐ | 后端 | 3h |
| 配额追踪与告警 | 中 | ⭐⭐ | 后端+前端 | 4h |
| 月度报告 | 中 | ⭐⭐ | 后端 | 3h |
| 模型使用排行 | 低 | ⭐ | 后端 | 2h |
| 数据导出功能 | 低 | ⭐ | 后端+前端 | 2h |

---

## 📝 九、关键发现

### ✅ 已有能力
1. ✅ 密钥使用统计框架完整（calls + tokens）
2. ✅ 审计日志记录系统完善
3. ✅ 模型标签系统支持自定义数据
4. ✅ 提供商元数据字段灵活

### ❌ 主要缺失
1. ❌ **成本计算完全缺失** ← 最关键！
2. ❌ 没有时间序列使用数据
3. ❌ 缺少配额消耗追踪
4. ❌ 没有实时监控指标
5. ❌ 缺乏合规性报告

### 🎯 建议次序
1. **第 1 阶段**: 实现成本统计核心（后端 + 仪表板卡片）
2. **第 2 阶段**: 建立成本中心页面 + 配额告警
3. **第 3 阶段**: 添加时间序列分析 + 月度报告

---

## 📚 参考资源

**详细分析文档**: `/memories/session/team_ai_platform_dashboard_analysis.md`

**源代码入口**:
- 前端 API: `frontend/src/lib/api.ts`
- 后端 schemas: `backend/app/schemas.py`
- 存储层: `backend/app/store.py`
