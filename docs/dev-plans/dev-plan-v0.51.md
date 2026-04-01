# KB Platform v0.51 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v051
**版本**: V1.0（初始版）
**日期**: 2026-03-31
**基线**: v0.50 完成后
**依据**: WISHLIST W-03/W-05/W-06/W-10/W-14/W-15 + 生产就绪目标
**作者**: Claude Code（自动生成）

---

## 第一章 版本主题

**v0.51：生产就绪 & 商业化 — 水平扩展 + 租户分级 + SKILL 化 + 知识本体**

> v0.47-v0.50 补齐了 PRD 全部功能缺口。v0.51 是**从"能用"到"好用"的跃迁**：支撑多实例部署、SaaS 商业化分级、用户自定义知识处理规则、以及深度语义理解。完成 v0.51 后，KB Platform 达到生产级 SaaS 标准。

---

## 第二章 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.51.1 | 水平扩展 — Redis Sentinel + S3 迁移 | P0 | 待开发 | W-03 |
| v0.51.2 | 租户分级 — tier + feature_flags + quota | P0 | 待开发 | W-05 |
| v0.51.3 | 用户组织层级 — department/team 字段 | P1 | 待开发 | W-06 |
| v0.51.4 | Stage 条件执行 — 重排序 + 规则引擎 | P1 | 待开发 | W-10 |
| v0.51.5 | SKILL 驱动 Pipeline — 用户自定义提取规则 | P1 | 待开发 | W-14 |
| v0.51.6 | 知识本体建模 — 概念图 + 关系推理 | P2 | 待开发 | W-15 |
| v0.51.7 | OpenTelemetry 全链路追踪 | P2 | 待开发 | W-01 |

---

## 第三章 目标与边界

### 3.1 北极星校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ |
|-----|----------------|-------------|-------------|
| v0.51.1 | - | - | ✅ 生产部署 |
| v0.51.2 | - | - | ✅ 商业化 |
| v0.51.3 | - | - | ✅ 企业客户 |
| v0.51.4 | ✅ 整合端灵活性 | - | - |
| v0.51.5 | ✅ 整合端（用户驱动知识处理） | - | - |
| v0.51.6 | ✅ 图谱端深度（第四层语义） | - | - |
| v0.51.7 | - | - | ✅ 运维必备 |

### 3.2 明确不做

- 多区域部署（跨 region 数据同步）— 超出当前阶段
- GraphQL API — 当前 REST API 满足需求
- 实时协作编辑（CRDTs）— 非核心需求

---

## 第四章 执行顺序

```
基础设施链：v0.51.1 → v0.51.7
商业化链：v0.51.2 → v0.51.3
Pipeline 链：v0.51.4 → v0.51.5
语义链：v0.51.6（独立但最复杂）
```

建议：`v0.51.1 → v0.51.2 → v0.51.4 → v0.51.5 → v0.51.3 → v0.51.6 → v0.51.7`

---

## 第五章 各任务详细定义

---

### v0.51.1: 水平扩展 — Redis Sentinel + S3 迁移

**前置依赖：** 无

**背景：** 当前 Redis 单实例、MinIO 本地模式，不支持多实例部署。

**变更：**
- `packages/shared-config/shared_config/settings.py` — 新增：
  - `redis_sentinel_hosts`（逗号分隔）
  - `storage_backend`："minio" | "s3"
  - `s3_bucket`、`s3_region`、`s3_endpoint`
- `services/api/app/utils/storage.py` — StorageClient 适配 S3（使用 boto3）
- `services/api/app/middleware/rate_limit.py` — Redis 连接支持 Sentinel 模式
- Celery broker 连接支持 Sentinel
- 约 100 行

**验收标准：**
- 可通过环境变量切换 MinIO ↔ S3
- Redis Sentinel 故障转移后服务自动恢复
- 多 API 实例可同时运行

---

### v0.51.2: 租户分级 — tier + feature_flags + quota

**前置依赖：** 无

**变更：**
- `packages/shared-models/shared_models/tenant.py` — Tenant 表新增：
  ```
  tier: String(20) default="free"    # "free" | "pro" | "enterprise"
  feature_flags: JSONB default={}     # {"video_parsing": true, "skill_pipeline": false, ...}
  quota_projects: Integer default=3
  quota_docs_per_project: Integer default=1000
  quota_storage_gb: Integer default=5
  ```
- `services/api/app/deps.py` — 新增 `check_quota()` 依赖，资源创建前校验
- `services/api/app/deps.py` — 新增 `check_feature()` 依赖，功能调用前校验
- `infra/sql/alembic/versions/` — migration
- 约 80 行

**验收标准：**
- free 租户限制 3 项目 / 1000 文档 / 5GB
- feature_flags 控制视频解析、SKILL pipeline 等高级功能
- 超限时返回 403 + 友好提示

---

### v0.51.3: 用户组织层级

**前置依赖：** v0.51.2

**变更：**
- `packages/shared-models/shared_models/user.py` — User 新增 `department`、`team` 字段
- `packages/shared-models/shared_models/team.py` — 新增 Team 模型（id, kb_id, name, parent_team_id）
- 基于团队的项目权限分配
- 约 60 行

---

### v0.51.4: Stage 条件执行 — 重排序 + 规则引擎

**前置依赖：** 无

**变更：**
- `packages/shared-models/shared_models/pipeline_config.py` — PipelineStageConfig 新增：
  ```
  execution_order: Integer default=0
  condition: JSONB nullable=True    # {"min_docs": 100, "if_feature": "quality_check_v2"}
  ```
- `services/pipeline-worker/worker/tasks.py` — stage 执行按 execution_order 排序，条件不满足则跳过
- 约 40 行

---

### v0.51.5: SKILL 驱动 Pipeline — 用户自定义提取规则

**前置依赖：** v0.51.4

**背景：** Shiji-KB 使用 54 个 SKILL 文档驱动处理。用户希望定义自己的实体提取规则、分类逻辑、文档模板。

**变更：**
- `packages/shared-models/shared_models/skill.py` — 新模型：
  ```
  Skill:
    id, project_id, stage_name, name, description,
    prompt_template: Text    # 用户定义的 prompt 模板
    input_schema: JSONB      # 期望输入格式
    output_schema: JSONB     # 期望输出格式
    version: Integer
    is_active: Boolean
  ```
- `services/api/app/routers/skills.py` — CRUD API
- `services/pipeline-worker/worker/stages/*.py` — 各 stage 检查是否有用户 SKILL，有则使用 SKILL prompt 替代默认 prompt
- `apps/web/src/app/(dashboard)/projects/[id]/settings/skills/page.tsx` — SKILL 管理 UI
- 约 200 行

**验收标准：**
- 用户可为 classify stage 创建自定义 SKILL
- SKILL 的 prompt_template 在 pipeline 执行时被使用
- SKILL 有版本管理，可回滚

---

### v0.51.6: 知识本体建模 — 概念图 + 关系推理

**前置依赖：** v0.49.3（反思循环）

**背景：** 当前知识图谱停留在"文档→实体→关键词"两层。PRD 和 Shiji-KB 都指向更深的语义：概念层级、因果关系、推理规则。

**变更：**
- `packages/shared-models/shared_models/ontology.py` — 新模型：
  ```
  Concept:       id, project_id, name, definition, parent_concept_id
  ConceptRelation: id, source_id, target_id, relation_type, confidence, evidence_doc_id
                   relation_type: "is_a" | "part_of" | "causes" | "contradicts" | "depends_on"
  ```
- `services/ai-orchestrator/orchestrator/tasks.py` — 新增 `build_ontology` Celery task
  - 从已发布文档中提取概念和关系
  - 构建层级概念树
  - 识别因果链（A causes B causes C）
- `services/api/app/routers/ontology.py` — 查询 API
- `apps/web/src/app/(dashboard)/projects/[id]/ontology/page.tsx` — 本体可视化页
- 约 250 行

**验收标准：**
- 从 100 篇文档中自动提取概念树
- 支持 5 种关系类型
- 可视化展示概念层级和因果链

---

### v0.51.7: OpenTelemetry 全链路追踪

**前置依赖：** v0.49.6（Prometheus）

**变更：**
- 所有 4 个服务接入 OpenTelemetry SDK
- API → Celery → AI Orchestrator 跨服务 trace 关联
- 约 60 行（每个服务 ~15 行 OTEL 初始化）

---

## 第六章 风险

| 风险 | 缓解 |
|------|------|
| S3 迁移需要数据迁移脚本 | 提供 migrate_minio_to_s3 CLI 工具 |
| 租户配额检查增加请求延迟 | Redis 缓存配额信息（TTL 60s） |
| SKILL prompt 注入风险 | SKILL prompt 不直接拼接用户输入，通过 schema 约束 |
| 知识本体提取 LLM 成本高 | 分批处理，仅对已发布文档执行，可配置关闭 |
| OTEL 收集器部署 | 提供 Docker Compose 配置 |

---

## 第七章 里程碑总览

v0.51 完成后，KB Platform 达到：
- **功能完整度**：PRD 100% 覆盖 + WISHLIST 16/16 项完成
- **安全等级**：企业级（RBAC + 租户隔离 + 2FA + 文件扫描 + 审计 + 加密）
- **性能等级**：生产级（pgvector + 连接池 + Redis Sentinel + S3）
- **智能等级**：行业领先（4 层语义 + 反思循环 + SKILL 驱动）
- **商业就绪**：SaaS 分级 + 配额 + 成本追踪
