# KB Platform v0.47 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v047
**版本**: V1.0（初始版）
**日期**: 2026-03-31
**基线 commit**: 643bd9e
**基线分支**: test-v-0-44-a（已合入 main）
**依据**: PRD Gap 分析 + 交叉审计留存项 + WISHLIST
**作者**: Claude Code（自动生成）

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.46.7 + PRD Gap 修复后的代码增量增强。禁止重构无关模块。

### 1.2 继承已有能力

- **PII 检测**（quality_check.py）— 8 类正则扫描，detect_pii 配置开关
- **update_type 追踪**（KnowledgeDoc.update_type）— 已加字段 + 前端标签
- **LLM token 日志**（llm_client.py）— prompt/completion/total tokens 已输出
- **Pipeline 配置化**（v0.46.1-4）— 7 stage enable/disable + params
- **SSRF 防护**（url_fetcher.py + url_validator.py）— DNS rebinding 防御已就绪
- **API Key 限流**（agent.py:_check_rate_limit）— Redis 固定窗口已实现

### 1.3 最小改动原则

每个任务只改必须改的文件。

---

## 第二章 当前阶段事实

### 2.1 版本主题

**v0.47：安全加固 + 质量收尾 — 审计留存项修复 + 基础设施加固**

> 本版本聚焦"修内功"：修复交叉审计留存 bug、加强安全运维基础、完善测试覆盖。不引入新功能，为后续大版本打牢地基。

### 2.2 来源追溯

| 来源 | 任务 |
|------|------|
| 交叉审计留存 C-3 | 矛盾检测排除 draft 文档 |
| 交叉审计留存 H-1 | suggest_tags entity_types 来源修正 |
| 交叉审计留存 H-4 | pipeline params schema 校验 |
| WISHLIST W-02 | 数据库连接池优化 |
| WISHLIST W-08 | 审计日志保留策略 |
| WISHLIST W-09 | 模型 API Key 加密文档化 |
| WISHLIST W-12 | Pipeline 执行可观测性（per-stage 日志） |
| WISHLIST W-16 | 缺失的集成测试 |

---

## 第三章 本轮目标与边界

### 3.1 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.47.1 | 矛盾检测排除 draft 文档 | P0 | 待开发 | 审计 C-3 |
| v0.47.2 | suggest_tags entity_types 从 pipeline config 读取 | P0 | 待开发 | 审计 H-1 |
| v0.47.3 | Pipeline params JSON Schema 校验 | P1 | 待开发 | 审计 H-4 |
| v0.47.4 | 数据库连接池显式配置 | P1 | 待开发 | W-02 |
| v0.47.5 | 审计日志保留策略 + 归档 | P1 | 待开发 | W-08 |
| v0.47.6 | Pipeline per-stage 执行日志表 | P1 | 待开发 | W-12 |
| v0.47.7 | 模型 API Key 加密方案文档化 + 轮换 API | P2 | 待开发 | W-09 |
| v0.47.8 | 集成测试补全（ZIP/节点CRUD/跨租户拒绝） | P2 | 待开发 | W-16 |

### 3.2 北极星三问校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ | 结论 |
|-----|----------------|-------------|-------------|------|
| v0.47.1 | ✅ 图谱质量（排除无效数据） | - | - | ✅ |
| v0.47.2 | ✅ 整合端（配置正确性） | - | - | ✅ |
| v0.47.3 | - | - | ✅ 防止配置错误 | ✅ |
| v0.47.4 | - | - | ✅ 生产稳定性 | ✅ |
| v0.47.5 | - | - | ✅ 运维合规 | ✅ |
| v0.47.6 | - | - | ✅ 成本追踪基础 | ✅ |
| v0.47.7 | - | - | ✅ 安全合规 | ✅ |
| v0.47.8 | - | - | ✅ 质量保障 | ✅ |

### 3.3 明确不做的事项

- 新增解析器（视频/网页）— 留给 v0.48
- 审批工作流引擎 — 留给 v0.50
- Prometheus/OpenTelemetry 全链路 — v0.47 仅做 per-stage DB 日志，全链路留给 v0.49
- 前端新页面 — v0.47 无新页面

---

## 第四章 优先级与执行顺序

```
Bug 修复链：
v0.47.1 → v0.47.2 → v0.47.3
← 顺序：先修数据质量 bug，再修配置 bug

基础设施链：
v0.47.4 → v0.47.6 → v0.47.5
← 先连接池（被所有服务依赖），再 stage 日志（为成本追踪铺路），最后审计归档

安全 & 测试：
v0.47.7 → v0.47.8
← 可并行
```

建议执行顺序：

```
v0.47.1 → v0.47.2 → v0.47.3 → v0.47.4
→ v0.47.6 → v0.47.5 → v0.47.7 → v0.47.8
```

---

## 第五章 各任务详细定义

---

### v0.47.1: 矛盾检测排除 draft 文档

**优先级：** P0
**前置依赖：** 无

**背景：** 当前 `ai_detect_contradictions` 会对所有文档（含 draft）做矛盾检测，导致未完成文档产生误报。

**变更：**
- `services/api/app/routers/ai_actions.py` — 查询文档时加 `KnowledgeDoc.status != 'draft'` 过滤
- 约 3 行改动

**验收标准：**
- draft 状态文档不参与矛盾检测
- published / reviewing 文档正常检测

---

### v0.47.2: suggest_tags entity_types 从 pipeline config 读取

**优先级：** P0
**前置依赖：** 无

**背景：** `ai-suggest-tags` 端点的 entity_types 参数当前硬编码，应从 `pipeline_stage_config` 读取 classify stage 的 `entity_types` 配置。

**变更：**
- `services/api/app/routers/ai_actions.py` — ai_suggest_tags 函数查询 PipelineStageConfig，读取 classify 的 entity_types
- 约 10 行改动

**验收标准：**
- 用户在 pipeline config 设置的 entity_types 会被 suggest_tags 使用
- 未配置时使用默认值

---

### v0.47.3: Pipeline params JSON Schema 校验

**优先级：** P1
**前置依赖：** 无

**背景：** PUT pipeline config 端点不校验 params 内容，用户可传入任意 JSON。

**变更：**
- `services/api/app/routers/pipeline_config.py` — 定义每个 stage 的 params schema，PUT 时校验
- 新增 `STAGE_PARAM_SCHEMAS` 字典（每个 stage name → 合法 key 及类型）
- 约 40 行改动

**验收标准：**
- 传入非法 key 或类型错误时返回 422
- 传入合法配置正常保存

---

### v0.47.4: 数据库连接池显式配置

**优先级：** P1
**前置依赖：** 无

**背景：** SQLAlchemy 使用默认连接池配置（pool_size=5），高并发下可能耗尽。

**变更：**
- `packages/shared-config/shared_config/settings.py` — 新增 db_pool_size、db_pool_recycle、db_max_overflow 配置项
- `packages/shared-models/shared_models/database.py` — create_async_engine / create_engine 传入池参数
- 约 15 行改动

**验收标准：**
- 可通过环境变量配置连接池参数
- 默认值：pool_size=10, pool_recycle=3600, max_overflow=20

---

### v0.47.5: 审计日志保留策略

**优先级：** P1
**前置依赖：** v0.47.4

**背景：** audit_log 表无 TTL 清理，会无限增长。

**变更：**
- `packages/shared-config/shared_config/settings.py` — 新增 audit_retention_days（默认 90 天）
- `services/api/app/services/audit_service.py` — 新增 `cleanup_old_logs()` 方法
- `services/api/app/routers/health.py` 或 Celery periodic task — 每日执行清理
- 约 30 行改动

**验收标准：**
- 超过 retention_days 的日志被自动删除
- 可通过环境变量调整保留天数

---

### v0.47.6: Pipeline per-stage 执行日志表

**优先级：** P1
**前置依赖：** v0.47.4

**背景：** Job 仅记录整体 status，无法追踪每个 stage 的耗时和 token 消耗。

**变更：**
- `packages/shared-models/shared_models/pipeline_stage_log.py` — 新模型：
  ```
  PipelineStageLog: id, job_id, stage_name, status, started_at, finished_at,
                    token_usage(JSONB), error_message
  ```
- `infra/sql/alembic/versions/` — 新增 migration
- `services/pipeline-worker/worker/tasks.py` — 每个 stage 前后写入 log 记录
- 约 50 行改动

**验收标准：**
- 每次 pipeline 执行产生 7 条 stage log
- 可查询某个 job 各 stage 的耗时和 token 消耗

---

### v0.47.7: 模型 API Key 加密方案文档化 + 轮换 API

**优先级：** P2
**前置依赖：** 无

**变更：**
- `docs/security/model-key-encryption.md` — 文档化加密方案
- `services/api/app/routers/model_providers.py` — 新增 `POST /v1/model-providers/{id}/rotate-key`
- 约 25 行代码 + 文档

---

### v0.47.8: 集成测试补全

**优先级：** P2
**前置依赖：** v0.47.1-3

**变更：**
- `services/api/tests/test_batch_import_zip.py` — ZIP 导入端到端测试
- `services/api/tests/test_architecture_nodes_crud.py` — 架构节点 CRUD 完整测试
- `services/api/tests/test_cross_tenant_rejection.py` — 显式跨租户拒绝测试
- 约 150 行测试代码

---

## 第六章 风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 连接池参数调优需要生产数据 | v0.47.4 默认值可能不适合所有场景 | 设为可配置，文档化推荐值 |
| Celery periodic task 需要 celery beat | v0.47.5 自动清理依赖调度器 | 备选方案：API 端点手动触发 |
| stage log 写入增加 DB 负载 | v0.47.6 每次 pipeline 多 7 次写入 | 使用 bulk insert，非关键路径异步写入 |

---

## 第七章 预计产出

- 修复 3 个审计留存 bug
- 新增 1 张 DB 表（pipeline_stage_log）
- 新增 1 个 API 端点（rotate-key）
- 3 个集成测试文件
- 1 份安全文档
- 0 个新前端页面
