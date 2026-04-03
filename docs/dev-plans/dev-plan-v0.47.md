# KB Platform v0.47 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v047
**版本**: V2.0（规范重写版）
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

- **PII 检测**（`services/pipeline-worker/worker/stages/quality_check.py`）— 8 类正则扫描，`detect_pii` 配置开关
- **update_type 追踪**（`packages/shared-models/shared_models/knowledge.py: KnowledgeDoc.update_type`）— 已加字段 + 前端标签
- **LLM token 日志**（`services/ai-orchestrator/orchestrator/llm_client.py`）— prompt/completion/total tokens 已输出
- **Pipeline 配置化**（v0.46.1-4）— 7 stage enable/disable + params，`PipelineStageConfig` 模型
- **SSRF 防护**（`services/api/app/utils/url_fetcher.py` + `url_validator.py`）— DNS rebinding 防御已就绪
- **API Key 限流**（`services/api/app/routers/agent.py:_check_rate_limit`）— Redis 固定窗口已实现
- **Pipeline stages**（`services/pipeline-worker/worker/stages/`）— classify / architecture_draft / doc_generate / quality_check / conflict_detect / embed / review_notify
- **CrossReference**（`packages/shared-models/shared_models/cross_reference.py`）— 5 种关系类型 + CRUD API
- **矛盾检测 + 模式发现**（v0.46.5-6）— AI detect contradictions / discover patterns API

### 1.3 最小改动原则

每个任务只改必须改的文件。如果发现无关问题，记录到衍生建议但不执行。

### 1.4 任务领取规则

每次只能领取一个任务。完成后按第九章格式汇报，确认后再领下一个。

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
Bug 修复链：v0.47.1 → v0.47.2 → v0.47.3
← 顺序：先修数据质量 bug，再修配置 bug

基础设施链：v0.47.4 → v0.47.6 → v0.47.5
← 先连接池（被所有服务依赖），再 stage 日志（为成本追踪铺路），最后审计归档

安全 & 测试：v0.47.7 → v0.47.8
← 可并行
```

建议执行顺序：`v0.47.1 → v0.47.2 → v0.47.3 → v0.47.4 → v0.47.6 → v0.47.5 → v0.47.7 → v0.47.8`

---

## 第五章 各任务详细定义

---

### v0.47.1: 矛盾检测排除 draft 文档

**任务版本号：** v0.47.1
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**现状：** `ai_detect_contradictions` 对所有文档（含 draft）做矛盾检测，导致未完成文档产生误报。

**目标（Goal）：** 修改矛盾检测查询，排除 `status='draft'` 的文档，仅对非 draft 文档（pending / approved / rejected / archived）执行矛盾检测。
> ⚠️ 注意：KnowledgeDoc.status 合法值为 `draft / pending / approved / rejected / archived`，不存在 `published` 或 `reviewing` 状态。

---

#### 后端变更

**修改文件：**
- `services/api/app/routers/ai_actions.py` — `ai_detect_contradictions` 函数：
  - 查询文档时加 `.filter(KnowledgeDoc.status != 'draft')` 过滤条件

**业务规则：**
① 读取项目文档列表时，添加 `status != 'draft'` 过滤
② 非 draft 状态的文档（pending / approved / rejected / archived）正常参与矛盾检测
③ 如果过滤后文档数 < 2，返回空结果（沿用已有逻辑）

---

#### 验收标准

- [ ] 项目中有 3 篇 approved + 2 篇 draft 文档 → 矛盾检测只比对 3 篇 approved，draft 不参与
- [ ] 项目仅有 draft 文档 → 返回空结果，不报错
- [ ] pending 状态文档正常参与检测
- [ ] 已有 approved 文档行为不变（不回归）

---

#### 工作范围

**包含：** ai_actions.py 中查询过滤条件修改（~3 行）
**不包含：** 矛盾检测逻辑本身的调整（v0.49）

---

#### 预估工作量

- Phase 1 读 ai_detect_contradictions 函数：0.5 小时
- Phase 2 执行：0.5 小时
- Phase 3 测试：0.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 过滤逻辑影响其他 AI action 端点 | 低 | 低 | 仅修改 detect_contradictions 函数，不影响其他 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/routers/ai_actions.py` 中 `ai_detect_contradictions` 函数完整逻辑
> 2. 确认文档查询位置和已有过滤条件

---

### v0.47.2: suggest_tags entity_types 从 pipeline config 读取

**任务版本号：** v0.47.2
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**现状：** `ai-suggest-tags` 端点的 `entity_types` 参数当前硬编码，应从 `PipelineStageConfig` 读取 classify stage 的 `entity_types` 配置。

**目标（Goal）：** 修改 `ai_suggest_tags` 函数，从项目 pipeline config 读取 classify stage 的 `entity_types`，确保用户配置的实体类型在标签建议中生效。

---

#### 后端变更

**修改文件：**
- `services/api/app/routers/ai_actions.py` — `ai_suggest_tags` 函数：
  - 查询 `PipelineStageConfig`，读取 `stage_name='classify'` 的 `params.entity_types`
  - 若存在，传入 prompt 构建函数
  - 若不存在，使用默认值（行为不变）

**业务规则：**
① 查询项目 `PipelineStageConfig` 中 `stage_name='classify'` 记录
② 从 `params` JSONB 中提取 `entity_types` 字段（`list[str] | None`）
③ 传入 AI prompt 构建函数，用于指导标签建议
④ 未配置时使用原有默认行为（不限定实体类型）
⑤ `entity_types` 为空列表 `[]` 等价于未配置

---

#### 验收标准

- [ ] 项目 pipeline config 设置 `entity_types: ["人名", "地名"]` → suggest_tags 返回的标签中包含对应类型
- [ ] 未配置 entity_types → suggest_tags 行为与 v0.46 完全一致
- [ ] PipelineStageConfig 表中无该项目记录 → 使用默认值，不报错

---

#### 工作范围

**包含：** ai_actions.py 中 suggest_tags 读取 pipeline config（~10 行）
**不包含：** prompt 模板本身的修改（v0.46.3 已完成）；前端 UI 变更

---

#### 预估工作量

- Phase 1 读 ai_suggest_tags 函数 + PipelineStageConfig 查询方式：0.5 小时
- Phase 2 执行：1 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| DB 查询增加端点延迟 | 低 | 低 | 单次查询，可忽略 |
| entity_types 格式不符预期 | 低 | 低 | 校验为 list[str]，否则 fallback 默认 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/routers/ai_actions.py` 中 `ai_suggest_tags` 完整逻辑
> 2. 读 `PipelineStageConfig` 模型确认查询方式
> 3. 确认 v0.46.3 中 entity_types 在 params 中的存储格式

---

### v0.47.3: Pipeline params JSON Schema 校验

**任务版本号：** v0.47.3
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**现状：** `PUT /v1/projects/{pid}/pipeline-config/{stage}` 端点不校验 `params` 内容，用户可传入任意 JSON。

**目标（Goal）：** 为每个 stage 定义合法 params schema，PUT 时校验传入参数的 key 和类型，非法输入返回 422。

---

#### 后端变更

**修改文件：**
- `services/api/app/routers/pipeline_config.py` — 新增 `STAGE_PARAM_SCHEMAS` 字典 + 校验逻辑：

**STAGE_PARAM_SCHEMAS 定义：**
```python
STAGE_PARAM_SCHEMAS = {
    "classify": {
        "confidence_threshold": {"type": float, "min": 0.0, "max": 1.0},
        "entity_types": {"type": list},
    },
    "architecture_draft": {},
    "doc_generate": {
        "max_length": {"type": int, "min": 100, "max": 50000},
        "entity_types": {"type": list},
    },
    "quality_check": {
        "min_content_length": {"type": int, "min": 1, "max": 10000},
        "require_title": {"type": bool},
        "detect_pii": {"type": bool},
    },
    "conflict_detect": {
        "similarity_threshold": {"type": float, "min": 0.0, "max": 1.0},
    },
    "embed": {
        "model": {"type": str},
    },
    "review_notify": {},
}
```

**业务规则：**
① PUT 请求到达时，根据 `stage_name` 查找对应 schema
② 遍历传入 `params` 的每个 key：若 key 不在 schema 中 → 422 "unknown parameter: {key}"
③ 若 key 存在但类型不匹配 → 422 "parameter {key}: expected {type}, got {actual}"
④ 若有 min/max 约束且值超出范围 → 422 "parameter {key}: value out of range [{min}, {max}]"
⑤ 校验通过 → 正常保存

---

#### 验收标准

- [ ] PUT classify stage，`params: {"confidence_threshold": 0.8}` → 200 成功
- [ ] PUT classify stage，`params: {"unknown_key": 123}` → 422 "unknown parameter"
- [ ] PUT quality_check，`params: {"min_content_length": "abc"}` → 422 类型错误
- [ ] PUT classify，`params: {"confidence_threshold": 1.5}` → 422 超出范围
- [ ] PUT 空 params `{}` → 200 成功
- [ ] 不影响 GET 和 POST reset 端点

---

#### 工作范围

**包含：** pipeline_config.py 中 schema 定义 + 校验逻辑（~40 行）
**不包含：** 前端表单校验（前端已有基本校验）；schema 热加载（写死在代码中）

---

#### 预估工作量

- Phase 1 读 pipeline_config.py PUT 端点逻辑：0.5 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Schema 定义与已有配置不一致导致旧数据更新失败 | 中 | 中 | 校验仅在 PUT 时触发，不影响已有数据读取 |
| 新增 stage 时忘记添加 schema | 低 | 低 | 未知 stage_name 已有 404 处理 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/routers/pipeline_config.py` 完整 PUT 端点逻辑
> 2. 读各 stage 实际使用的参数，确认 schema 定义与实际一致

---

### v0.47.4: 数据库连接池显式配置

**任务版本号：** v0.47.4
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**现状：** SQLAlchemy 使用默认连接池配置（pool_size=5），高并发下可能耗尽。

**目标（Goal）：** 在 shared-config 中新增连接池配置项，在 database.py 创建引擎时传入，支持通过环境变量调优。

---

#### 后端变更

**修改文件：**
- `packages/shared-config/shared_config/settings.py` — 新增配置项：
  - `db_pool_size: int = 10` — 连接池大小
  - `db_pool_recycle: int = 3600` — 连接回收时间（秒）
  - `db_max_overflow: int = 20` — 溢出连接数上限

- `packages/shared-models/shared_models/database.py` — 修改 `create_async_engine` / `create_engine` 调用：
  - 传入 `pool_size=settings.db_pool_size`
  - 传入 `pool_recycle=settings.db_pool_recycle`
  - 传入 `max_overflow=settings.db_max_overflow`

**业务规则：**
① 从 settings 读取 3 个连接池参数
② 创建 SQLAlchemy engine 时传入这 3 个参数
③ 未设置环境变量时使用默认值（pool_size=10, pool_recycle=3600, max_overflow=20）
④ 不修改已有 DB URL 配置逻辑

---

#### 验收标准

- [ ] 设置 `DB_POOL_SIZE=20` 环境变量 → engine 使用 pool_size=20
- [ ] 不设置环境变量 → 使用默认值（pool_size=10, pool_recycle=3600, max_overflow=20）
- [ ] API 服务启动正常，数据库操作不受影响
- [ ] pipeline-worker 服务使用同样的连接池配置

---

#### 工作范围

**包含：** settings.py 3 个新字段 + database.py engine 参数传入（~15 行）
**不包含：** 连接池监控指标（v0.49 Prometheus）；PgBouncer 等外部连接池

---

#### 预估工作量

- Phase 1 读 settings.py + database.py 当前配置方式：0.5 小时
- Phase 2 执行：1 小时
- Phase 3 测试：0.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 默认值不适合所有场景 | 低 | 低 | 设为可配置，文档化推荐值 |
| 修改 engine 参数影响现有连接 | 低 | 中 | 仅在启动时配置，不影响运行中连接 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `packages/shared-config/shared_config/settings.py` 当前配置项
> 2. 读 `packages/shared-models/shared_models/database.py` engine 创建方式
> 3. 确认所有服务（api / pipeline-worker / ai-orchestrator / ingestion-worker）共用同一 database.py

---

### v0.47.5: 审计日志保留策略 + 归档

**任务版本号：** v0.47.5
**优先级：** P1
**前置依赖：** v0.47.4（连接池就绪）

---

#### 背景与目标

**现状：** `audit_log` 表无 TTL 清理，数据会无限增长。

**目标（Goal）：** 新增审计日志保留天数配置，实现自动清理超期日志的功能。

---

#### 后端变更

**修改文件：**
- `packages/shared-config/shared_config/settings.py` — 新增：
  - `audit_retention_days: int = 90` — 审计日志保留天数

- `services/api/app/services/audit_service.py` — 新增 `cleanup_old_logs()` 方法：
  ```
  def cleanup_old_logs(db: Session) -> int:
      # 删除 created_at < now() - retention_days 的记录
      # 返回删除行数
  ```

- `services/api/app/routers/health.py`（或新增 Celery periodic task）— 每日触发清理

**业务规则：**
① 计算截止日期 = `now() - timedelta(days=settings.audit_retention_days)`
② 删除 `audit_log` 表中 `created_at < 截止日期` 的记录
③ 记录删除行数到日志（INFO 级别）
④ 通过 Celery beat 每日 03:00 执行清理；备选方案：API 端点 `POST /v1/admin/cleanup-audit-logs` 手动触发
⑤ retention_days 可通过环境变量 `AUDIT_RETENTION_DAYS` 配置

---

#### 验收标准

- [ ] 设置 `AUDIT_RETENTION_DAYS=7` → 清理执行后，7 天前的日志被删除
- [ ] 默认 90 天保留 → 90 天内的日志不受影响
- [ ] 清理后 audit_log 表中无超期记录
- [ ] 清理操作本身记录到应用日志（含删除行数）
- [ ] 手动触发端点可用（备选方案）

---

#### 工作范围

**包含：** settings 配置 + cleanup 方法 + 触发机制（~30 行）
**不包含：** 日志归档到冷存储（S3 等）；日志压缩导出

---

#### 预估工作量

- Phase 1 读 audit_log 模型 + audit_service.py 结构：0.5 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Celery periodic task 需要 celery beat | 中 | 低 | 备选方案：API 端点手动触发 |
| 大量删除导致 DB 负载 | 低 | 中 | 分批删除（每次最多 1000 行）|

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `audit_log` 模型确认 `created_at` 字段存在
> 2. 读 `services/api/app/services/audit_service.py` 确认服务结构
> 3. 确认 Celery beat 是否已配置

---

### v0.47.6: Pipeline per-stage 执行日志表

**任务版本号：** v0.47.6
**优先级：** P1
**前置依赖：** v0.47.4（连接池就绪）

---

#### 背景与目标

**现状：** Pipeline Job 仅记录整体 status，无法追踪每个 stage 的耗时和 token 消耗。

**目标（Goal）：** 新增 `pipeline_stage_log` 表，记录每次 pipeline 执行中每个 stage 的状态、耗时和 token 消耗。

---

#### 后端变更

**新增文件：**
- `packages/shared-models/shared_models/pipeline_stage_log.py` — 新模型：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, default uuid4 | 主键 |
| job_id | UUID | FK→job.id, NOT NULL | 所属 pipeline job |
| stage_name | VARCHAR(50) | NOT NULL | Stage 标识 |
| status | VARCHAR(20) | NOT NULL | "running" / "completed" / "skipped" / "failed" |
| started_at | TIMESTAMP | nullable | 开始时间 |
| finished_at | TIMESTAMP | nullable | 结束时间 |
| token_usage | JSONB | default {} | `{"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}` |
| error_message | TEXT | nullable | 失败时的错误信息 |

- `infra/sql/alembic/versions/` — migration：`create_pipeline_stage_log_table`

**修改文件：**
- `packages/shared-models/shared_models/__init__.py` — 导出 `PipelineStageLog`
- `services/pipeline-worker/worker/tasks.py` — 每个 stage 执行前后写入 log 记录：
  - stage 执行前：插入 `status='running'`, `started_at=now()`
  - stage 执行后：更新 `status='completed'`, `finished_at=now()`, `token_usage=...`
  - stage 跳过时：插入 `status='skipped'`
  - stage 失败时：更新 `status='failed'`, `error_message=...`

**业务规则：**
① 每个 stage 执行前创建一条 log 记录（status=running）
② stage 执行完成后更新记录（status=completed/failed + 耗时 + token）
③ stage 被 PipelineStageConfig 禁用时记录 status=skipped
④ token_usage 从 LLM client 返回值中获取（对于不调用 LLM 的 stage 如 embed，token_usage 为空 {}）
⑤ 使用 bulk insert 优化性能，非关键路径异步写入

---

#### 验收标准

- [ ] 执行一次 pipeline → 产生 7 条 stage log 记录
- [ ] 每条记录包含正确的 started_at / finished_at（可计算耗时）
- [ ] 调用 LLM 的 stage（classify / doc_generate / quality_check）记录 token_usage
- [ ] 禁用的 stage 记录 status=skipped
- [ ] 查询某个 job 的 stage log 可按时间排序

---

#### 工作范围

**包含：** 新模型 + migration + tasks.py 日志写入（~50 行）
**不包含：** stage log 查询 API（v0.49 或 v0.50 的 cost dashboard）；前端展示

---

#### 预估工作量

- Phase 1 读 tasks.py pipeline 执行流程 + 确认 token_usage 获取方式：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| stage log 写入增加 pipeline 执行耗时 | 低 | 低 | 非关键路径，单次 DB 写入可忽略 |
| ~~pipeline_job 表名已确认~~ | — | — | **已确认：实际表名为 `job`（`packages/shared-models/shared_models/job.py`），FK 已修正为 `job.id`** |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/pipeline-worker/worker/tasks.py` 完整 run_pipeline 逻辑
> 2. **✅ 已确认：pipeline job 实际表名为 `job`**（`packages/shared-models/shared_models/job.py` → `__tablename__ = "job"`），FK 已修正为 `job.id`。
> 3. 确认 LLM client 返回 token_usage 的方式

---

### v0.47.7: 模型 API Key 加密方案文档化 + 轮换 API

**任务版本号：** v0.47.7
**优先级：** P2
**前置依赖：** 无

---

#### 背景与目标

**现状：** 模型 API Key 的加密方案未文档化，且无法在线轮换 key。

**目标（Goal）：** 文档化现有 API Key 加密方案；新增 key 轮换 API 端点，允许管理员在不中断服务的情况下更换模型 provider 的 API Key。

---

#### 后端变更

**新增文件：**
- `docs/security/model-key-encryption.md` — 文档化加密方案（Fernet / AES / 环境变量，视现有实现而定）

**修改文件：**
- `services/api/app/routers/model_providers.py` — 新增端点：

```
POST /v1/model-providers/{provider_id}/rotate-key
认证：JWT，kb_admin（仅 KB 管理员）
Body：{"new_api_key": "sk-xxx..."}
Response 200：{"data": {"provider_id": "...", "key_rotated_at": "2026-03-31T..."}}
Response 403：权限不足
Response 404：provider 不存在
```

**业务规则：**
① 校验调用者角色为 kb_admin
② 校验 provider_id 存在
③ 加密新 key（使用与现有相同的加密方案）
④ 更新 provider 记录的 `encrypted_api_key` 字段
⑤ 记录轮换时间到 `key_rotated_at`（新增字段或记录到审计日志）
⑥ 返回成功（不返回 key 明文）
⑦ 旧 key 立即失效（下次 LLM 调用使用新 key）

---

#### 验收标准

- [ ] `POST /v1/model-providers/{id}/rotate-key` 成功后，后续 LLM 调用使用新 key
- [ ] 非 kb_admin 调用 → 403
- [ ] 不存在的 provider_id → 404
- [ ] 安全文档说明了加密方案、密钥管理、轮换流程

---

#### 工作范围

**包含：** rotate-key API 端点 + 安全文档（~25 行代码 + 文档）
**不包含：** 自动 key 轮换调度；key 有效性验证（调用 LLM 测试）

---

#### 预估工作量

- Phase 1 读 model_providers.py + 加密方案：1 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 加密方案不一致导致新 key 无法解密 | 低 | 高 | Phase 1 确认加密方式，使用同一方案 |
| 轮换期间有 LLM 调用使用旧 key 失败 | 低 | 中 | 原子更新 DB 记录，旧 key 立即失效 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/routers/model_providers.py` 现有 CRUD 逻辑
> 2. 确认 API Key 的存储和加密方式（Fernet / 环境变量 / 明文）
> 3. 确认 model provider 表结构

---

### v0.47.8: 集成测试补全（ZIP/节点CRUD/跨租户拒绝）

**任务版本号：** v0.47.8
**优先级：** P2
**前置依赖：** v0.47.1-3（bug 修复完成后测试更有价值）

---

#### 背景与目标

**现状：** 以下关键路径缺少集成测试：ZIP 批量导入、架构节点 CRUD、跨租户隔离。

**目标（Goal）：** 补全 3 个集成测试文件，覆盖关键路径的 happy path + 边界条件 + 安全约束。

---

#### 后端变更

**新增文件：**
- `services/api/tests/test_batch_import_zip.py` — ZIP 导入端到端测试
  - 测试场景：有效 ZIP 上传 → 资产创建成功
  - 测试场景：空 ZIP → 合理错误返回
  - 测试场景：ZIP 中含不支持文件类型 → 跳过不支持文件
  - 测试场景：超大 ZIP → 大小限制检查

- `services/api/tests/test_architecture_nodes_crud.py` — 架构节点 CRUD 完整测试
  - 测试场景：创建/读取/更新/删除节点 → 正常 CRUD 流程
  - 测试场景：创建子节点 → 父子关系正确
  - 测试场景：删除有子节点的父节点 → 合理处理（级联或拒绝）
  - 测试场景：非 editor 角色创建 → 403

- `services/api/tests/test_cross_tenant_rejection.py` — 跨租户隔离测试
  - 测试场景：租户 A 的 JWT 访问租户 B 的项目 → 404 或 403
  - 测试场景：租户 A 的 JWT 操作租户 B 的文档 → 拒绝
  - 测试场景：租户 A 的 JWT 查看租户 B 的资产 → 空结果或拒绝

**业务规则：**
① 使用 pytest + TestClient（FastAPI）
② 每个测试文件独立可运行
③ 使用 fixtures 创建测试数据（tenant / project / user）
④ 跨租户测试需创建 2 个独立 tenant + 对应 JWT

---

#### 验收标准

- [ ] `pytest services/api/tests/test_batch_import_zip.py` — 全部通过
- [ ] `pytest services/api/tests/test_architecture_nodes_crud.py` — 全部通过
- [ ] `pytest services/api/tests/test_cross_tenant_rejection.py` — 全部通过
- [ ] 每个文件至少 4 个测试场景
- [ ] 跨租户测试明确验证隔离性（租户 A 不能看到租户 B 数据）

---

#### 工作范围

**包含：** 3 个测试文件（~150 行测试代码）
**不包含：** 前端 E2E 测试；性能测试；其他端点的测试补全

---

#### 预估工作量

- Phase 1 读现有测试结构 + fixtures：1 小时
- Phase 2 执行：4 小时
- Phase 3 测试（运行自身）：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 测试环境缺少 fixtures 或 conftest | 中 | 中 | Phase 1 确认现有测试基础设施 |
| ZIP 测试需要实际文件 | 低 | 低 | 使用 io.BytesIO 动态创建测试 ZIP |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/tests/` 目录结构和现有 conftest.py
> 2. 确认测试数据库和 fixture 创建方式
> 3. 确认 ZIP 导入、架构节点、租户隔离的 API 路由路径

---

## 第六章 实现约束

- 目录结构：遵循现有 `services/api/`、`packages/shared-models/` 结构
- Migration 命名：Alembic 标准，路径 `infra/sql/alembic/versions/`，revision ID 使用随机字符串
- 权限：所有新端点必须校验 JWT + 角色权限
- 审计：state-changing 操作记录审计日志

---

## 第七章 任务领取规则

每次只能领取一个任务。完成后按第九章格式汇报，确认后再领下一个。不混做不同阶段，衍生任务仅记录不执行。

---

## 第八章 测试要求

> 引用项目技术规范：`docs/tech-specs/testing-strategy.md`

| 层次 | 工具 | 覆盖重点 |
|------|------|---------|
| 后端单元测试 | pytest | pipeline params 校验、cleanup_old_logs 方法 |
| 后端集成测试 | pytest + TestClient | v0.47.1-3 bug 修复验证、v0.47.7 rotate-key 端点 |
| 前端 | 无 | v0.47 无前端变更 |

---

## 第九章 任务汇报格式

> 引用项目技术规范：`docs/tech-specs/dev-governance-part0-automation.md` §0.7

每个 `vX.Y.Z` 任务完成后，按以下 9 项结构报告：

1. **计划 / 当前迭代目标**
2. **文件变更清单**
3. **用户可见能力**
4. **真实场景验证**（至少 5 个场景）
5. **开放问题**
6. **收尾说明**
7. **版本状态更新**（VERSION / CHANGELOG / TODO_NEXT.md）
8. **commit 信息**
9. **是否继续下一个任务**

---

## 第十章 版本号管理

> 引用 `docs/tech-specs/dev-governance-part1-version.md` §1.1–§1.4

- 版本号格式：`v0.47.{Z}`，Z 为任务序号（1–8）
- 每完成一个任务，VERSION 更新为 `0.47.{Z}`
- CHANGELOG.md 追加变更记录
- Commit message：`feat|fix|refactor: 简要描述 (v0.47.{Z})`

---

## 第十一章 文档产出要求

> 引用 `docs/tech-specs/dev-governance-part0-automation.md` §0.7

每个任务完成后必须同步更新：VERSION / CHANGELOG.md / TODO_NEXT.md / 本计划文件中该任务状态

版本全部完成后产出：`docs/versions/phase-report-v0.47.md` + `docs/versions/seal-audit-v0.47.md`

---

## 第十二章 新增数据库表汇总

| 任务 | 表名 | 变更类型 | 字段 | 类型 | 约束 | 说明 |
|------|------|---------|------|------|------|------|
| v0.47.6 | `pipeline_stage_log` | **新增表** | `id` | UUID | PK, default uuid4 | 主键 |
| v0.47.6 | `pipeline_stage_log` | | `job_id` | UUID | FK→job.id, NOT NULL | 所属 job |
| v0.47.6 | `pipeline_stage_log` | | `stage_name` | VARCHAR(50) | NOT NULL | Stage 标识 |
| v0.47.6 | `pipeline_stage_log` | | `status` | VARCHAR(20) | NOT NULL | running/completed/skipped/failed |
| v0.47.6 | `pipeline_stage_log` | | `started_at` | TIMESTAMP | nullable | 开始时间 |
| v0.47.6 | `pipeline_stage_log` | | `finished_at` | TIMESTAMP | nullable | 结束时间 |
| v0.47.6 | `pipeline_stage_log` | | `token_usage` | JSONB | default {} | token 消耗 |
| v0.47.6 | `pipeline_stage_log` | | `error_message` | TEXT | nullable | 失败错误信息 |

合计：1 张新表（8 个字段），1 次 Alembic 迁移。

---

## 第十三章 开始前必须先输出

Agent 在进入 Phase 2 编码之前，必须先输出以下三项：

1. **当前代码现状理解** — 列出 pipeline-worker stages / ai_actions.py / audit_service / database.py 的当前状态
2. **第一个任务的实施计划** — 按实施计划模板输出
3. **第一个任务的预计修改文件清单**

**在这三项输出并经确认之前，不要开始写代码。**

---

## 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 计划周期 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|--------|----------|--------|------|
| v0.47.1 | 矛盾检测排除 draft 文档 | — | 2026-04-03 | 1 | ✅ Done |
| v0.47.2 | suggest_tags entity_types 从 pipeline config 读取 | — | — | 0 | Planned |
| v0.47.3 | Pipeline params JSON Schema 校验 | — | — | 0 | Planned |
| v0.47.4 | 数据库连接池显式配置 | — | — | 0 | Planned |
| v0.47.5 | 审计日志保留策略 + 归档 | — | — | 0 | Planned |
| v0.47.6 | Pipeline per-stage 执行日志表 | — | — | 0 | Planned |
| v0.47.7 | 模型 API Key 加密方案文档化 + 轮换 API | — | — | 0 | Planned |
| v0.47.8 | 集成测试补全 | — | — | 0 | Planned |

---

## 第十五章 变更记录

| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-31 | V1.0 初始版本 | Claude Code |
| 2026-03-31 | V2.0 按规范重写，补齐所有必填字段 | Claude Code |
| 2026-04-01 | V2.1 交叉审查修复：v0.47.6 Phase 1 前置确认强化 pipeline_job 表名验证 | Claude Code |
| 2026-04-01 | V2.2 交叉审查v2修复：C-1 pipeline_job→job FK 修正（4处）；C-2 published/reviewing→正确状态值（3处） | Claude Code |

---

## 第十六章 决策与假设

**关键决策：**
- v0.47 不引入新功能，聚焦修复和加固 — 原因：v0.46 引入大量新能力，需要巩固
- Pipeline stage log 使用 DB 表而非日志文件 — 原因：可查询、可聚合、为 v0.49 成本追踪铺路
- 审计日志清理采用 Celery beat 而非 DB 自身 TTL — 原因：PostgreSQL 无原生 TTL，pg_cron 需额外部署

**重要假设：**
- v0.46 全部完成后才启动 v0.47
- Celery beat 已可用或可快速配置
- 现有加密方案可通过代码审查确认

---

## 第十七章 版本级风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 连接池参数调优需要生产数据 | 低 | 低 | 设为可配置，文档化推荐值 |
| Celery periodic task 需要 celery beat | 中 | 低 | 备选方案：API 端点手动触发 |
| stage log 写入增加 DB 负载 | 低 | 低 | bulk insert，非关键路径 |
| 集成测试依赖测试环境完善度 | 中 | 中 | Phase 1 先确认测试基础设施 |
