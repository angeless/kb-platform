# KB Platform v0.51 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v051
**版本**: V2.0（规范重写版）
**日期**: 2026-03-31
**基线**: v0.50 完成后
**依据**: WISHLIST W-03/W-05/W-06/W-10/W-14/W-15 + 生产就绪目标
**作者**: Claude Code（自动生成）

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

基于 v0.50 完成后的代码增量增强。禁止重构无关模块。

### 1.2 继承已有能力

- **Redis**（已部署）— 缓存 / 限流 / 成本追踪 / 确认码
- **MinIO**（`services/api/app/utils/storage.py`）— 文件存储
- **Celery**（`services/pipeline-worker/` + `services/ai-orchestrator/`）— 任务队列
- **Pipeline 配置化**（v0.46）— PipelineStageConfig enable/disable + params
- **Stage 条件执行基础**（v0.46.2）— config 参数化 + enabled 开关
- **PipelineStageLog**（v0.47.6）— per-stage 日志 + token_usage
- **反思循环 v2**（v0.49.4-5）— 规则校验 + AI 自检
- **Prometheus**（v0.49.8）— /metrics 端点
- **CrossReference**（5 种关系类型）— contradicts / related / ...
- **Tenant 模型**（`packages/shared-models/shared_models/tenant.py`）— KB 级租户
- **User 模型**（`packages/shared-models/shared_models/user.py`）— 用户 + RBAC

### 1.3 最小改动 / 1.4 任务领取规则

同 v0.47。

---

## 第二章 当前阶段事实

### 2.1 版本主题

**v0.51：生产就绪 & 商业化 — 水平扩展 + 租户分级 + SKILL 化 + 知识本体**

> v0.47-v0.50 补齐了功能缺口。v0.51 是从"能用"到"好用"的跃迁：支撑多实例部署、SaaS 分级、用户自定义知识处理规则、深度语义理解。

---

## 第三章 本轮目标与边界

### 3.1 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.51.1 | 水平扩展 — S3 存储适配 | P0 | 待开发 | W-03 |
| v0.51.2 | 水平扩展 — Redis Sentinel 支持 | P0 | 待开发 | W-03 |
| v0.51.3 | 租户分级 — tier + feature_flags + quota | P0 | 待开发 | W-05 |
| v0.51.4 | 用户组织层级 — department/team 字段 | P1 | 待开发 | W-06 |
| v0.51.5 | Stage 条件执行 — 重排序 + 规则引擎 | P1 | 待开发 | W-10 |
| v0.51.6 | SKILL 驱动 Pipeline — DB 模型 + CRUD API | P1 | 待开发 | W-14 |
| v0.51.7 | SKILL 驱动 Pipeline — Stage 集成 | P1 | 待开发 | W-14 |
| v0.51.8 | SKILL 驱动 Pipeline — 管理 UI | P1 | 待开发 | W-14 |
| v0.51.9 | 知识本体建模 — DB 模型 + API | P2 | 待开发 | W-15 |
| v0.51.10 | 知识本体建模 — AI 提取 task | P2 | 待开发 | W-15 |
| v0.51.11 | 知识本体建模 — 可视化页 | P2 | 待开发 | W-15 |
| v0.51.12 | OpenTelemetry 全链路追踪 | P2 | 待开发 | W-01 |

### 3.2 北极星三问校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ |
|-----|----------------|-------------|-------------|
| v0.51.1 | - | - | ✅ 生产部署 |
| v0.51.2 | - | - | ✅ 生产部署 |
| v0.51.3 | - | - | ✅ 商业化 |
| v0.51.4 | - | - | ✅ 企业客户 |
| v0.51.5 | ✅ 整合端灵活性 | - | - |
| v0.51.6 | ✅ 整合端（SKILL 基础） | - | - |
| v0.51.7 | ✅ 整合端（用户驱动知识处理） | - | - |
| v0.51.8 | - | ✅ 输出接口 | - |
| v0.51.9 | ✅ 图谱端深度 | - | - |
| v0.51.10 | ✅ 图谱端深度（AI 提取） | - | - |
| v0.51.11 | - | ✅ 输出接口 | - |
| v0.51.12 | - | - | ✅ 运维必备 |

### 3.3 明确不做

- 多区域部署（跨 region 数据同步）— 超出当前阶段
- GraphQL API — 当前 REST API 满足需求
- 实时协作编辑（CRDTs）— 非核心需求

---

## 第四章 执行顺序

```
基础设施链：v0.51.1 → v0.51.2 → v0.51.12
商业化链：v0.51.3 → v0.51.4
Pipeline 链：v0.51.5 → v0.51.6 → v0.51.7 → v0.51.8
语义链：v0.51.9 → v0.51.10 → v0.51.11
```

建议：`v0.51.1 → v0.51.2 → v0.51.3 → v0.51.5 → v0.51.6 → v0.51.7 → v0.51.4 → v0.51.8 → v0.51.9 → v0.51.10 → v0.51.11 → v0.51.12`

---

## 第五章 各任务详细定义

---

### v0.51.1: 水平扩展 — S3 存储适配

**任务版本号：** v0.51.1
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**现状：** MinIO 本地模式，不支持多实例共享存储。

**目标（Goal）：** 将 StorageClient 适配 S3（使用 boto3），通过环境变量切换 MinIO ↔ S3。

---

#### 后端变更

**修改文件：**
- `packages/shared-config/shared_config/settings.py` — 修改：
  - 新增 `storage_backend: str = "minio"` — "minio" | "s3" 切换开关
  > ⚠️ 注意：`s3_endpoint`, `s3_access_key`, `s3_secret_key`, `s3_bucket`, `s3_region` **已存在**于 settings.py（用于 MinIO 配置），无需重复添加。仅需新增 `storage_backend` 字段。

- `services/api/app/utils/storage.py` — StorageClient 重构：
  - 抽象接口：`upload(key, data)` / `download(key)` / `delete(key)` / `presign_url(key)`
  - MinioStorage 实现（沿用现有逻辑）
  - S3Storage 实现（使用 boto3）
  - 工厂函数：根据 `storage_backend` 选择实现

- 依赖文件 — 新增 `boto3`

**业务规则：**
① `storage_backend="minio"` → 使用现有 MinIO 客户端（行为不变）
② `storage_backend="s3"` → 使用 boto3 S3 客户端
③ 所有文件操作（upload / download / delete / presign）通过统一接口
④ S3 认证使用 boto3 默认链（环境变量 / IAM role / 配置文件）
⑤ `s3_endpoint` 非空时用于 S3 兼容服务（如本地 MinIO 测试）

---

#### 验收标准

- [ ] `STORAGE_BACKEND=minio` → 文件上传/下载正常（不回归）
- [ ] `STORAGE_BACKEND=s3` + 有效 AWS 凭证 → 文件上传/下载到 S3
- [ ] `STORAGE_BACKEND=s3` + `S3_ENDPOINT=http://localhost:9000` → 可连接本地 MinIO
- [ ] 切换 backend 后无需修改业务代码
- [ ] presign URL 在两种 backend 下都正常工作

---

#### 工作范围

**包含：** storage.py 重构 + settings 配置 + boto3 依赖（~60 行）
**不包含：** 数据迁移脚本（MinIO → S3）；多 bucket 支持

---

#### 预估工作量

- Phase 1 读 storage.py 当前实现 + MinIO 调用方式：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| MinIO 和 S3 API 差异 | 低 | 中 | MinIO 兼容 S3 API，差异有限 |
| boto3 依赖增加镜像大小 | 低 | 低 | ~10MB，可接受 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/utils/storage.py` 完整实现
> 2. 确认所有调用 storage 的位置（上传 / 下载 / 删除）
> 3. 确认 MinIO 客户端 API 与 boto3 的差异

---

### v0.51.2: 水平扩展 — Redis Sentinel 支持

**任务版本号：** v0.51.2
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**现状：** Redis 单实例，无故障转移。

**目标（Goal）：** Redis 连接支持 Sentinel 模式，故障转移后服务自动恢复。

---

#### 后端变更

**修改文件：**
- `packages/shared-config/shared_config/settings.py` — 新增：
  - `redis_sentinel_hosts: str = ""` — 逗号分隔的 sentinel 地址（如 "host1:26379,host2:26379"）
  - `redis_sentinel_master: str = "mymaster"` — Sentinel master 名称

- `services/api/app/middleware/rate_limit.py`（或 Redis 连接初始化位置）— 修改：
  - 若 `redis_sentinel_hosts` 非空 → 使用 `redis.sentinel.Sentinel` 创建连接
  - 否则沿用现有单实例连接

- Celery broker 配置 — 支持 Sentinel URL 格式

**业务规则：**
① `redis_sentinel_hosts` 为空 → 使用现有单实例 Redis（行为不变）
② `redis_sentinel_hosts` 非空 → 创建 Sentinel 实例，通过 master 发现连接
③ Sentinel 故障转移后，新的 master 自动被发现
④ Celery broker 也支持 Sentinel（`sentinel://host1:26379,host2:26379/0`）

---

#### 验收标准

- [ ] `REDIS_SENTINEL_HOSTS` 未设置 → 使用单实例 Redis（不回归）
- [ ] 设置 Sentinel hosts → 通过 Sentinel 发现 master
- [ ] Sentinel 故障转移后 → 服务自动恢复（不需重启）
- [ ] Celery broker 通过 Sentinel 连接
- [ ] 多 API 实例可同时运行且共享 Redis 状态

---

#### 工作范围

**包含：** Redis 连接改造 + Celery broker 配置 + settings（~40 行）
**不包含：** Sentinel 部署；Redis Cluster 支持

---

#### 预估工作量

- Phase 1 读 Redis 连接初始化位置 + Celery broker 配置：1 小时
- Phase 2 执行：2.5 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Sentinel 配置复杂 | 中 | 中 | 文档化配置步骤 |
| Celery sentinel URL 格式差异 | 低 | 中 | Phase 1 确认 Celery sentinel 支持 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读所有 Redis 连接初始化位置（rate_limit / cost_tracker / 缓存）
> 2. 确认 Celery broker URL 格式
> 3. 确认 redis-py sentinel API

---

### v0.51.3: 租户分级 — tier + feature_flags + quota

**任务版本号：** v0.51.3
**优先级：** P0
**前置依赖：** 无（建议 v0.51.1 S3 适配先完成，存储量计算需通过统一 StorageClient 接口）

---

#### 背景与目标

**目标（Goal）：** 在 Tenant 表新增分级字段（free/pro/enterprise），实现配额检查和功能开关机制。

---

#### 数据库变更

**修改文件：**
- `packages/shared-models/shared_models/tenant.py` — Tenant 新增字段：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| tier | VARCHAR(20) | NOT NULL, default 'free' | "free" / "pro" / "enterprise" |
| feature_flags | JSONB | default {} | `{"video_parsing": true, "skill_pipeline": false}` |
| quota_projects | INTEGER | default 3 | 项目数上限 |
| quota_docs_per_project | INTEGER | default 1000 | 每项目文档上限 |
| quota_storage_gb | INTEGER | default 5 | 存储上限（GB） |

- `infra/sql/alembic/versions/` — migration

**修改文件：**
- `services/api/app/deps.py` — 新增 2 个依赖：
  ```
  async def check_quota(resource_type: str, kb_id: str):
      # 资源创建前校验配额（项目数 / 文档数 / 存储）
      # 超限 → raise HTTPException(403, "quota_exceeded")

  async def check_feature(feature_name: str, kb_id: str):
      # 功能调用前校验 feature_flags
      # 未开启 → raise HTTPException(403, "feature_not_available")
  ```

**业务规则：**
① 创建项目时 → `check_quota("projects", kb_id)` → 当前项目数 >= quota_projects → 403
② 创建文档时 → `check_quota("docs", kb_id)` → 当前文档数 >= quota_docs_per_project → 403
③ 上传文件时 → `check_quota("storage", kb_id)` → 当前存储 >= quota_storage_gb → 403
  - **存储量计算方式**：查询 `Asset` 表 `SUM(file_size)` WHERE `kb_id=X`（Asset.file_size 字段记录原始文件大小）。通过 Redis 缓存累计值（key: `storage:{kb_id}`，TTL 60s），文件上传/删除时主动 invalidate 缓存。不直接查询 MinIO/S3 API 避免延迟。
④ 调用高级功能时 → `check_feature("video_parsing", kb_id)` → feature_flags 中为 false → 403
⑤ 配额信息缓存到 Redis（TTL 60s），避免频繁 DB 查询
⑥ 超限返回：`{"error": "quota_exceeded", "detail": "Free tier limited to 3 projects", "upgrade_url": "..."}`

---

#### 验收标准

- [ ] free 租户限制 3 项目 → 创建第 4 个时 403
- [ ] free 租户限制 1000 文档/项目 → 超限时 403
- [ ] feature_flags `{"video_parsing": false}` → 调用视频解析时 403
- [ ] pro 租户有更高配额 → 正常创建
- [ ] 超限返回友好提示 + 升级引导
- [ ] 配额检查不显著增加请求延迟（Redis 缓存）

---

#### 工作范围

**包含：** Tenant 字段 + migration + check_quota / check_feature 依赖（~80 行）
**不包含：** 计费系统集成；前端配额展示页；tier 变更 API

---

#### 预估工作量

- Phase 1 读 Tenant 模型 + deps.py 依赖注入模式：1 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 配额检查增加请求延迟 | 低 | 低 | Redis 缓存（TTL 60s） |
| 多 API 实例间配额不一致 | 低 | 中 | Redis 共享状态 + 短 TTL |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 Tenant 模型当前字段
> 2. 读 deps.py 现有依赖注入模式
> 3. 确认资源计数方式（项目数 / 文档数 / 存储量）— **存储量需确认 Asset 表是否有 file_size 字段，若无需在本任务中新增**
> 4. 确认 v0.51.1 StorageClient 是否已完成（影响存储量统计方式）

---

### v0.51.4: 用户组织层级 — department/team 字段

**任务版本号：** v0.51.4
**优先级：** P1
**前置依赖：** v0.51.3（租户分级，enterprise tier 需要组织层级）

---

#### 背景与目标

**目标（Goal）：** 在 User 模型新增 department/team 字段，新增 Team 模型支持基于团队的项目权限分配。

---

#### 数据库变更

**修改文件：**
- `packages/shared-models/shared_models/user.py` — User 新增字段：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| department | VARCHAR(100) | nullable | 部门名称 |
| team_id | UUID | FK→team.id, nullable | 所属团队 |

**新增文件：**
- `packages/shared-models/shared_models/team.py` — 新模型：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, default uuid4 | 主键 |
| kb_id | UUID | FK→tenant.id, NOT NULL | 所属租户 |
| name | VARCHAR(100) | NOT NULL | 团队名称 |
| parent_team_id | UUID | FK→team.id, nullable | 上级团队（树形结构） |
| created_at | TIMESTAMP | default now() | 创建时间 |

- `infra/sql/alembic/versions/` — migration

**新增端点：**
- `services/api/app/routers/teams.py` — Team CRUD API：

```
GET /v1/teams
认证：JWT，viewer+
Query：?parent_team_id=uuid（可选，获取子团队）
Response 200：{"data": [...], "total": N}

POST /v1/teams
认证：JWT，kb_admin
Body：{"name": "工程团队", "parent_team_id": "uuid|null"}
Response 201：{"data": {"id": "uuid", "kb_id": "...", "name": "工程团队", "parent_team_id": null, "created_at": "..."}}
Response 400：name 为空
Response 403：非 kb_admin

PUT /v1/teams/{team_id}
认证：JWT，kb_admin
Body：{"name": "新名称", "parent_team_id": "uuid|null"}
Response 200：{"data": {...}}
Response 404：team 不存在

DELETE /v1/teams/{team_id}
认证：JWT，kb_admin
Response 204
Response 400：team 下有成员时拒绝删除（需先移除成员）

PUT /v1/users/{user_id}/team
认证：JWT，kb_admin
Body：{"team_id": "uuid|null"}
Response 200：{"data": {"user_id": "...", "team_id": "...", "department": "..."}}
Response 404：user 不存在
```

**业务规则：**
① Team 支持树形结构（parent_team_id 自引用）
② 一个 User 属于一个 Team
③ 项目可分配给 Team → Team 中所有成员获得项目访问权限
④ kb_admin 管理 Team CRUD
⑤ 删除 Team 前校验无成员（team 下 User 数 == 0），否则 400
⑥ kb_id 从 JWT 中获取（租户隔离）
⑦ 所有 state-changing 操作记录审计日志

---

#### 验收标准

- [ ] 创建 Team → 返回 team 数据含 id / kb_id / name
- [ ] 用户分配到 Team → user.team_id 正确
- [ ] Team 树形结构（A → B → C）正确
- [ ] 基于 Team 的项目权限正常工作
- [ ] 删除有成员的 Team → 400 拒绝
- [ ] 非 kb_admin 创建/删除 Team → 403
- [ ] 跨租户不可见（kb_id 隔离）

---

#### 工作范围

**包含：** Team 模型 + User 字段 + migration + Team CRUD API（~60 行）
**不包含：** 团队级权限的复杂规则（继承 / 覆盖）；前端团队管理页

---

#### 预估工作量

- Phase 1 读 User 模型 + 权限系统：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 树形结构查询性能 | 低 | 低 | 团队层级有限（通常 < 5 层） |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 User 模型 + 现有权限系统
> 2. 确认项目权限分配方式

---

### v0.51.5: Stage 条件执行 — 重排序 + 规则引擎

**任务版本号：** v0.51.5
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**目标（Goal）：** 在 PipelineStageConfig 新增执行顺序和条件字段，支持 stage 重排序和条件跳过。

---

#### 数据库变更

**修改文件：**
- `packages/shared-models/shared_models/pipeline_config.py` — PipelineStageConfig 新增：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| execution_order | INTEGER | default 0 | 执行顺序（越小越先） |
| condition | JSONB | nullable | `{"min_docs": 100, "if_feature": "quality_check_v2"}` |

- `infra/sql/alembic/versions/` — migration

**修改文件：**
- `services/pipeline-worker/worker/tasks.py` — stage 执行逻辑修改：
  - 按 `execution_order` 排序 stage 列表（而非硬编码顺序）
  - 每个 stage 执行前检查 `condition`：
    - `min_docs`: 项目文档数 >= N 才执行
    - `if_feature`: feature_flags 中对应值为 true 才执行

**业务规则：**
① 按 execution_order 升序排列 stage（相同值保持默认顺序）
② condition 为 NULL → 无条件执行
③ condition.min_docs 检查：当前项目文档数 < N → 跳过
④ condition.if_feature 检查：tenant.feature_flags 中对应值为 false → 跳过
⑤ 跳过的 stage 记录到 PipelineStageLog（status=skipped, reason=condition）

---

#### 验收标准

- [ ] 设置 execution_order → stage 按顺序执行
- [ ] condition `{"min_docs": 100}` + 项目仅 50 文档 → stage 跳过
- [ ] condition `{"if_feature": "quality_check_v2"}` + feature 未开启 → stage 跳过
- [ ] 无 condition → 正常执行（不回归）
- [ ] 跳过记录到 PipelineStageLog

---

#### 工作范围

**包含：** 2 个新字段 + migration + tasks.py 条件执行逻辑（~40 行）
**不包含：** 前端 UI（条件配置界面）；复杂条件组合（AND/OR）

---

#### 预估工作量

- Phase 1 读 tasks.py stage 执行逻辑 + PipelineStageConfig：1 小时
- Phase 2 执行：2.5 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 重排序破坏 stage 依赖关系 | 中 | 高 | 校验 embed 必须在 doc_generate 之后 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 tasks.py 中 stage 执行顺序逻辑
> 2. 确认 stage 间是否有硬依赖关系

---

### v0.51.6: SKILL 驱动 Pipeline — DB 模型 + CRUD API

**任务版本号：** v0.51.6
**优先级：** P1
**前置依赖：** v0.51.5（条件执行框架）

---

#### 背景与目标

**目标（Goal）：** 新增 Skill 模型，定义用户自定义的知识处理规则（prompt 模板 + input/output schema），并提供 CRUD API。

---

#### 数据库变更

**新增文件：**
- `packages/shared-models/shared_models/skill.py` — 新模型：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, default uuid4 | 主键 |
| project_id | UUID | FK→project.id, NOT NULL | 所属项目 |
| stage_name | VARCHAR(50) | NOT NULL | 关联 stage（classify / doc_generate / ...） |
| name | VARCHAR(100) | NOT NULL | SKILL 名称 |
| description | TEXT | nullable | SKILL 描述 |
| prompt_template | TEXT | NOT NULL | 用户定义的 prompt 模板 |
| input_schema | JSONB | default {} | 期望输入格式 |
| output_schema | JSONB | default {} | 期望输出格式 |
| version | INTEGER | default 1 | 版本号（支持回滚） |
| is_active | BOOLEAN | default true | 是否激活 |
| created_at | TIMESTAMP | default now() | 创建时间 |
| updated_at | TIMESTAMP | default now() | 更新时间 |

- `infra/sql/alembic/versions/` — migration

**新增端点：**
- `services/api/app/routers/skills.py` — CRUD API：

```
GET /v1/projects/{project_id}/skills
认证：JWT，viewer+
Response 200：{"data": [...], "total": N}

POST /v1/projects/{project_id}/skills
认证：JWT，editor+
Body：{"stage_name": "classify", "name": "金融实体提取", "prompt_template": "...", "input_schema": {...}, "output_schema": {...}}
Response 201：{"data": {"id": "uuid", ...}}

PUT /v1/projects/{project_id}/skills/{skill_id}
认证：JWT，editor+
Body：{"prompt_template": "...", "is_active": true}
Response 200：{"data": {...}}
说明：更新时 version 自动 +1

DELETE /v1/projects/{project_id}/skills/{skill_id}
认证：JWT，editor+
Response 204

GET /v1/projects/{project_id}/skills/{skill_id}/versions
认证：JWT，viewer+
Response 200：历史版本列表
```

**业务规则：**
① 每个 SKILL 关联一个 stage_name
② prompt_template 必填，不能为空
③ 更新 SKILL 时自动递增 version（旧版本保留用于回滚）
④ is_active=false 的 SKILL 不参与 pipeline 执行
⑤ 一个项目的一个 stage 可有多个 SKILL（但只有 is_active=true 的生效）

---

#### 验收标准

- [ ] 创建 SKILL → 返回完整数据含 version=1
- [ ] 更新 SKILL → version 自动 +1
- [ ] 列表 API 返回项目所有 SKILL
- [ ] 版本历史 API 返回 SKILL 的所有版本
- [ ] 删除 SKILL → 软删除或硬删除
- [ ] 非 editor 创建 → 403

---

#### 工作范围

**包含：** Skill 模型 + migration + CRUD API 5 个端点（~100 行）
**不包含：** Pipeline 集成（v0.51.7）；前端 UI（v0.51.8）

---

#### 预估工作量

- Phase 1 读 pipeline stage 名称列表 + 现有 router 模式：1 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| SKILL prompt 注入风险 | 中 | 高 | prompt 不直接拼接用户输入，通过 schema 约束 |
| 版本管理复杂度 | 低 | 低 | 简单递增 version，不做分支 |

> ⚠️ **Phase 1 前置确认：**
> 1. 确认 pipeline stage 名称枚举
> 2. 读现有 router 注册模式

---

### v0.51.7: SKILL 驱动 Pipeline — Stage 集成

**任务版本号：** v0.51.7
**优先级：** P1
**前置依赖：** v0.51.6（Skill 模型和 API 存在）

---

#### 背景与目标

**目标（Goal）：** 修改各 stage，执行时检查是否有用户 SKILL，有则使用 SKILL 的 prompt_template 替代默认 prompt。

---

#### 后端变更

**修改文件：**
- `services/pipeline-worker/worker/stages/classify.py` — 执行时：
  - 查询 `Skill.objects.filter(project_id=pid, stage_name="classify", is_active=True)`
  - 若有 SKILL → 使用 SKILL 的 `prompt_template` 替代默认 classify prompt
  - 使用 `input_schema` 格式化输入数据
  - 使用 `output_schema` 校验 LLM 输出

- `services/pipeline-worker/worker/stages/doc_generate.py` — 同理
- `services/pipeline-worker/worker/stages/quality_check.py` — 同理
- 其他 stage 可扩展（但 v0.51.7 仅做 classify / doc_generate / quality_check 三个核心 stage）

**业务规则：**
① 每个 stage 执行前查询项目的 active SKILL
② 有 SKILL → 使用 SKILL.prompt_template 构建 LLM prompt
③ 无 SKILL → 使用默认 prompt（行为不变）
④ SKILL prompt 中可使用占位符（`{content}`, `{entity_types}` 等），由 stage 填充
⑤ SKILL output_schema 用于校验 LLM 返回格式
⑥ 校验失败 → 记录 WARNING + fallback 默认处理

---

#### 验收标准

- [ ] 项目有 classify SKILL → pipeline 使用 SKILL prompt 执行分类
- [ ] SKILL prompt 产出的结果符合 output_schema
- [ ] 无 SKILL → 使用默认 prompt（不回归）
- [ ] SKILL prompt 有错误（格式不对）→ fallback 默认 + WARNING 日志
- [ ] 三个核心 stage 均支持 SKILL

---

#### 工作范围

**包含：** classify / doc_generate / quality_check 三个 stage 的 SKILL 集成（~60 行）
**不包含：** 其他 stage 的 SKILL 集成；SKILL 调试工具

---

#### 预估工作量

- Phase 1 读三个 stage 的 prompt 构建方式：1.5 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 用户 SKILL prompt 导致 LLM 输出异常 | 中 | 中 | output_schema 校验 + fallback |
| 占位符替换不完整 | 低 | 中 | 定义明确的占位符列表 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 classify / doc_generate / quality_check 的 prompt 构建逻辑
> 2. 确认 prompt 占位符方案

---

### v0.51.8: SKILL 驱动 Pipeline — 管理 UI

**任务版本号：** v0.51.8
**优先级：** P1
**前置依赖：** v0.51.6（API 可用）

---

#### 背景与目标

**目标（Goal）：** 在项目设置中新增 SKILL 管理页面，允许用户创建、编辑、查看版本历史、切换激活状态。

---

#### 前端变更

**新增文件：**
- `apps/web/src/app/(dashboard)/projects/[id]/settings/skills/page.tsx` — SKILL 管理页：
  - SKILL 列表（按 stage 分组）
  - 创建 SKILL 弹窗（name + stage 下拉 + prompt 编辑器 + schema JSON 编辑器）
  - 编辑 SKILL 弹窗（修改 prompt / schema / is_active）
  - 版本历史面板（查看历史版本 prompt）
  - 激活/停用切换

**业务规则：**
① 页面展示项目所有 SKILL，按 stage_name 分组
② 创建时 stage_name 为下拉选择（7 个 stage）
③ prompt_template 使用多行文本编辑器
④ input_schema / output_schema 使用 JSON 编辑器
⑤ viewer 角色：只读
⑥ editor+ 角色：可创建/编辑/删除

---

#### 验收标准

- [ ] SKILL 列表正确展示（按 stage 分组）
- [ ] 创建 SKILL → 表单提交后列表刷新
- [ ] 编辑 SKILL → 版本自动递增
- [ ] 版本历史展示正确
- [ ] 激活/停用切换正常
- [ ] viewer 角色下编辑功能 disabled

---

#### 工作范围

**包含：** skills/page.tsx SKILL 管理全部 UI（~120 行）
**不包含：** SKILL 效果预览；SKILL 市场/共享

---

#### 预估工作量

- Phase 1 读项目设置页结构：0.5 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| JSON 编辑器组件不存在 | 中 | 中 | 使用 textarea + JSON.parse 校验 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读项目设置页导航结构
> 2. 确认现有 JSON 编辑器或 textarea 组件

---

### v0.51.9: 知识本体建模 — DB 模型 + API

**任务版本号：** v0.51.9
**优先级：** P2
**前置依赖：** 无

---

#### 背景与目标

**目标（Goal）：** 新增 Concept 和 ConceptRelation 模型，支持概念层级和关系类型，提供查询 API。

---

#### 数据库变更

**新增文件：**
- `packages/shared-models/shared_models/ontology.py` — 2 个新模型：

**Concept 表：**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| project_id | UUID | FK→project.id, NOT NULL | 所属项目 |
| name | VARCHAR(200) | NOT NULL | 概念名称 |
| definition | TEXT | nullable | 概念定义 |
| parent_concept_id | UUID | FK→concept.id, nullable | 上级概念（树形） |
| created_at | TIMESTAMP | default now() | 创建时间 |

**ConceptRelation 表：**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| source_id | UUID | FK→concept.id, NOT NULL | 源概念 |
| target_id | UUID | FK→concept.id, NOT NULL | 目标概念 |
| relation_type | VARCHAR(20) | NOT NULL | "is_a" / "part_of" / "causes" / "contradicts" / "depends_on" |
| confidence | FLOAT | default 1.0 | 置信度 |
| evidence_doc_id | UUID | FK→knowledge_doc.id, nullable | 证据文档 |
| created_at | TIMESTAMP | default now() | 创建时间 |

**新增端点：**
- `services/api/app/routers/ontology.py` — 查询 API：

```
GET /v1/projects/{project_id}/ontology/concepts
认证：JWT，viewer+
Query：?parent_id=uuid（可选，获取子概念）
Response 200：{"data": [...]}

GET /v1/projects/{project_id}/ontology/relations
认证：JWT，viewer+
Query：?concept_id=uuid&relation_type=causes
Response 200：{"data": [...]}

GET /v1/projects/{project_id}/ontology/tree
认证：JWT，viewer+
Response 200：树形结构的概念层级
```

---

#### 验收标准

- [ ] Concept 表创建成功，支持树形结构
- [ ] ConceptRelation 支持 5 种关系类型
- [ ] 查询 API 返回正确数据
- [ ] 树形查询返回层级结构

---

#### 工作范围

**包含：** 2 个模型 + migration + 3 个查询 API（~80 行）
**不包含：** AI 自动提取（v0.51.10）；可视化（v0.51.11）

---

#### 预估工作量

- Phase 1 读 CrossReference 模型参考关系设计：0.5 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 概念数量大时树形查询慢 | 低 | 中 | 限制查询深度 + 分页 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 CrossReference 模型参考设计模式
> 2. 确认树形查询方式（递归 CTE 或应用层递归）

---

### v0.51.10: 知识本体建模 — AI 提取 task

**任务版本号：** v0.51.10
**优先级：** P2
**前置依赖：** v0.51.9（Concept / ConceptRelation 模型存在）

---

#### 背景与目标

**目标（Goal）：** 新增 `build_ontology` Celery task，从已发布文档中自动提取概念和关系，构建层级概念树和因果链。

---

#### 后端变更

**新增逻辑：**
- `services/ai-orchestrator/orchestrator/tasks.py` — 新增 task：
  ```
  @celery_app.task(name="orchestrator.build_ontology")
  def build_ontology(project_id: str) -> dict:
      # 1. 加载项目 published 文档的 summary + keywords
      # 2. 调用 LLM 提取概念（名称 + 定义 + 层级）
      # 3. 调用 LLM 识别概念间关系（5 种类型）
      # 4. 写入 Concept + ConceptRelation 表
      # 返回 {"concepts_count": N, "relations_count": M}
  ```

- `services/ai-orchestrator/orchestrator/prompts.py` — 新增：
  - `build_concept_extraction_prompt()` — 提取概念
  - `build_relation_inference_prompt()` — 推理关系

**API 触发端点：**
```
POST /v1/projects/{project_id}/ontology/build
认证：JWT，editor+
Response 200：{"data": {"job_id": "uuid", "status": "started"}}
```

**业务规则：**
① 加载 published 文档的 summary + keywords（轻量数据）
② 分批提取概念（每批 20 篇文档）
③ 提取后去重（LLM 判断同义概念合并）
④ 概念层级由 LLM 推断（A is_a B → A 的 parent = B）
⑤ 关系类型：is_a / part_of / causes / contradicts / depends_on
⑥ confidence 由 LLM 返回（0.0-1.0）
⑦ 可通过 pipeline config 关闭（配置 `ontology_enabled: false`）

---

#### 验收标准

- [ ] 100 篇文档 → 提取概念树（至少 3 层深度）
- [ ] 概念间关系包含 5 种类型
- [ ] 关系有 confidence 评分
- [ ] 概念去重（同义词不重复）
- [ ] 可通过 API 触发构建

---

#### 工作范围

**包含：** build_ontology task + prompts + 触发 API（~100 行）
**不包含：** 增量更新（全量重建）；实时本体更新

---

#### 预估工作量

- Phase 1 读已有 AI task 模式 + prompt 设计：1.5 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM 提取概念不准确 | 中 | 中 | confidence 评分 + 人工可编辑 |
| 大量文档 LLM 成本高 | 确定 | 中 | 分批 + 仅 published 文档 + 可配置关闭 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读已有 AI task 模式（detect_contradictions / discover_patterns）
> 2. 设计 prompt 结构

---

### v0.51.11: 知识本体建模 — 可视化页

**任务版本号：** v0.51.11
**优先级：** P2
**前置依赖：** v0.51.9（API 可用）+ v0.51.10（有数据）

---

#### 背景与目标

**目标（Goal）：** 新增本体可视化页面，展示概念层级树和关系图。

---

#### 前端变更

**新增文件：**
- `apps/web/src/app/(dashboard)/projects/[id]/ontology/page.tsx` — 本体可视化页：
  - 左侧：概念树（树形列表，可展开/折叠）
  - 右侧：关系图（节点=概念，边=关系，按类型着色）
  - 顶部："构建本体"按钮 → 调用 `POST .../ontology/build`
  - 关系类型筛选（5 种类型 checkbox）
  - 点击概念 → 显示定义 + 关联文档

**业务规则：**
① 概念树从 `GET .../ontology/tree` 获取
② 关系图从 `GET .../ontology/relations` 获取
③ 关系类型颜色：is_a=蓝色, part_of=绿色, causes=橙色, contradicts=红色, depends_on=紫色
④ "构建本体"按钮仅 editor+ 可见
⑤ 无数据时显示引导页（"点击构建本体开始分析"）

---

#### 验收标准

- [ ] 概念树正确展示层级关系
- [ ] 关系图节点和边正确渲染
- [ ] 5 种关系类型颜色区分明确
- [ ] "构建本体"触发 API 调用
- [ ] 空数据显示引导页
- [ ] 筛选关系类型后图谱更新

---

#### 工作范围

**包含：** ontology/page.tsx 可视化页（~120 行）
**不包含：** 概念编辑功能；本体导出

---

#### 预估工作量

- Phase 1 读图谱页现有实现方式：1 小时
- Phase 2 执行：6 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 图形渲染库选择 | 中 | 中 | 复用图谱页现有库（如 react-flow 或 vis.js） |
| 大量概念/关系渲染性能 | 低 | 中 | 限制展示 Top 100 概念 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读现有图谱页使用的渲染库
> 2. 确认图形渲染库是否支持关系类型着色

---

### v0.51.12: OpenTelemetry 全链路追踪

**任务版本号：** v0.51.12
**优先级：** P2
**前置依赖：** v0.49.8（Prometheus 基础）

---

#### 背景与目标

**目标（Goal）：** 所有 4 个后端服务接入 OpenTelemetry SDK，实现跨服务 trace 关联（API → Celery → AI Orchestrator）。

---

#### 后端变更

**修改文件：**（4 个服务各约 15 行初始化代码）
- `services/api/app/main.py` — OTEL 初始化 + FastAPI middleware
- `services/pipeline-worker/worker/__init__.py` — OTEL 初始化 + Celery 信号
- `services/ai-orchestrator/orchestrator/__init__.py` — OTEL 初始化
- `services/ingestion-worker/worker/__init__.py` — OTEL 初始化

**新增配置：**
- `packages/shared-config/shared_config/settings.py` — 新增：
  - `otel_endpoint: str = ""` — OTEL collector 端点
  - `otel_service_name: str = ""` — 服务名称
  - `otel_enabled: bool = False` — 是否启用

- 依赖文件 — 新增 `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-celery`

**业务规则：**
① `otel_enabled=False` → 完全跳过 OTEL 初始化（行为不变）
② `otel_enabled=True` → 初始化 tracer provider + exporter
③ API 请求自动创建 span
④ Celery task 执行自动创建 child span（关联父 trace）
⑤ LLM 调用创建 span（记录 model / tokens / duration）
⑥ Trace ID 通过 Celery task kwargs 传递（API → Worker）

---

#### 验收标准

- [ ] `OTEL_ENABLED=False` → 无 OTEL 开销（不回归）
- [ ] `OTEL_ENABLED=True` → API 请求产生 trace
- [ ] Pipeline 执行 → API 和 Worker 的 span 在同一 trace 下
- [ ] LLM 调用有独立 span（含 model / tokens）
- [ ] OTEL collector 可接收数据（`curl` 或 Jaeger UI 验证）

---

#### 工作范围

**包含：** 4 个服务 OTEL 初始化 + 配置（~60 行总计）
**不包含：** OTEL collector 部署（运维任务）；Jaeger/Grafana 配置

---

#### 预估工作量

- Phase 1 读 4 个服务入口 + Celery 信号机制：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| OTEL SDK 依赖冲突 | 低 | 中 | Phase 1 确认依赖兼容性 |
| Celery trace 传递复杂 | 中 | 中 | 使用 opentelemetry-instrumentation-celery 自动注入 |
| OTEL 增加请求延迟 | 低 | 低 | 异步导出，可忽略 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 4 个服务入口文件
> 2. 确认 Celery task 的 trace context 传递方式
> 3. 确认 OTEL SDK 版本兼容性

---

## 第六章 ~ 第十七章

### 第六章 实现约束
同 v0.47。

### 第七章 任务领取规则
同 v0.47。

### 第八章 测试要求
| 层次 | 覆盖重点 |
|------|---------|
| 后端单元测试 | StorageClient S3 适配、check_quota/check_feature、SKILL CRUD、ontology 查询 |
| 后端集成测试 | S3/MinIO 切换、Redis Sentinel、配额检查、SKILL pipeline 集成 |
| 前端组件测试 | SKILL 管理页、本体可视化页 |

### 第九章 ~ 第十一章
同 v0.47。版本号：`v0.51.{Z}`，Z = 1-12。

### 第十二章 新增数据库表汇总

| 任务 | 表名 | 变更类型 | 字段 | 类型 | 约束 | 说明 |
|------|------|---------|------|------|------|------|
| v0.51.3 | tenant | 修改 | tier | VARCHAR(20) | NOT NULL, default 'free' | 租户等级 |
| v0.51.3 | tenant | 修改 | feature_flags | JSONB | default {} | 功能开关 |
| v0.51.3 | tenant | 修改 | quota_projects | INTEGER | default 3 | 项目配额 |
| v0.51.3 | tenant | 修改 | quota_docs_per_project | INTEGER | default 1000 | 文档配额 |
| v0.51.3 | tenant | 修改 | quota_storage_gb | INTEGER | default 5 | 存储配额 |
| v0.51.4 | team | **新增表** | id / kb_id / name / parent_team_id / created_at | — | — | 团队模型 |
| v0.51.4 | user | 修改 | department | VARCHAR(100) | nullable | 部门 |
| v0.51.4 | user | 修改 | team_id | UUID | FK→team.id | 所属团队 |
| v0.51.5 | pipeline_stage_config | 修改 | execution_order | INTEGER | default 0 | 执行顺序 |
| v0.51.5 | pipeline_stage_config | 修改 | condition | JSONB | nullable | 条件规则 |
| v0.51.6 | skill | **新增表** | 12 个字段 | — | — | SKILL 模型 |
| v0.51.9 | concept | **新增表** | 6 个字段 | — | — | 概念模型 |
| v0.51.9 | concept_relation | **新增表** | 7 个字段 | — | — | 概念关系 |

合计：4 张新表，3 张表修改，6 次 Alembic migration。

### 第十三章 开始前必须先输出
1. storage.py / Redis 连接 / Tenant / User / pipeline stages 当前代码理解
2. 第一个任务的实施计划
3. 预计修改文件清单

### 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|----------|--------|------|
| v0.51.1 | S3 存储适配 | — | 0 | Planned |
| v0.51.2 | Redis Sentinel | — | 0 | Planned |
| v0.51.3 | 租户分级 | — | 0 | Planned |
| v0.51.4 | 用户组织层级 | — | 0 | Planned |
| v0.51.5 | Stage 条件执行 | — | 0 | Planned |
| v0.51.6 | SKILL 模型+API | — | 0 | Planned |
| v0.51.7 | SKILL Stage 集成 | — | 0 | Planned |
| v0.51.8 | SKILL 管理 UI | — | 0 | Planned |
| v0.51.9 | 本体模型+API | — | 0 | Planned |
| v0.51.10 | 本体 AI 提取 | — | 0 | Planned |
| v0.51.11 | 本体可视化 | — | 0 | Planned |
| v0.51.12 | OpenTelemetry | — | 0 | Planned |

### 第十五章 变更记录
| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-31 | V1.0 初始版本 | Claude Code |
| 2026-03-31 | V2.0 规范重写：水平扩展拆为 S3+Redis 2 任务，SKILL 拆为 模型+集成+UI 3 任务，本体拆为 模型+AI+可视化 3 任务 | Claude Code |
| 2026-04-01 | V2.1 交叉审查修复：v0.51.3 补充存储量计算方式 + 建议前置依赖 v0.51.1；v0.51.4 补充 Team CRUD API 契约（5 端点） | Claude Code |
| 2026-04-01 | V2.2 交叉审查v2修复：H-2 v0.51.1 S3 config 字段已存在于 settings.py，仅需新增 storage_backend | Claude Code |

### 第十六章 决策与假设
**关键决策：**
- 水平扩展拆为 S3 和 Redis 两个独立任务 — 解耦，任一可单独部署
- SKILL 不直接拼接用户输入 — 安全考量，通过 schema 约束
- 知识本体全量重建而非增量 — 简化实现，增量留给未来
- OTEL 默认关闭 — 需额外部署 collector

**假设：**
- boto3 可在容器中安装且 S3 凭证可用
- Redis Sentinel 可配置（3 节点）
- 图谱页已有渲染库可复用

### 第十七章 版本级风险
| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| S3 迁移需数据迁移脚本 | 确定 | 中 | 提供 migrate_minio_to_s3 CLI 工具 |
| 租户配额检查增加延迟 | 低 | 低 | Redis 缓存 TTL 60s |
| SKILL prompt 注入 | 中 | 高 | schema 约束 + 不直接拼接用户输入 |
| 本体提取 LLM 成本高 | 确定 | 中 | 分批 + 可配置关闭 |
| OTEL collector 部署 | 中 | 低 | 提供 Docker Compose 配置 |
