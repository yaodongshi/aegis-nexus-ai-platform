# Aegis Nexus AI Platform Database Migration Guide

> 目标：把平台控制面数据库从初始化到演进的流程固定下来，避免手工改库和版本漂移。

## 1. 初始化顺序

1. 创建 PostgreSQL 数据库和基础账号
2. 执行核心表建表脚本
3. 创建唯一约束与索引
4. 初始化默认策略和管理员角色
5. 导入最小模型目录与试点虚拟 Key

## 2. 核心表

- `model_registry`
- `access_key`
- `skill_package`
- `session`
- `policy`
- `approval`

## 3. 迁移原则

- 所有表结构变更必须使用迁移脚本，不允许手工改库
- 每次迁移必须配套回滚脚本或回滚说明
- 对枚举状态字段的变更必须保持向后兼容
- 数据修复类迁移必须先在测试库验证，再进入预发

## 4. 索引与约束建议

### 4.1 唯一约束

- `model_registry(provider, name)`
- `skill_package(name, version)`
- `access_key(key_hash)`
- `policy(name, type)`

### 4.2 常用索引

- `access_key(user_id, project_id, status)`
- `session(user_id, project_id, created_at desc)`
- `approval(status, created_at desc)`
- `model_registry(availability, cost_tier)`
- `skill_package(status, owner_id)`

## 5. 表结构演进建议

### 5.1 model_registry

- 追加字段时优先使用可空字段或默认值
- 不要直接改语义字段名称，必要时先新增后迁移

### 5.2 access_key

- key 明文只在发放时返回一次
- 数据库存储 hash，不保存原文
- 回收状态必须可审计

### 5.3 skill_package

- 版本号必须参与唯一约束
- 发布/回滚应保留完整历史记录
- 签名字段必须可追溯到发布人和时间

### 5.4 session

- 会话摘要与向量索引分离存储
- 仅保留必要元数据在 PostgreSQL
- 长文本内容优先放对象存储或向量库引用

### 5.5 policy

- 策略变更优先采用新增版本覆盖旧版本的方式
- 灰度期间允许并行策略存在

### 5.6 approval

- 高风险操作必须有审批轨迹
- 审批状态至少包含 pending / approved / rejected / canceled

## 6. 备份与恢复

- 每次发版前备份关键表
- 保留最近一次可回滚版本
- 数据库恢复后先验证 Key、模型目录和审批链路
- 恢复演练需定期执行

## 7. 启动前检查

- PostgreSQL 可连接且版本满足要求
- Qdrant 可连接且 collection 可创建
- LiteLLM 配置可被读取
- `.env` 中的敏感变量已正确设置
- 试点 Key 和管理员账号已准备完毕

## 8. 推荐迁移文件结构

```text
migrations/
├── 0001_init.sql
├── 0002_indexes.sql
├── 0003_seed_admin_and_policy.sql
├── 0004_seed_model_registry.sql
├── 0005_seed_trial_keys.sql
└── rollback/
    ├── 0002_indexes.rollback.sql
    ├── 0003_seed_admin_and_policy.rollback.sql
    └── ...
```

## 9. 运维建议

- 每次发版前备份 PostgreSQL 关键表
- 记录模型目录、策略和技能包版本快照
- 对 Key 回收、技能回滚、审批驳回保留审计日志
- 所有迁移动作写入变更记录
