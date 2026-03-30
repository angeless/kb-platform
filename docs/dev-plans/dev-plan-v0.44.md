# KB Platform v0.44 版本开发任务计划

**文档编号**: PLAN-2026-03-28-v044
**版本**: V2.7（新增 v0.44.16 内部 tenant_id → kb_id 重命名）
**日期**: 2026-03-28
**基线 commit**: main HEAD (v0.43.5)
**基线分支**: main
**依据**: 产品北极星（docs/tech-specs/product-north-star.md）+ WISHLIST.md + 代码实际读取核实（2026-03-28）
**作者**: 产品 Owner

> **V2.0 修订说明（相对 V1.0 草稿的重大变更）**
>
> V1.0 在未读代码的情况下起草，存在 5 处严重错误，V2.0 全部修正：
>
> | 错误项 | V1.0 错误假设 | V2.0 实际情况 |
> |-------|------------|------------|
> | W-001 RBAC 数据模型 | 拟新建 `roles`/`user_project_roles` 两张表 | `user.role` 字段已存在，`require_role()` 函数已实现，用户管理 API 已完整 — 仅需前端工作 |
> | W-002 版本历史数据模型 | 拟新建 `document_versions` 表 | `knowledge_doc_version` 表已存在，版本详情/diff API 已实现 — 仅缺列表 API 和回滚 API |
> | W-002 字段名 | `content`、`change_summary`、`version_number`、`architecture_id` | 实际为 `content_md`、`change_reason`、`version`、`node_id` |
> | ArchitectureNode 软删除 | `is_deleted = true` | 该模型无 `is_deleted` 字段，应用 `status` 字段 |
> | ApiKey 表名 | `api_keys`（复数） | 实际表名 `api_key`（单数） |
>
> V1.0 的 14 个任务缩减为 V2.0 的 12 个任务（RBAC 和版本历史各减少 1 个"建表"任务）。

> **V2.1 修订说明（审查合规性修复，7 项问题修复）**
>
> 对照 §2.5 规范逐条审查，修复 H-1×3（缺少 scope boundary）、H-2（GET /versions 权限 editor+ → viewer+）、H-3（JWT/role 获取路径不明确）、M-1（GET batch 返回结构缺失）、M-2（parent_id 假设未标注）。

> **V2.2 修订说明（北极星过滤，W-007 SSE 移出，任务从 12 → 11）**
>
> W-007（SSE 进度推送）北极星三问不通过（属于 UX 优化，不强化核心链路），从 v0.44 移出，原 v0.44.8–v0.44.12 重新编号为 v0.44.8–v0.44.11。

> **V2.3 修订说明（基于 v0.45 代码读取，补充已有能力 + 边界澄清）**
>
> 编写 v0.45 计划时系统读取了 `cross_refs.py`、`audit_service.py`、`audit.py`、`search.py`、`model_providers.py` 等文件，发现以下能力**在 v0.44 计划起草时已存在但未在 Chapter 1.2 中列出**：
>
> | 新增至已有能力清单 | 对 v0.44 的影响 |
> |----------------|---------------|
> | CrossReference CRUD API（`/v1/cross-refs`）完整实现 | v0.44.8/9 边界注释更精确：这两个任务只操作 `ArchitectureNode`，不涉及 `CrossReference` |
> | `AuditService` + `GET /v1/audit-logs` 完整实现 | v0.44 各任务实现时无需自行建审计机制；v0.45.10 统一补全写入集成 |
> | `POST /v1/search/hybrid`（混合检索端点）已实现 | W-003 gap 确认为纯前端，v0.45 范围 |
> | 模型提供商 + 路由规则 CRUD（`/v1/model-providers`）已实现 | W-021 gap 确认为纯前端，v0.45 范围 |

> **V2.7 修订说明（新增 v0.44.16，总任务 15 → 16）**
>
> 产品 Owner 确认：将 KB 内部所有 `tenant_id` 字段重命名为 `kb_id`，覆盖数据库列（Alembic migration）、ORM 模型、所有 service / router / dep、JWT payload 及前端。
> PA 侧（PA 中台、PAPass）字段名不变，KB 向 PA 上报时须将 `kb_id` 映射为 PA 约定字段名（待 PA 提供规范后在 v0.44.14/15 实现时确认）。
> 此任务影响全仓库，属于高风险重构，执行时须逐文件确认，并覆盖 tenant 隔离的回归测试。

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.43.5 现有代码增量增强。禁止重构无关模块、禁止重写已有业务逻辑、禁止变更已有 API 契约（除非本计划明确要求）。

### 1.2 继承已有能力（代码核实后的完整清单）

以下能力经代码读取确认真实存在：

- **`services/api/app/deps.py`** — `require_role(minimum_role)` 工厂函数已实现，角色层级：`viewer(0) < editor(1) < reviewer(2) < project_admin(3) < tenant_admin/admin(4) < platform_admin(5)`
- **`services/api/app/routers/users.py`** — `GET /v1/users`（列表）、`POST /v1/users`（邀请+指定角色）、`PATCH /v1/users/{id}`（修改角色/状态）、`DELETE /v1/users/{id}`（软删除）均已实现，均要求 `tenant_admin` 角色
- **`packages/shared-models/shared_models/user.py`** — `User.role` 字段已存在（String(30)，默认 `viewer`）
- **`packages/shared-models/shared_models/knowledge.py`** — `knowledge_doc_version` 表已存在（`doc_id`, `version`, `content_md`, `change_reason`, `created_by`）；`KnowledgeDoc.current_version` 字段已存在
- **`services/api/app/routers/docs.py`** — `GET /v1/docs/{id}/versions/{version}`（版本详情）和 `GET /v1/docs/{id}/versions/diff`（diff 对比）已实现；`PUT /v1/docs/{id}`（更新内容+新建版本）已实现，需要 `editor` 角色
- **`services/api/app/routers/agent.py`** — `POST /v1/agent/search` 和 `POST /v1/agent/ask` 已实现，API Key 认证
- **`services/api/app/routers/graph.py`** — `GET /v1/projects/{id}/graph` 已实现；图谱节点是 `KnowledgeDoc`，图谱边是 `CrossReference`
- **`services/ingestion-worker/worker/parsers/asr_parser.py`** — 使用本地 `openai-whisper`；支持格式：MP3/WAV/M4A/FLAC/OGG/WEBM（ffmpeg 解码）；已正确抛出 RuntimeError
- **`services/api/app/routers/qa.py`** — QA 接口已实现 SSE 流式响应（`StreamingResponse` with `text/event-stream`），可作为 SSE 实现参考
- **`packages/shared-models/shared_models/api_key.py`** — 表名 `api_key`（单数），字段：`project_id`, `tenant_id`, `name`, `key_hash`, `key_prefix`, `is_active`, `created_by`, `last_used_at`

> **以下条目为 V2.3 新增（基于编写 v0.45 计划时的代码读取）：**

- **`services/api/app/routers/cross_refs.py`** — CrossReference CRUD **完整实现**，v0.44 无需修改后端：
  - `POST /v1/cross-refs`（创建关联，editor+）
  - `GET /v1/cross-refs/doc/{doc_id}`（文档关联列表）
  - `DELETE /v1/cross-refs/{ref_id}`（删除，editor+）
  - `GET /v1/cross-refs/project/{project_id}/graph`（项目关联图数据）
  - `POST /v1/cross-refs/auto-suggest`（AI 建议关联）
  - CrossReference 字段：`source_doc_id`、`target_doc_id`、`relation_type`（枚举：`related/depends_on/extends/contradicts/supersedes`）、`confidence`、`note`、`created_by`
- **`services/api/app/services/audit_service.py`** — `AuditService` 完整实现（`log()` + `list()`），v0.44 实现各任务时**无需重复建审计机制**；`audit_log` 表已存在；写入集成统一在 v0.45.10 补全
- **`services/api/app/routers/audit.py`** — `GET /v1/audit-logs` 已实现（分页 + 过滤，`tenant_admin+`）
- **`services/api/app/routers/search.py`** — 三个搜索端点均已实现（JWT 认证，非 API Key）：
  - `POST /v1/search/text`（全文检索）
  - `POST /v1/search/semantic`（pgvector）
  - `POST /v1/search/hybrid`（混合搜索）— v0.45.1 前端切换目标
- **`services/api/app/routers/model_providers.py`** — 模型提供商 + 路由规则 CRUD 完整实现（`tenant_admin+`）— v0.45.12 前端设置页的 API 来源

### 1.3 最小改动原则

每个任务只改必须改的文件。如果发现无关问题，记录到衍生建议但不执行。

### 1.4 任务领取规则

每次只能领取一个任务。完成后按第十一章格式汇报，确认后再领下一个。

---

## 第二章 当前阶段事实

### 2.1 项目目标

将多模态原始资料自动整理为可追溯、可维护、可被 AI 使用的结构化知识系统。平台本质是带知识拆解和结构化层的数据库，对外提供输入接口（接收多模态内容）和输出接口（Agent 可检索）。

### 2.2 当前基线

- **版本**: v0.43.5（5 个任务已完成）
- **分支**: main

### 2.3 代码核实后的 Gap 分析

> 以下 Gap 基于 2026-03-28 代码实际读取，而非文档描述。

| WISHLIST | 需求 | 后端 Gap | 前端 Gap |
|---------|------|---------|---------|
| W-001 | RBAC 权限体系 | **无**（已完整实现） | **有**：无角色上下文、无权限门控 UI、无用户管理页 |
| W-002 | 版本历史与回滚 | **部分**：缺 `GET /versions`（列表）和 `POST /rollback` | **有**：无版本历史 UI |
| W-004 | 批量导入 ZIP | **有**：无批量导入 API 和批量任务调度 | **有**：无拖拽上传 UI |
| W-005 | ASR 端到端打通 | **待验证**：parser 已有但完整链路未验证 | **有**：无 ASR 专有状态展示 |
| W-007 | SSE 进度推送 | **有**：jobs 路由仍为轮询；无 SSE 端点 | **有**：仍为轮询 |
| W-010 | 图谱节点合并/拆分 | **有**：无 ArchitectureNode 合并/拆分 API | **有**：图谱只读 |
| W-011 | 图谱关系手动编辑 | **无**（CrossReference CRUD + auto-suggest 完整实现，v0.44 不需动后端） | **有**：图谱/文档页仅只读，无关联创建/删除 UI — **延后至 v0.45（v0.45.7/8）** |
| W-015 | API 限流 + 用量统计 | **有**：`api_key` 无限速字段；无限流中间件；无用量记录 | **无** |

---

## 第三章 本轮目标与边界

### 3.1 版本主题

**v0.44：权限体系前端化 + 核心链路强化**

### 3.2 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 |
|----------|--------|------|------|
| v0.44.1 | 前端 RBAC 感知（角色上下文 + 权限门控 UI） | P0 | Done (0dea90c) |
| v0.44.2 | 侧边栏隐藏"用户管理"入口（产品决策：v1 单用户场景，企业版再开放） | P0 | Done (a293bd5) |
| v0.44.3 | 版本历史 API 补全（`GET /versions` 列表 + `POST /rollback`） | P0 | Done (cf085ee) |
| v0.44.4 | 前端版本历史 UI（版本列表 + diff + 回滚） | P0 | Done (2568ac7) |
| v0.44.5 | 批量导入后端（ZIP 解压 + 批量任务调度 + batch API） | P1 | Planned |
| v0.44.6 | 前端批量导入 UI（拖拽上传 + 批次进度列表） | P1 | Planned |
| v0.44.7 | ASR 端到端打通（验证 + 修复 + 前端状态展示） | P1 | Planned |
| v0.44.8 | 图谱 ArchitectureNode 合并/拆分 API | P1 | Planned |
| v0.44.9 | 前端图谱编辑操作（选节点 + 合并/拆分面板） | P1 | Planned |
| v0.44.10 | API Key 限流（Redis token bucket，per key 速率限制） | P1 | Planned |
| v0.44.11 | API 用量统计（`api_usage_log` 表 + 查询端点） | P1 | Planned |
| v0.44.12 | Q&A 对话界面（`POST /v1/qa/ask` 已有后端，补前端） | P1 | Planned |
| v0.44.13 | 首次体验修复（[P0-Critical] 上传触发 ingest job + 仪表板真实统计 + 上传引导 + 表单说明） | P0 | Planned |
| v0.44.14 | 审计日志上报 PA 中台（服务端 + 客户端） | P0 | Blocked（待 PA 接口规范） |
| v0.44.15 | 登录接入 PAPass（OAuth/OIDC 统一账号） | P0 | Blocked（待 PAPass 接入文档） |
| v0.44.16 | KB 内部 `tenant_id` 全面重命名为 `kb_id`（DB migration + ORM + service/router/dep + JWT + 前端） | P1 | Planned |

### 3.3 明确不做的事项

- ~~新建 RBAC 数据模型/中间件~~（已存在）
- ~~新建版本历史数据表~~（已存在 `knowledge_doc_version`）
- 项目级独立角色（user_project_roles 表）— 现有系统是 tenant-wide 角色，不在本版本引入 project-level 分层
- 图谱关系手动编辑（W-011）— CrossReference 后端 CRUD **已完整实现**（不需动后端），仅缺前端 UI；延后至 v0.45（v0.45.7 文档详情页关联面板 + v0.45.8 图谱页关系编辑）
- 多人协作编辑（W-012）— 北极星明确不做
- 多格式导出（W-006）— 延后
- AI 对话式 RAG / 自动摘要（W-008/009）— 延后
- **SSE 流水线进度推送（W-007）— 北极星三问不通过，属于 UX 优化，不在本版本做；保留轮询，放回 WISHLIST 候排**

---

## 第四章 优先级与执行顺序

```
P0 优先：

v0.44.1 → v0.44.2    ← RBAC 前端（v0.44.2 依赖 v0.44.1 的角色上下文）
v0.44.3 → v0.44.4    ← 版本历史（v0.44.4 依赖 v0.44.3 的 API）

P1 独立，可按顺序推进：

v0.44.5 → v0.44.6    ← 批量导入（v0.44.6 依赖 v0.44.5 的 API）
v0.44.7              ← ASR 独立
v0.44.8 → v0.44.9   ← 图谱编辑（v0.44.9 依赖 v0.44.8 的 API）
v0.44.10 → v0.44.11 ← API 限流 + 统计（v0.44.11 可与 v0.44.10 同步进行）
v0.44.12             ← Q&A 对话界面（独立纯前端）
v0.44.13             ← 首次体验修复（独立纯前端，含 P0-Critical 上传触发 bug）

⚠️  Blocked（待 PA 接口文档）：
v0.44.14             ← 审计日志上报 PA 中台
v0.44.15             ← 登录接入 PAPass

P1 独立（可穿插执行，建议在 v0.44.14/15 解除阻塞前完成）：
v0.44.16             ← KB 内部 tenant_id → kb_id 全量重命名（高风险重构，须单独分支）
```

---

## 第五章 各任务详细定义

---

### v0.44.1: 前端 RBAC 感知

**任务版本号：** v0.44.1
**优先级：** P0
**前置依赖：** 无（后端已完整实现）

---

#### 背景与目标

**后端现状（已有）：**
- `User.role` 字段：`viewer` / `editor` / `reviewer` / `project_admin` / `tenant_admin` / `admin` / `platform_admin`
- `require_role()` 依赖函数已在 docs.py 路由中使用
- 登录 API 已返回 JWT，前端可从 token payload 或专用 API 获取 `role`

**目标（Goal）：**
前端根据当前用户角色，隐藏不应该显示的操作按钮，防止 UI 引导用户执行无权限的操作（后端已有权限拦截，前端隐藏是体验层保护）。

**输入（Input）：**
- 当前用户的 `role` 字段，来源为 JWT payload 或 `GET /v1/users/me` 接口

> ⚠️ **Phase 1 强制前置确认（在写任何前端代码之前）：**
> 读 `services/api/app/routers/auth.py` 中的 token 生成逻辑，确认 JWT payload 是否包含 `role` 字段。
>
> **分支 A — JWT payload 已含 `role`（最理想）：**
> 前端从 `jwtDecode(token).role` 获取，无需任何后端修改。直接进入前端开发。
>
> **分支 B — JWT 不含 `role`，但 `GET /v1/users/me` 已返回 `role`：**
> 前端登录后额外调用一次 `/users/me`，将 role 存入 `authStore`。无需后端修改。
>
> **分支 C — JWT 不含 `role`，且 `/users/me` 不存在或不返回 `role`：**
> 作为 v0.44.1 Phase 2 的第 1 步，修改 `auth.py` 将 `role` 写入 JWT payload（最小改动，约 1 行）。此修改范围已包含在本任务内，不新增任务版本号。
>
> **注**：`GET /v1/users/me` 是否存在未在 v0.43 已有能力清单中核实，Phase 1 读代码时同步确认。

---

#### 前端变更

**新增文件：**
- `apps/web/stores/authStore.ts`（若不存在则新建，若存在则扩展）— 在用户信息中存储 `role` 字段
- `apps/web/hooks/usePermission.ts` — `can(action: string): boolean` hook，根据 role 判断是否有权限
- `apps/web/components/PermissionGuard.tsx` — 包裹组件，无权限时不渲染子组件

**权限判断规则（与后端层级对齐）：**

| 操作类型 | 最低角色 | 说明 |
|---------|---------|------|
| 查看知识条目/图谱 | viewer | 所有人可查看 |
| 创建/编辑知识条目 | editor | 编辑者+ |
| 审核知识条目 | reviewer | 审核者+ |
| 批量发布 | project_admin | 项目管理员+ |
| 删除知识条目 | project_admin | 项目管理员+ |
| 管理项目成员 | tenant_admin | 租户管理员 |

**修改范围（最小化）：**
- 知识条目列表页：编辑/删除按钮用 `<PermissionGuard>` 包裹
- 文档详情页：编辑内容/发布/回滚按钮用 `<PermissionGuard>` 包裹
- 审核中心页：审核按钮用 `<PermissionGuard>` 包裹
- 导航菜单：用户管理入口（tenant_admin 可见）

---

#### 验收标准

- [ ] 以 `viewer` 角色登录，知识条目列表中编辑/删除按钮不渲染（DOM 中不存在，不仅仅是 disabled）
- [ ] 以 `editor` 角色登录，可见编辑按钮，不可见删除按钮
- [ ] 以 `tenant_admin` 角色登录，导航栏中出现"用户管理"入口
- [ ] `usePermission('edit')` 在 viewer 下返回 false，在 editor 下返回 true
- [ ] 切换租户或重新登录后，角色上下文正确刷新

---

#### 工作范围

**包含：**
- `apps/web/stores/authStore.ts`（扩展或新建）
- `apps/web/hooks/usePermission.ts`（新建）
- `apps/web/components/PermissionGuard.tsx`（新建）
- 现有页面中的按钮包裹（最小修改）

**不包含（延迟到 v0.44.2）：**
- 用户管理页面本身
- 邀请/修改角色功能

---

#### 预估工作量

- Phase 1 理解与计划：2 小时（必须先确认 JWT/me 接口是否返回 role）
- Phase 2 执行：6 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|-----|------|--------|
| JWT payload 未含 role，需修改 token 生成逻辑 | 中 | 中 | Phase 1 先读 auth.py 确认，若需修改则先做后端微调 |
| 现有页面无统一按钮入口，改动点分散 | 中 | 低 | 逐页检查，优先覆盖高频操作页面 |

---

### v0.44.2: 侧边栏隐藏"用户管理"入口

**任务版本号：** v0.44.2
**优先级：** P0
**前置依赖：** 无（独立改动，单文件）

---

#### 背景与产品决策

> **V2.6 重新定义（产品 Owner 确认，2026-03-28）**
>
> 当前 KB Platform v1 的使用场景是**单用户/单团队自管理**，每个注册账号拥有自己独立的知识库，不需要邀请其他成员共同管理。用户管理（邀请/改角色/移除）是企业级多人协作场景的功能，当前阶段暴露在侧边栏会造成困惑并无实际用途。
>
> **决策：v0.44 中将"用户管理"和"审计日志"从侧边栏完全移除，不做角色判断，直接不展示。页面文件保留，不删除，供未来企业版启用。**

**补充说明：**
- 注册行为设计上会给每个注册者 `tenant_admin` 角色（因为你是自己知识库的主人），这是正确的
- 两个独立注册的账号属于两个不同租户，后端已做严格 `tenant_id` 隔离，互相看不到对方数据
- "用户管理"入口目前对所有人可见是因为侧边栏没有做任何角色过滤，这是侧边栏的问题，不是角色分配的问题

---

#### 修改内容

**`apps/web/src/components/sidebar.tsx`**

当前 `settingsItems` 数组：
```
{ label: "模型配置", href: "/settings/models", icon: "🤖" },
{ label: "用户管理", href: "/settings/users", icon: "👥" },   ← 移除
{ label: "审计日志", href: "/settings/audit", icon: "📋" },   ← 移除
```

修改后：
```
{ label: "模型配置", href: "/settings/models", icon: "🤖" },
```

> 如果"系统管理"分组只剩一项，可考虑去掉分组标题，直接放入主导航，具体由实现时判断。

---

#### 验收标准

- [ ] 登录后侧边栏中不出现"用户管理"和"审计日志"入口
- [ ] 直接访问 `/settings/users` 仍可正常打开（页面保留，不删除）
- [ ] 侧边栏其余项目（项目、模型配置）行为不变

---

#### 工作范围

**包含：**
- `apps/web/src/components/sidebar.tsx`（修改，移除两个 settingsItems 条目）

**明确不包含：**
- 删除 `/settings/users/page.tsx`（保留，未来企业版使用）
- 删除 `/settings/audit/page.tsx`（保留）
- 角色判断逻辑（不做条件判断，直接不展示）
- 任何后端修改

---

### v0.44.3: 版本历史 API 补全

**任务版本号：** v0.44.3
**优先级：** P0
**前置依赖：** 无（独立后端任务）

---

#### 背景与目标

**已有（经代码确认）：**
- 表 `knowledge_doc_version`：字段 `doc_id`、`version`（INTEGER）、`content_md`（TEXT）、`change_reason`（TEXT, nullable）、`created_by`（UUID → users.id）
- `KnowledgeDoc.current_version`：当前版本号（INTEGER）
- `GET /v1/docs/{doc_id}/versions/{version}` — 获取指定版本详情（已有）
- `GET /v1/docs/{doc_id}/versions/diff?from_version=&to_version=` — 版本 diff（已有）
- `PUT /v1/docs/{doc_id}` — 更新内容并创建新版本（已有，要求 editor 角色）

**Gap（需新增）：**
- `GET /v1/docs/{doc_id}/versions` — 版本列表（当前缺失）
- `POST /v1/docs/{doc_id}/versions/{version}/rollback` — 回滚（当前缺失）

---

#### 新增 API 端点

| 端点 | 方法 | 权限 | 说明 |
|-----|------|------|------|
| `/v1/docs/{doc_id}/versions` | GET | `viewer+` | 获取该文档所有版本列表（只读，viewer 可查看） |
| `/v1/docs/{doc_id}/versions/{version}/rollback` | POST | `editor+` | 将文档回滚到指定版本（写操作，要求 editor+） |

> **权限决策说明**：版本列表（GET）是只读信息，viewer 应有权查看文档的修改历史，以了解知识条目的演变过程；回滚（POST）是写操作，改变文档内容，要求 `editor+`，与现有 `PUT /v1/docs/{id}` 更新内容的权限保持一致。

**`GET /v1/docs/{doc_id}/versions` 返回结构：**
```json
{
  "data": {
    "versions": [
      {
        "version": 3,
        "change_reason": "修正错误描述",
        "created_by": "uuid",
        "created_at": "2026-03-28T10:00:00Z"
      }
    ],
    "total": 3,
    "current_version": 3
  }
}
```
注：列表不返回 `content_md`（减小 payload），已有的 `GET .../versions/{version}` 接口返回全文。

**`POST .../rollback` 业务规则：**
1. 校验调用者对该文档所属 project 有 `editor` 或更高角色（用已有 `require_role("editor")`）
2. 查询 `knowledge_doc_version`，找到 `doc_id = {doc_id} AND version = {version}` 的记录；若不存在返回 404 + `VERSION_NOT_FOUND`
3. 调用现有 `DocService.update_content()`（或等效方法），将文档内容更新为 `snapshot.content_md`，`change_reason` 设为 `f"回滚到版本 {version}"`
4. 此更新会触发现有逻辑，自动在 `knowledge_doc_version` 中写一条新版本（`version = current_version + 1`）
5. 返回 200 + 更新后的 `KnowledgeDocDetailOut`

**错误码：**
- `VERSION_NOT_FOUND` — 指定版本不存在（注册到 `packages/shared-errors/`）

---

#### 验收标准

- [ ] `GET /v1/docs/{id}/versions` 返回版本列表，按 `version` 降序，不含 `content_md`
- [ ] 列表中 `total` 与 `knowledge_doc_version` 表中记录数一致
- [ ] 以 `editor` 身份 POST rollback，`knowledge_doc.current_version` 递增，且新版本记录的 `content_md` 与目标版本一致
- [ ] rollback 后 version 继续递增（不回退，而是新增快照）
- [ ] 以 `viewer` 身份 POST rollback，返回 403

---

#### 工作范围

**包含：**
- `services/api/app/routers/docs.py` — 新增两个端点（最小修改）
- `services/api/app/services/doc_service.py` — 新增或扩展版本列表查询和回滚方法
- `packages/shared-schemas/` — 新增 `DocVersionListOut` schema（若不存在）
- `packages/shared-errors/` — 注册 `VERSION_NOT_FOUND` 错误码

**不包含：**
- 修改已有版本相关端点
- 任何数据库表变更（表已存在）

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|-----|------|--------|
| `DocService.update_content()` 不存在或接口不符预期 | 低 | 中 | Phase 1 先读 `doc_service.py` 确认现有方法签名 |
| rollback 后 `current_version` 计数出现竞态（并发写） | 低 | 低 | 用数据库事务 + SELECT FOR UPDATE 保证版本号单调递增 |

---

### v0.44.4: 前端版本历史 UI

**任务版本号：** v0.44.4
**优先级：** P0
**前置依赖：** v0.44.3（列表 API 和 rollback API 已可用）

---

#### 前端变更

**入口：** 知识条目详情页右上角，新增"历史版本"按钮

**已可复用的 API：**
- `GET .../versions` — 版本列表（v0.44.3 新增）
- `GET .../versions/{version}` — 版本详情含全文（已有）
- `GET .../versions/diff?from_version=&to_version=` — diff（已有）
- `POST .../versions/{version}/rollback` — 回滚（v0.44.3 新增）

**新增组件：**
- `apps/web/components/VersionHistory/VersionPanel.tsx` — 右侧抽屉（版本列表）
- `apps/web/components/VersionHistory/VersionDiff.tsx` — diff 展示（利用 `diff?from_version=&to_version=` API 返回数据，纯文本行级高亮）
- `apps/web/components/VersionHistory/RollbackConfirm.tsx` — 回滚确认对话框

**交互流程：**
1. 点击"历史版本" → 右侧抽屉展开，调用 `GET .../versions` 显示版本列表（最新在前）
2. 点击某历史版本 → 调用 diff API 展示 "当前版本 vs 历史版本" 的差异（行级红绿高亮）
3. editor/admin 可见"回滚到此版本"按钮 → 确认对话框 → POST rollback → 成功后抽屉关闭、页面正文刷新、toast 提示 "已回滚到版本 N"
4. viewer 不可见回滚按钮（复用 `<PermissionGuard>`）

---

#### 验收标准

- [ ] 详情页出现"历史版本"按钮，点击展开抽屉
- [ ] 版本列表正确显示 version 号、change_reason、创建时间
- [ ] 点击历史版本后显示 diff 视图，红色为删除行，绿色为新增行
- [ ] editor 可见回滚按钮，viewer 不可见
- [ ] 回滚成功后页面正文内容更新，抽屉关闭，toast 提示正确

---

#### 工作范围

**包含：**
- `apps/web/components/VersionHistory/VersionPanel.tsx`（新建）
- `apps/web/components/VersionHistory/VersionDiff.tsx`（新建）
- `apps/web/components/VersionHistory/RollbackConfirm.tsx`（新建）
- 知识条目详情页：新增"历史版本"按钮入口

**不包含（延后）：**
- diff 内容的行内编辑功能（仅展示，不可在 diff 视图中直接编辑）
- 版本内容导出（独立需求）
- 比较任意两个历史版本（当前仅支持"某历史版本 vs 当前版本"）

---

### v0.44.5: 批量导入后端

**任务版本号：** v0.44.5
**优先级：** P1
**前置依赖：** 无（独立后端任务）

---

#### 需求定义

**目标（Goal）：**
支持上传 ZIP 压缩包，后端自动解压并为每个合法文件创建独立的 `asset` 记录和 Celery ingestion 任务，返回批次 ID。

**新增 API 端点：**

| 端点 | 方法 | 权限 | 说明 |
|-----|------|------|------|
| `/v1/projects/{project_id}/batch-import` | POST | `editor+` | 上传 ZIP，返回 batch_id |
| `/v1/projects/{project_id}/batch-import/{batch_id}` | GET | `viewer+` | 查询批次内各文件状态 |

**`POST .../batch-import` 入参（multipart/form-data）：**
- `file`：ZIP 文件，最大 500MB
- `auto_start`：boolean，默认 true（是否立即触发 ingestion）

**`GET .../batch-import/{batch_id}` 返回结构：**
```json
{
  "data": {
    "batch_id": "uuid",
    "status": "processing",
    "total_files": 5,
    "completed_files": 3,
    "failed_files": 0,
    "created_at": "2026-03-28T10:00:00Z",
    "files": [
      {
        "asset_id": "uuid",
        "original_filename": "docs/chapter1.md",
        "parse_status": "completed"
      },
      {
        "asset_id": "uuid",
        "original_filename": "docs/chapter2.pdf",
        "parse_status": "processing"
      }
    ]
  }
}
```
注：`batch.status` 由 `pending_files > 0 → processing`，`all completed → completed`，`any failed → partial_failed` 动态派生；前端每 3 秒轮询此接口直到 `status` 为终态。

**`POST .../batch-import` 业务规则：**
1. 校验文件扩展名为 `.zip`，大小不超过 500MB；否则返回 400 + `INVALID_FILE_TYPE` / `FILE_TOO_LARGE`
2. 将 ZIP 上传到 MinIO（路径 `projects/{project_id}/batches/{batch_id}/original.zip`）
3. 在内存中解压 ZIP，递归枚举文件（最多 3 层子目录），跳过隐藏文件（`.` 开头）和不支持格式
   - **支持格式**（与 ingestion-worker 已有 parser 对齐）：`.txt`, `.md`, `.pdf`, `.docx`, `.jpg`, `.jpeg`, `.png`, `.mp3`, `.wav`, `.m4a`, `.flac`
4. 为每个合法文件：上传至 MinIO + 创建 `asset` 记录（`parse_status = "pending"`）
5. 将所有 `asset.id` 写入新表 `batch_import`（见下方）
6. 若 `auto_start = true`，为每个 asset 调度 Celery `ingestion.parse_asset` 任务
7. 返回 201 + `{batch_id, total_files, skipped_files}`

---

#### 新增数据库表

> Base 基类已提供 `id`（UUID PK）、`created_at`、`updated_at`，无需重复定义。

**表: `batch_import`（命名遵循项目单数惯例）**

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| project_id | UUID | FK → project.id, NOT NULL | 项目 |
| created_by | UUID | FK → user.id, NOT NULL | 操作者 |
| zip_path | VARCHAR(500) | NOT NULL | MinIO 中 ZIP 路径 |
| total_files | INTEGER | NOT NULL | 解压后合法文件数 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | `pending`/`processing`/`completed`/`partial_failed` |
| completed_at | TIMESTAMPTZ | NULL | 完成时间 |

**表: `batch_import_asset`（关联表，命名遵循单数惯例）**

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| batch_id | UUID | FK → batch_import.id, NOT NULL | 批次 |
| asset_id | UUID | FK → asset.id, NOT NULL | 文件 |
| original_filename | VARCHAR(500) | NOT NULL | ZIP 内原始文件名（含子路径） |
| UNIQUE | (batch_id, asset_id) | — | 防重 |

---

#### 验收标准

- [ ] 上传含 5 个合法文件的 ZIP，返回 201 + batch_id，`batch_import` 表有 1 条记录，`batch_import_asset` 有 5 条记录
- [ ] 上传非 ZIP 文件，返回 400 + `INVALID_FILE_TYPE`
- [ ] 上传空 ZIP（无合法文件），返回 400 + `EMPTY_ARCHIVE`
- [ ] ZIP 内 `.exe` 等不支持格式被跳过，不计入 `total_files`，在 `skipped_files` 中列出
- [ ] `GET .../batch-import/{batch_id}` 返回批次内各文件当前 `parse_status`
- [ ] `auto_start=false` 时，asset 记录创建但不调度 Celery 任务

---

#### 工作范围

**包含：**
- `services/api/app/routers/assets.py` 或新建 `services/api/app/routers/batch_import.py`（新增 2 个端点）
- `services/api/app/services/batch_import_service.py`（新建）
- `packages/shared-models/` — `batch_import.py`（新增两个模型）
- `packages/shared-schemas/` — `batch_import.py`（新增相关 schema）
- `infra/sql/alembic/` — 新增 migration

**不包含（延迟到 v0.44.6）：**
- 前端 UI

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|-----|------|--------|
| 大 ZIP（500MB）内存解压 OOM | 低 | 高 | 使用 `zipfile.ZipFile` streaming 逐文件处理，不一次性解压到内存 |
| Celery 任务并发调度超过 worker 容量 | 低 | 低 | 任务已有 idempotency 保护（tasks.py 中已有），超量时 worker 自行排队 |

---

### v0.44.6: 前端批量导入 UI

**任务版本号：** v0.44.6
**优先级：** P1
**前置依赖：** v0.44.5（后端 API 已可用）

---

#### 前端变更

**入口：** 项目页资产上传区域旁新增"批量导入"按钮

**新增组件：**
- `apps/web/components/BatchImport/BatchDropzone.tsx` — 拖拽区域（仅接受 `.zip`）
- `apps/web/components/BatchImport/BatchProgressList.tsx` — 批次内各文件进度列表

**交互流程：**
1. 拖拽或点击选择 `.zip` 文件 → 显示文件名和大小确认
2. 上传中：进度条（XHR upload progress）
3. 上传完成 → 展示 `BatchProgressList`：每行文件名 + `parse_status` 状态标签，每 3 秒轮询 `GET .../batch-import/{batch_id}`
4. 全部完成后：汇总提示（成功 N 个/失败 M 个）

**前端不做的事（本任务不包含）：**
- 多文件拖拽后前端自动打包为 ZIP — 延后

---

#### 验收标准

- [ ] 拖拽 ZIP → 触发上传 → 进度条可见
- [ ] 上传非 ZIP 文件时，前端显示提示"请上传 .zip 格式文件"，不发 API
- [ ] 上传完成后 `BatchProgressList` 展示各文件状态，状态跟随轮询实时刷新
- [ ] 所有文件完成后显示汇总

---

### v0.44.7: ASR 端到端打通

**任务版本号：** v0.44.7
**优先级：** P1
**前置依赖：** 无（独立任务）

---

#### 背景（代码核实后的真实状态）

**已有：**
- `asr_parser.py` 使用 `openai-whisper`（本地模型，`WHISPER_MODEL` env var 控制，默认 `base`）
- 支持格式：MP3/WAV/M4A/FLAC/OGG/WEBM（通过 ffmpeg 解码）；**MP4 不在原生列表但 ffmpeg 可处理**
- 转录结果作为 `asset_chunk` 写入，`tags.source_type = "audio"`（不是独立 type 字段）
- v0.43.2 已修复静默失败 → 现在会正确抛出 `RuntimeError`

**待验证 / 可能存在 Gap：**
- `openai-whisper` 是否已安装在 ingestion-worker 容器（`requirements.in` 中是否已有）
- `ffmpeg` 是否已安装（系统依赖）
- `parse_asset` Celery 任务是否正确调用 `asr_parser.parse()` 对音频类型 asset
- pipeline-worker 是否能正确消费 `tags.source_type = "audio"` 的 chunks 生成 `knowledge_doc`

---

#### 验证与修复流程

**Phase 1（必须先读代码）：**
- 读 `services/ingestion-worker/requirements.in` 确认 `openai-whisper` 是否已列
- 读 `worker/parsers/__init__.py` 确认 `get_parser()` 是否对 `mp3`/`wav` 正确路由到 `asr_parser`
- 读 `worker/tasks.py` 确认 parse_asset 如何调用 parser 并写 chunks
- 读 pipeline-worker 代码确认对 audio chunks 的处理路径

**Phase 2（按发现修复，逐项记录）：**
- 每发现一个 Bug，记录：现象 → 根因 → 最小修复 → 验证方式
- 禁止宽泛重写；只修复发现的具体问题

---

#### 端到端验证场景

1. 上传 `.mp3` 文件 → `asset.parse_status` 从 `pending` → `processing` → `completed`
2. `asset_chunk` 表中出现 `tags.source_type = "audio"` 的记录，`content_text` 非空
3. pipeline-worker 处理后，`knowledge_doc` 中出现由转写内容生成的知识条目
4. 前端文件列表中，mp3 文件显示正确的解析状态（`processing` → `completed`）

---

#### 验收标准

- [ ] 上传 `.mp3`，Celery 任务完成后 `asset.parse_status = "completed"`
- [ ] `asset_chunk` 中存在 `content_text` 非空、`tags.source_type = "audio"` 的记录
- [ ] `knowledge_doc` 中出现由转写内容生成的条目（不要求内容完美，但必须非空）
- [ ] 上传 `.txt` 或 `.pdf` 文件的现有解析不受影响（回归验证）
- [ ] 所有修复记录在任务报告的 Bug 清单中

---

#### 工作范围

**包含（仅修复发现的 bug）：**
- `services/ingestion-worker/requirements.in`（若 whisper 缺失则补）
- `worker/parsers/__init__.py`（若路由错误则修）
- `worker/tasks.py`（若写 chunk 逻辑有问题则修）
- pipeline-worker 相关文件（若消费 audio chunk 有问题则修）

**不包含：**
- ASR 提供商切换（不做云 API 接入）
- 视频转写（MP4）— 延后，本版本只验证音频

---

### v0.44.8: 图谱 ArchitectureNode 合并/拆分 API

**任务版本号：** v0.44.8
**优先级：** P1
**前置依赖：** 无（独立后端任务）

---

#### 背景（代码核实后）

**图谱结构说明（来自 graph.py 代码读取）：**
- **图谱节点（GraphNode）** = `KnowledgeDoc`（知识条目是图谱的可视节点）
- **图谱边（GraphEdge）** = `CrossReference`（跨文档引用是图谱的边）
- **`ArchitectureNode`** = 知识架构的分类树节点，是 `KnowledgeDoc.node_id` 的外键目标（即文档所属的分类）

**"图谱节点合并/拆分" 的正确含义：**
合并/拆分的是 **`ArchitectureNode`**（架构分类），而不是 `KnowledgeDoc`（知识条目）。合并两个分类后，两个分类下的知识条目统一归入新分类，图谱中这些文档节点的 `node_path` 也随之更新。

**已有字段：**
- `ArchitectureNode.status`（VARCHAR(20)，默认 `draft`）— 软删除用 `status = "archived"`
- `KnowledgeDoc.node_id` — FK → `architecture_node.id`，nullable（无分类时为 null）

---

#### 新增 API 端点

| 端点 | 方法 | 权限 | 说明 |
|-----|------|------|------|
| `/v1/projects/{project_id}/graph/nodes/merge` | POST | `project_admin+` | 合并 2+ 个 ArchitectureNode |
| `/v1/projects/{project_id}/graph/nodes/{node_id}/split` | POST | `project_admin+` | 拆分 1 个 ArchitectureNode |

> **权限选择理由**：合并/拆分会改变知识架构结构，影响范围广，要求 `project_admin` 以上（而不是 editor），与现有 `batch_publish` 的权限级别对齐。

**`POST .../merge` 入参：**
```json
{
  "source_node_ids": ["uuid1", "uuid2"],
  "target_name": "合并后的分类名称",
  "target_description": "合并后的分类描述（可选）",
  "target_node_type": "topic"
}
```

**合并业务规则：**
1. 校验所有 `source_node_ids`（至少 2 个）均属于当前 project，否则 404 + `NODE_NOT_FOUND`
2. 在同一个数据库事务中：
   a. 创建新 `ArchitectureNode`（`architecture_id` 继承自 source 节点，`parent_id` 若 source 节点的 parent_id 一致则继承，否则为 null）
      > ⚠️ **假设**：若两个源节点的 `parent_id` 不同，新节点提升为顶层节点（`parent_id = null`）。若需用户自选目标父级，需将 `POST merge` 入参扩展加入 `target_parent_id` 字段，作为后续版本优化。
   b. 将所有 `KnowledgeDoc.node_id IN source_node_ids` 更新为新节点 id
   c. 将 source 节点的 `status` 更新为 `"archived"`
3. 返回 201 + 新 `ArchitectureNode` 对象

**`POST .../split` 入参：**
```json
{
  "node_id": "uuid",
  "part_a": {
    "name": "子分类 A",
    "node_type": "topic",
    "doc_ids": ["uuid_doc1", "uuid_doc2"]
  },
  "part_b": {
    "name": "子分类 B",
    "node_type": "topic",
    "doc_ids": ["uuid_doc3", "uuid_doc4"]
  }
}
```

**拆分业务规则：**
1. 校验 `node_id` 属于当前 project
2. 校验 `part_a.doc_ids` 与 `part_b.doc_ids` 无交集，且并集恰好等于该节点下所有 `KnowledgeDoc.id`；否则返回 400 + `DOC_LIST_INCOMPLETE` 或 `DOC_LIST_OVERLAP`
3. 在同一事务中：
   a. 创建 `ArchitectureNode` A 和 B（`parent_id` 继承原节点的 `parent_id`）
   b. 按 `doc_ids` 分别更新 `KnowledgeDoc.node_id`
   c. 原节点 `status = "archived"`
4. 返回 201 + [节点 A, 节点 B]

**错误码（新增）：**
- `NODE_NOT_FOUND` — 节点不存在或不属于当前项目
- `INSUFFICIENT_SOURCES` — 合并至少需要 2 个节点
- `DOC_LIST_INCOMPLETE` — 拆分时 doc_ids 未覆盖节点下全部文档
- `DOC_LIST_OVERLAP` — 拆分时 part_a 与 part_b 的 doc_ids 有重叠

---

#### 验收标准

- [ ] 合并 2 个节点：新节点存在，原节点 `status = "archived"`，相关 `KnowledgeDoc.node_id` 更新为新节点 id
- [ ] `GET /graph` 返回数据中：原节点消失，新节点出现，相关文档 `node_path` 更新
- [ ] 拆分节点：2 个新节点存在，原节点 `status = "archived"`，docs 按指定划分分配
- [ ] doc_ids 不完整时返回 400 + `DOC_LIST_INCOMPLETE`
- [ ] 以 `editor` 身份调用合并/拆分，返回 403
- [ ] 所有操作在事务中执行，任意步骤失败则全部回滚

---

#### 工作范围

**包含：**
- `services/api/app/routers/graph.py` — 新增 2 个端点
- `services/api/app/services/graph_service.py`（新建或扩展）
- `packages/shared-schemas/` — 新增合并/拆分相关 schema
- `packages/shared-errors/` — 注册新错误码

**不包含：**
- 任何数据库 migration（无新表）
- `CrossReference` 的处理（合并/拆分后跨文档引用保持原样，不强制更新）

> ⚠️ **边界说明（V2.3 新增）**：`CrossReference` CRUD API（`/v1/cross-refs`）**已完整实现**，v0.44.8 不涉及 CrossReference 的任何修改。v0.44.8 操作的对象是 `ArchitectureNode`（架构分类节点），与跨文档关联层完全独立。

---

### v0.44.9: 前端图谱编辑操作

**任务版本号：** v0.44.9
**优先级：** P1
**前置依赖：** v0.44.8（API 可用）

---

#### 前端变更

**基础：** v0.43.4 已有图谱可视化页面（只读），本任务在此基础上添加编辑操作。

> **Phase 1 必须先读** `apps/web/app/projects/[id]/graph/page.tsx`（或等效路径），确认现有图谱组件库（是 D3/Cytoscape/ReactFlow？）和节点的交互方式，再设计合并/拆分 UI。

**新增交互（根据现有图谱组件库调整具体实现）：**

**合并流程：**
1. 按住 Shift 多选 ArchitectureNode 类型的分类节点
2. 右键菜单 → "合并选中分类" → Modal（填写新分类名称、描述）
3. 确认 → POST merge → 图谱刷新

**拆分流程：**
1. 右键单个 ArchitectureNode → "拆分分类"
2. 侧栏 Panel：展示该分类下所有文档列表（调用 `GET /v1/docs?project_id=&node_id=`），拖拽或勾选分配到 A/B 组
3. 填写 A/B 分类名称 → 确认 → POST split → 图谱刷新

**权限：** `project_admin+` 可见操作菜单；editor/viewer 无此菜单

**新增组件：**
- `apps/web/components/Graph/NodeMergeModal.tsx`
- `apps/web/components/Graph/NodeSplitPanel.tsx`

---

#### 验收标准

- [ ] `project_admin` 进入图谱页，分类节点出现右键菜单
- [ ] `editor` 进入图谱页，无右键菜单
- [ ] 多选 2 个分类节点后合并，图谱刷新，原节点消失，新节点出现
- [ ] 拆分操作，Panel 展示文档列表，可分配到 A/B，确认后图谱刷新
- [ ] 操作成功后 toast 提示

---

#### 工作范围

**包含：**
- `apps/web/app/projects/[id]/graph/page.tsx`（或等效路径）— 新增多选、右键菜单交互
- `apps/web/components/Graph/NodeMergeModal.tsx`（新建）
- `apps/web/components/Graph/NodeSplitPanel.tsx`（新建）

**不包含（延后）：**
- 图谱边（CrossReference）的手动编辑与审核（W-011）— CrossReference 后端 CRUD 已完整实现，仅缺前端 UI，**已在 v0.45 规划（v0.45.7 文档详情页关联面板 + v0.45.8 图谱页关系编辑）**。v0.44.9 不实现 CrossReference 相关的任何前端逻辑。
- ArchitectureNode 重命名/描述修改（非本任务，可通过已有后端接口处理，不在此次 UI 中引入）
- 合并/拆分的撤销（Undo）功能

---

### v0.44.10: API Key 限流

**任务版本号：** v0.44.10
**优先级：** P1
**前置依赖：** 无（独立任务；依赖 v0.43.3 已有的 `get_api_key_project` 依赖函数）

---

#### 需求定义

**目标（Goal）：**
为 `/v1/agent/*` 的每个 API Key 实施速率限制，防止滥用。

**已有（代码确认）：**
- `api_key` 表（单数）：`project_id`, `tenant_id`, `name`, `key_hash`, `key_prefix`, `is_active`, `created_by`, `last_used_at`
- `get_api_key_project` 依赖函数：已验证 API Key 并返回 `(api_key, project_id, tenant_id)`

---

#### `api_key` 表新增字段（Alembic migration）

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| rate_limit_per_minute | INTEGER | NOT NULL, DEFAULT 60 | 每分钟最大请求数；0 表示不限速 |

---

#### 限流实现

> ⚠️ **V2.4 修正（冲突修复）**
>
> 原计划拟新建 `middleware/rate_limiter.py`，但 `services/api/app/middleware/rate_limit.py` 已存在完整生产级限流中间件（Redis 滑动窗口 + 本地内存 fallback，已全局注册于 `main.py`）。
> 若再新建同名文件将造成命名冲突和逻辑重复。
>
> **修正方案：不新建独立文件，在 `agent.py` 两个端点的依赖链中内联 per-key Redis INCR（约 15 行），与全局 `rate_limit.py` 完全并列、互不影响。**

**算法：** 固定窗口计数（用 Redis INCR + TTL 模拟）

**Redis Key 格式：** `rl:api:{api_key_id}:{unix_timestamp_minute}`
（每个整分钟一个 Key，TTL = 120 秒，避免时钟偏差导致 Key 过早过期）

**业务规则：**
1. 请求到达 `/v1/agent/*`，提取 `api_key.id` 和 `rate_limit_per_minute`
2. 若 `rate_limit_per_minute == 0`，跳过限流
3. 否则：`count = INCR rl:api:{api_key_id}:{minute}`；首次 INCR 时设置 TTL = 120s
4. 若 `count > rate_limit_per_minute`：返回 429 + header `Retry-After: {60 - current_second}` + 错误码 `SYSTEM_RATE_LIMITED`（复用 `shared_errors.codes.SYSTEM_RATE_LIMITED`，不新增枚举值）
5. 否则：放行

**接入方式：** 在 `services/api/app/routers/agent.py` 的两个端点依赖链中内联限流逻辑（而不是全局 middleware，避免影响其他路由）

---

#### 验收标准

- [ ] `api_key` 表新增 `rate_limit_per_minute` 字段，migration 可正向执行
- [ ] 同一 API Key 连续发送 61 次 `POST /v1/agent/search`，第 61 次返回 429 + `Retry-After` header
- [ ] 不同 API Key 的限流计数独立互不影响
- [ ] `rate_limit_per_minute = 0` 的 Key 无限速
- [ ] 等待到下一分钟，限流重置，可正常请求
- [ ] `POST /v1/agent/ask` 同样被限流
- [ ] JWT 认证的普通 API（`/v1/docs`、`/v1/projects` 等）不受限流影响

---

#### 工作范围

**包含：**
- `infra/sql/alembic/` — migration（`api_key` 表新增字段）
- `packages/shared-models/shared_models/api_key.py` — 新增 `rate_limit_per_minute` 字段
- `services/api/app/routers/agent.py` — 内联 per-key 限流逻辑（约 15 行，复用 Redis client）

**不新增：**
- `services/api/app/middleware/rate_limiter.py`（❌ 与已有 `rate_limit.py` 冲突，禁止新建）
- `packages/shared-errors/` 中的 `RATE_LIMIT_EXCEEDED`（❌ 复用已有 `SYSTEM_RATE_LIMITED`，不新增枚举值）

**不包含：**
- 管理员修改 API Key 限流值的 UI（已有 `PATCH /v1/api-keys/{id}` 可覆盖，若不存在则作为衍生建议）

---

### v0.44.11: API 用量统计

**任务版本号：** v0.44.11
**优先级：** P1
**前置依赖：** v0.44.10（限流中间件已建立，可在同位置追加统计逻辑）

---

#### 需求定义

**目标（Goal）：**
记录每个 API Key 的调用日志，并提供汇总查询接口，使 API Key 持有者（通过 Key 本身）可查看用量。

---

#### 新增数据库表

**表: `api_usage_log`（单数，与项目惯例一致）**

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| api_key_id | UUID | FK → api_key.id, NOT NULL | API Key |
| endpoint | VARCHAR(200) | NOT NULL | 调用路径（如 `/v1/agent/search`） |
| method | VARCHAR(10) | NOT NULL | HTTP 方法 |
| status_code | INTEGER | NOT NULL | 响应状态码 |
| latency_ms | INTEGER | NOT NULL | 响应延迟（毫秒） |
| requested_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 请求时间 |
| INDEX | (api_key_id, requested_at DESC) | — | 查询加速 |

> Base 类提供 `id`, `created_at`, `updated_at`，本表的时序查询依赖 `requested_at` 而非 `created_at`，故显式定义。

**写入时机：** 每次 `/v1/agent/*` 请求完成后（含 429 限流），用 FastAPI `BackgroundTask` 异步写入，不阻塞响应。

---

#### 新增 API 端点

| 端点 | 方法 | 权限 | 说明 |
|-----|------|------|------|
| `/v1/agent/usage` | GET | API Key 认证 | 查询该 Key 的用量汇总 |

**查询参数：**
- `start_date`（YYYY-MM-DD，默认 7 天前）
- `end_date`（YYYY-MM-DD，默认今天）
- `group_by`：`day` / `endpoint`（默认 `day`）

**返回结构（group_by=day）：**
```json
{
  "data": {
    "api_key_id": "uuid",
    "period": {"start": "2026-03-21", "end": "2026-03-28"},
    "total_requests": 1234,
    "total_errors": 12,
    "daily": [
      {"date": "2026-03-28", "requests": 200, "errors": 2, "avg_latency_ms": 120}
    ]
  }
}
```

---

#### 验收标准

- [ ] `api_usage_log` 表存在，migration 可执行
- [ ] 调用 `POST /v1/agent/search`，`api_usage_log` 中出现对应记录（endpoint、status_code、latency_ms 正确）
- [ ] 限流触发（429）的请求也被记录（status_code = 429）
- [ ] `GET /v1/agent/usage` 返回过去 7 天汇总，数字与 `api_usage_log` 一致
- [ ] 用量写入通过 `BackgroundTask`，主响应延迟增量不超过 5ms（压测验证）

---

#### 工作范围

**包含：**
- `infra/sql/alembic/` — migration
- `packages/shared-models/` — `api_usage_log.py`
- `services/api/app/routers/agent.py` — 追加 `BackgroundTask` 写入逻辑 + `GET /v1/agent/usage` 端点
- `packages/shared-schemas/` — usage 相关 schema

**不包含：**
- 管理员查看所有 API Key 用量的汇总视图（衍生建议）
- 用量告警 / 用量上限自动封禁（衍生建议）

---

### v0.44.12: Q&A 对话界面

**任务版本号：** v0.44.12
**优先级：** P1
**前置依赖：** 无（后端 `POST /v1/qa/ask` 已完整实现，含 SSE streaming + 非流式模式）

---

#### 需求定义

**目标（Goal）：**
为已有的 Q&A 后端接口提供前端对话页面，让用户可以在项目内用自然语言向知识库提问，并看到流式回答。

**已有（代码确认）：**
- `POST /v1/qa/ask`：JWT 认证，支持 `stream=true`（SSE `StreamingResponse`）和 `stream=false`（普通 JSON）
- `QAService.ask_stream()`：已实现，RAG 检索 + LLM 生成
- 无任何前端 Q&A 页面

---

#### 新增页面

**新增页面：** `apps/web/src/app/(dashboard)/projects/[id]/qa/page.tsx`

**页面功能：**
1. 消息列表区：用户问题（右侧气泡）+ AI 回答（左侧气泡，SSE 流式渲染）
2. 输入框 + 发送按钮（支持 Enter 发送）
3. 发送时调用 `POST /v1/qa/ask`（`stream=true`），逐 token 更新 AI 气泡内容
4. 回答完成后在气泡底部展示引用来源（`sources[]` 字段）
5. 对话历史保存在组件 state（刷新即清空，不持久化）
6. 空状态文案：「向本项目的知识库提问，AI 将基于已有文档回答」

**项目首页新增入口：**
- 在 `projects/[id]/page.tsx` 的 9 个 tile 中添加"问答"tile（第 10 个，或替换"—"最多的 tile 之一）
- Sidebar 当前无项目级子导航，不改动 sidebar（侧边栏改动属于 v0.44.1 范围）

---

#### 验收标准

- [ ] 进入 `/projects/{id}/qa`，看到空对话界面和引导文案
- [ ] 输入问题发送，AI 回答以流式方式逐字出现（不是一次性加载）
- [ ] 流式过程中发送按钮变为"等待中"禁用状态
- [ ] 回答结束后展示 sources（若有）
- [ ] 网络错误时在 AI 气泡处显示错误提示，不崩溃

---

#### 工作范围

**包含：**
- `apps/web/src/app/(dashboard)/projects/[id]/qa/page.tsx`（新建）
- `apps/web/src/app/(dashboard)/projects/[id]/page.tsx`（修改，新增问答入口 tile）

**不包含：**
- 对话历史持久化（后端无接口，留 v0.46）
- 多轮对话上下文传递（v0.46）
- 模型选择 UI

---

### v0.44.13: 首次体验修复

**任务版本号：** v0.44.13
**优先级：** P0（影响新用户首次印象，是系统"能不能用"的感知问题）
**前置依赖：** 无（纯前端改动）

---

#### 需求定义

**目标（Goal）：**
修复新用户首次使用时遇到的三个具体迷惑点：项目首页仪表板全是"—"、不知道资料在哪里上传、新建项目表单不知道填什么。

**问题列表（代码核实）：**

| 问题 | 根因 | 修复方案 |
|-----|------|---------|
| **[P0-Critical] 上传文件后永远卡在"等待中"，无法处理** | `FileUpload` 组件上传成功后未调用任何 Job 创建接口；asset 记录 `parse_status="pending"` 后无人触发；Celery ingestion-worker 需收到 `ingest` Job 才会工作 | 上传成功后立即调用 `POST /v1/jobs`（`job_type="ingest"`, `asset_id`），自动触发解析；资料列表页为已解析完成的 asset 增加"运行流水线"按钮（`job_type="pipeline"`） |
| 项目首页 9 个 tile，8 个显示"—" | `projects/[id]/page.tsx` 只请求了 assets，其余 tile 无数据 | 并发请求 docs / architectures / jobs count，展示实际数字 |
| 不知道去哪里上传资料 | 无明显 CTA；"资料"tile 看起来和其他 tile 一样，且显示"—" | assets=0 时在项目首页展示醒目"上传第一份资料"卡片 |
| 新建项目"行业（可选）"不知所云 | placeholder 文字太短，没有说明用途 | 加说明文字：「帮助 AI 更准确地理解文档内容，例如：医疗、金融、教育、法律」 |
| OnboardingGuide 消失后再也看不到 | 基于 localStorage，关掉即永久不见 | 改为：无项目时始终显示（移除 localStorage 逻辑）；有项目后自动不显示 |

---

#### 修改清单

**1. `apps/web/src/components/file-upload.tsx`** ← **最优先**
- 上传成功后（`status: "done"`）立即调用 `POST /v1/jobs`：`{ project_id, job_type: "ingest", asset_id: <新asset的id> }`
- 上传接口返回值 `AssetOut` 含 `id`，可直接使用
- 成功触发后在文件项目旁显示"解析中..."提示

**2. `apps/web/src/app/(dashboard)/projects/[id]/assets/page.tsx`**
- 资产列表新增操作列：`parse_status="done"` 的 asset 显示"▶ 运行流水线"按钮 → `POST /v1/jobs`（`job_type="pipeline"`, `asset_id`）
- 解析中（`parse_status="processing"`）显示 spinner
- 等待中（`parse_status="pending"`）显示"⏳ 等待解析"（说明原因，不让用户困惑）

**3. `apps/web/src/app/(dashboard)/projects/[id]/page.tsx`**
- 并发请求 `GET /v1/docs?project_id={id}&page=1&page_size=1` → `meta.total` = 文档数
- 并发请求 `GET /v1/projects/{id}/architectures` → `.length` = 架构数
- 并发请求 `GET /v1/jobs?project_id={id}&page=1&page_size=1` → `meta.total` = 任务数
- assets=0 时，"最近资料"区域改为醒目的空状态卡，含"立即上传"大按钮（跳转 `/projects/{id}/assets`）

**4. `apps/web/src/app/(dashboard)/projects/page.tsx`**
- 新建项目表单"行业（可选）"input 下方添加说明文字：`帮助 AI 更准确地理解文档内容，例如：医疗、金融、教育、法律`
- placeholder 改为"例如：医疗、金融、教育"

**5. `apps/web/src/components/onboarding-guide.tsx`**
- 移除 localStorage 相关逻辑（`STORAGE_KEY` / `useEffect` / `handleDismiss`）
- 改为：`props.hasProjects === false` 时显示，否则不显示
- `ProjectsPage` 传入 `hasProjects={projects.length > 0}`

---

#### 验收标准

- [ ] **[Critical]** 上传一个 PDF 文件，上传完成后资产列表该文件旁出现"解析中..."，"任务"tile 数字变为 1
- [ ] **[Critical]** 进入资产列表，`parse_status="done"` 的文件显示"▶ 运行流水线"按钮，点击后任务数增加
- [ ] 进入任意已有内容的项目，首页 tile 均显示数字，无"—"
- [ ] 进入空项目（无资料），"最近资料"区域显示"立即上传"大按钮
- [ ] 新建项目表单"行业"字段有说明文字，placeholder 有示例
- [ ] 首次访问（无项目时）OnboardingGuide 正常展示
- [ ] 创建第一个项目后，OnboardingGuide 自动不再显示

---

#### 工作范围

**包含：**
- `apps/web/src/components/file-upload.tsx`（修改，上传后自动触发 ingest job）
- `apps/web/src/app/(dashboard)/projects/[id]/assets/page.tsx`（修改，新增流水线触发按钮）
- `apps/web/src/app/(dashboard)/projects/[id]/page.tsx`（修改，加载真实统计数据）
- `apps/web/src/app/(dashboard)/projects/page.tsx`（修改，表单说明文字）
- `apps/web/src/components/onboarding-guide.tsx`（修改，移除 localStorage 逻辑）

**不包含：**
- sidebar 的角色隔离（属于 v0.44.1 范围）
- 设置页重复路由清理（标注为已知问题，记为衍生建议）
- 后端流水线本身的任何改动（纯前端触发补全）

---

### v0.44.14: 审计日志上报 PA 中台

**任务版本号：** v0.44.14
**优先级：** P0
**前置依赖：** ⚠️ **硬性阻塞：PA 中台需提供日志收集接口规范（URL / 鉴权方式 / 字段格式）后方可开发**

---

#### 需求定义

**目标（Goal）：**
将 KB Platform 的服务端操作审计日志和客户端行为日志上报给 PA 中台，便于统一 debug 和用户行为分析。

**范围：**
- **服务端日志**：`AuditService.log()` 写完本地 `audit_log` 表后，异步推送给 PA 中台日志收集接口
- **客户端日志**：浏览器端关键用户行为（页面切换、上传、Q&A 发问）+ 未捕获的前端错误，推送给 PA 中台前端日志接口

**现状（代码确认）：**
- `AuditService.log()` 目前仅做 `INSERT INTO audit_log`，无任何外部推送
- 前端无任何日志上报逻辑
- PA 中台日志 API 规范：**未知，待 PA 团队提供**

---

#### 待确认事项（开发前必须明确）

| 问题 | 说明 |
|-----|------|
| PA 日志收集 URL | 服务端和客户端是同一个接口还是两个？ |
| 鉴权方式 | API Key？JWT？mTLS？ |
| 推送字段格式 | 哪些字段是必填的？字段命名规范？ |
| 推送失败策略 | 失败是否重试？是否允许丢弃（fire-and-forget）？ |
| 客户端日志级别 | 只要 error，还是也要 info/warn？ |

---

#### 实现方向（规范确认后细化）

**服务端：**
- `AuditService.log()` 写入本地 DB 后，启动 `asyncio.create_task()` 异步 HTTP POST 给 PA 接口
- 推送失败不影响主流程（fire-and-forget），但记录本地 warning 日志
- 新增 `PA_LOG_ENDPOINT` / `PA_LOG_API_KEY` 环境变量（`shared-config` 中注册）

**客户端：**
- 新建 `apps/web/src/lib/pa-logger.ts`：封装 PA 日志上报函数
- 在 `apps/web/src/app/layout.tsx` 注册全局 `window.onerror` + `unhandledrejection` 监听
- 关键操作节点（上传完成、Q&A 发问、登录）调用 `paLogger.track(event, payload)`

---

#### 验收标准

- [ ] 上传一个文件，PA 中台日志控制台可查到对应的 `upload` 事件记录
- [ ] 前端触发一个 JS 错误，PA 中台可查到错误上报
- [ ] PA 中台接口不可达时，KB 服务端和前端均不崩溃，本地流程正常继续
- [ ] 不上报任何用户密码、JWT token、API Key 等敏感字段

---

#### 工作范围

**包含：**
- `packages/shared-config/` — 新增 `PA_LOG_ENDPOINT`、`PA_LOG_API_KEY` 配置项
- `services/api/app/services/audit_service.py` — 修改，log() 后追加异步推送
- `apps/web/src/lib/pa-logger.ts`（新建）
- `apps/web/src/app/layout.tsx` — 修改，注册全局错误监听

**不包含：**
- 修改 `audit_log` 本地表结构
- 日志持久化队列 / 重试机制（先做 fire-and-forget，复杂版本留衍生）

---

### v0.44.15: 登录接入 Pass（PA 中台统一账号）

**任务版本号：** v0.44.15
**优先级：** P0
**前置依赖：** ✅ Pass 接入文档已提供（V1.0，2026-03-23）；所有技术问题已澄清（Q1-Q6）
**运维前置（非代码阻塞）：** 需 PA 管理员创建 KB 产品并提供 `productId`；需运维确认生产环境 Pass API 域名

---

#### 需求定义

**目标（Goal）：**
将 KB Platform 的登录认证从自建 email+bcrypt+KB-JWT 体系切换为 Pass（PA 中台统一账号），使用 Pass JWT 作为唯一认证凭据。用户在 KB 登录/注册时，KB 后端代理调用 Pass API，Pass 签发 JWT，KB 存入 httpOnly cookie 并基于 Pass JWT 验证所有后续请求。

**核心机制：**
- 认证信任根在 Pass 服务端，KB 不再自签 JWT
- KB 通过 `GET /pass/me`（Bearer Pass-JWT）验证 token 有效性并获取用户身份
- KB 本地 User 表通过 `pass_id` 字段关联 Pass 账号，存储 KB 内部的 `tenant_id` 和 `role`
- KB 与 Pass 之间只传 `passId`（UUID）和 `productId`，不传 KB 内部的 `tenant_id`

**现状（代码确认 2026-03-28）：**
- KB 当前认证：完全自建（`auth_service.py` → bcrypt 校验 → `create_access_token()` 本地签发 JWT）
- JWT payload：`{ sub: user_id, tenant_id, role, exp, iat }`
- `get_current_user()`：从 cookie/header 取 JWT → `decode_access_token()` 本地验签 → `SELECT User WHERE id = sub`
- 前端：email+password 表单 → `POST /v1/auth/login` → httpOnly cookie → `GET /v1/auth/me`
- `RefreshToken` 表存储 refresh token hash，支持吊销

---

#### Pass 接入文档摘要（PA 中台提供）

| API | 方法 | 用途 |
|-----|------|------|
| `/api/v1/pass/register` | POST | 注册 Pass 账号（需 productId, email/phone, password, displayName） |
| `/api/v1/pass/login` | POST | 登录（需 productId, email/phone, password）→ 返回 `{ passId, token, expiresAt, productBindings }` |
| `/api/v1/pass/refresh` | POST | 刷新 token（Bearer 旧 token）→ 返回 `{ token, expiresAt }` |
| `/api/v1/pass/me` | GET | 验证 token + 获取账号信息（Bearer token）→ 返回 `{ passId, email, phone, displayName, avatarUrl, productBindings }` |

**Pass JWT 格式：** `audience: "pass"`, `sub: "pass:{passAccountId}"`
**Token 有效期：** 默认 3600 秒（1 小时），由 PA 侧 `AUTH_TOKEN_TTL_SECONDS` 控制
**Pass API 限流：** 当前无限流（PA 侧待办项），KB 中期应加 Redis 缓存
**密码策略：** Pass 要求 8-128 位无复杂度限制，KB 的强校验（大小写+数字+特殊字符）完全兼容
**错误码：** PA-7001（不存在）、PA-7003（已注册）、PA-7004（已封禁）

---

#### 架构设计

**登录流程：**

```
用户输入 email + password
    ↓
KB 前端 POST /v1/auth/login { email, password }（不变）
    ↓
KB 后端 auth_service.py:
    1. 调用 Pass API: POST {PASS_BASE_URL}/api/v1/pass/login
       body: { productId: KB_PRODUCT_ID, email, password }
    2. Pass 返回 { passId, token, expiresAt, productBindings }
       ├─ 401 → 凭证无效 → 抛 UnauthorizedException
       ├─ PA-7004 (403) → 账号封禁 → 抛 ForbiddenException("账号已被封禁，请联系管理员")
       └─ 200 → 继续
    3. 查本地 User: SELECT * FROM user WHERE pass_id = :passId
       ├─ 存在 → 使用该 User
       └─ 不存在 → 首次登录，自动创建：
          a) 创建 Tenant(name=email, status="active")
          b) 创建 User(pass_id=passId, email=email, role="tenant_admin", tenant_id=tenant.id)
          c) 不设 password_hash（密码由 Pass 管理）
    4. 将 Pass JWT（token）存入 httpOnly cookie "access_token"
    5. 将 expiresAt 存入 httpOnly cookie（或由 cookie max_age 控制）
    6. 返回前端（前端无感知差异）
```

**请求验证流程（每个 API 请求）：**

```
get_current_user():
    1. 从 cookie/header 取出 Pass JWT
    2. 调用 Pass API: GET {PASS_BASE_URL}/api/v1/pass/me
       Header: Authorization: Bearer <pass_jwt>
       ├─ 401 → token 无效/过期 → 抛 UnauthorizedException
       └─ 200 → 返回 { passId, email, ... }
    3. SELECT * FROM user WHERE pass_id = :passId
       → 拿到 tenant_id、role（KB 内部概念）
    4. 返回 User 对象
    （中期优化：Redis 缓存 pass_jwt_hash → User 映射，TTL 5 分钟）
```

**Token 刷新流程：**

```
KB /v1/auth/refresh:
    1. 从 cookie 取出当前 Pass JWT
    2. 调用 Pass API: POST {PASS_BASE_URL}/api/v1/pass/refresh
       Header: Authorization: Bearer <pass_jwt>
    3. Pass 返回新 { token, expiresAt }
    4. 更新 httpOnly cookie
    5. 返回前端
    （KB 本地 RefreshToken 表不再使用，可保留但不写入新记录）
```

**注册流程：**

```
KB /v1/auth/register:
    1. 调用 Pass API: POST {PASS_BASE_URL}/api/v1/pass/register
       body: { productId: KB_PRODUCT_ID, email, password, displayName }
    2. Pass 返回 { passId, token, expiresAt, productBinding }
       ├─ PA-7003 (409) → 已注册 → 抛 ConflictException
       └─ 201 → 继续
    3. 创建 KB Tenant + User（pass_id=passId, role=tenant_admin）
    4. 将 Pass JWT 存入 httpOnly cookie（注册即登录）
    5. 返回前端
```

---

#### 架构影响评估

| 模块 | 影响 | 改动量 |
|-----|------|-------|
| `services/api/app/services/auth_service.py` | 核心改动：`login()` / `register()` / `refresh()` 改为代理 Pass API；新增 `PassClient` HTTP 客户端；移除本地 bcrypt 校验和 JWT 签发 | 大 |
| `services/api/app/deps.py` | `get_current_user()` 改为：调用 Pass `/me` 验证 → 按 `pass_id` 查 User（替代本地 JWT decode） | 中 |
| `services/api/app/routers/auth.py` | 适配新 auth_service 接口；`register` 改为注册即登录（设 cookie）；移除 `forgot-password` / `reset-password`（由 Pass 管理密码） | 中 |
| `packages/shared-models/shared_models/user.py` | 新增 `pass_id: Mapped[str | None]`（VARCHAR(255), nullable, 索引）；`password_hash` 改为 nullable | 小 |
| `infra/sql/alembic/` | 新增 migration：`ADD COLUMN pass_id` + `ALTER password_hash DROP NOT NULL` + `CREATE INDEX ix_user_pass_id` | 小 |
| `packages/shared-config/shared_config/settings.py` | 新增：`pass_base_url`、`kb_product_id` | 小 |
| `packages/shared-schemas/shared_schemas/auth.py` | `RegisterRequest` 移除 `tenant_name`，新增可选 `display_name`；其余不变 | 小 |
| `packages/shared-errors/` | 新增 Pass 错误码映射：PA-7001→404, PA-7003→409, PA-7004→403 | 小 |
| `apps/web/src/app/register/page.tsx` | "团队名称"字段改为可选的"昵称"字段 | 小 |
| `apps/web/src/app/login/page.tsx` | 不变（仍是 email+password 表单，调用同一 KB 后端） | 无 |
| `apps/web/src/stores/auth-store.ts` | `register()` 参数从 `(tenantName, email, password)` 改为 `(email, password, displayName?)`；注册后自动登录状态 | 小 |
| `apps/web/src/lib/api.ts` | 401 重试逻辑不变（仍调 KB `/v1/auth/refresh`，KB 后端代理 Pass refresh） | 无 |
| `services/api/app/utils/security.py` | `create_access_token()` / `decode_access_token()` 不再被 auth 流程调用，但 **保留**（可能被其他模块使用） | 无 |

---

#### 待确认事项（Q1-Q6 已全部澄清，2026-03-29）

| # | 问题 | 状态 | 结论 |
|---|-----|------|------|
| Q1 | productId 来源 | ✅ 已澄清 | `Product` 表主键（VarChar(36) UUID），由租户管理员在 PA 后台产品管理模块创建。KB 团队需找 PA 管理员创建产品并拿到 UUID，配置为环境变量 `KB_PRODUCT_ID` |
| Q2 | Pass API base URL | ✅ 已澄清 | Pass 模块挂载在 PA 核心 API 服务上，路由前缀 `/api/v1/pass/*`。开发：`http://localhost:3001`；生产：取决于部署域名（Nginx 反代），需运维确认。配置为环境变量 `PASS_BASE_URL` |
| Q3 | Token 有效期 | ✅ 已澄清 | 默认 3600 秒（1 小时），由 PA 侧 `AUTH_TOKEN_TTL_SECONDS` 控制。响应 `expiresAt` 是精确过期时间戳，KB 按此做 cookie max_age + 提前刷新 |
| Q4 | `/pass/me` 限流 | ✅ 已澄清 | 当前无限流（PA 代码无 `@Throttle` / `@RateLimit`）。KB 短期每次请求直接调；中期加 Redis 缓存（TTL 5 分钟） |
| Q5 | 密码策略 | ✅ 已澄清 | Pass：`@MinLength(8)` + `@MaxLength(128)`，无复杂度要求。KB 前端强校验完全兼容，无需改动 |
| Q6 | 封禁/解封 | ✅ 已澄清 | 管理端 `PATCH /pass-management/accounts/:id { status: "active" }` 可解封（需 `pass:manage` 权限）。无 C 端自助解封，KB 提示"请联系管理员" |
| — | 协议类型 | ✅ 已澄清 | REST API（非 OAuth2/OIDC），直接调用 `/pass/login` 返回 JWT |
| — | Token 验证方式 | ✅ 已决策 | 调用 `GET /pass/me` 验证（Pass JWT 签名由 PA 服务端验证，KB 无需本地验签） |
| — | Tenant 映射 | ✅ 已决策 | 每个 Pass 用户首次登录 KB 时创建独立 Tenant（沿用现有行为） |
| ⏳ | KB `productId` 实际值 | ⏳ 运维 | 需 PA 管理员在后台创建 KB 产品后提供 UUID |
| ⏳ | Pass API 生产域名 | ⏳ 运维 | 需运维确认生产环境部署地址 |
| ⏳ | 现有 KB 账号迁移策略 | ⏳ 产品决策 | 建议：上线时所有用户需通过 Pass 重新注册（v1 用户量极小，无需迁移脚本） |

---

#### 验收标准

- [ ] KB 登录页输入 email+password，后端调用 Pass `/login` → 成功登录 → 进入 `/projects`
- [ ] KB 注册页输入 email+password+昵称（可选），后端调用 Pass `/register` → 成功注册并自动登录
- [ ] 首次 Pass 登录自动创建 KB Tenant + User（`pass_id` 字段正确填充）
- [ ] 同一 Pass 账号重复登录 KB 不重复创建 Tenant/User
- [ ] Pass token 过期后，前端自动尝试 `/refresh` → 成功续期 → 用户无感知
- [ ] Pass token 过期且 refresh 失败 → 前端跳转登录页
- [ ] 已封禁账号（PA-7004）登录时提示"账号已被封禁，请联系管理员"
- [ ] 已注册邮箱再次注册（PA-7003）提示"邮箱已注册"
- [ ] KB 内部 `tenant_id` 隔离逻辑不变（两个不同 Pass 用户看不到对方的数据）
- [ ] `get_current_user()` 正确通过 Pass `/me` 验证 token → 返回正确的 User 对象
- [ ] 废弃的 `/forgot-password`、`/reset-password` 端点返回 410 Gone（或移除）
- [ ] 前端 TypeScript 编译无错误（`tsc --noEmit`）

---

#### 工作范围

**包含：**
- `services/api/app/services/auth_service.py` — 重写：login/register/refresh 代理 Pass API；新增 `PassClient` 封装 HTTP 调用
- `services/api/app/deps.py` — 修改 `get_current_user()`：Pass `/me` 验证 + `pass_id` 查 User
- `services/api/app/routers/auth.py` — 适配新 auth_service；注册改为注册即登录；废弃 forgot/reset-password
- `packages/shared-models/shared_models/user.py` — 新增 `pass_id` 字段；`password_hash` 改 nullable
- `infra/sql/alembic/` — migration：add `pass_id` + alter `password_hash` nullable + index
- `packages/shared-config/shared_config/settings.py` — 新增 `pass_base_url`、`kb_product_id`
- `packages/shared-schemas/shared_schemas/auth.py` — `RegisterRequest` 适配（移除 tenant_name，加 display_name）
- `packages/shared-errors/` — Pass 错误码映射
- `apps/web/src/app/register/page.tsx` — "团队名称" → "昵称"（可选）
- `apps/web/src/stores/auth-store.ts` — register 参数适配

**不包含：**
- 现有用户迁移脚本（v1 用户量极小，上线时用户通过 Pass 重新注册即可）
- MFA / 二次验证（由 Pass 侧负责）
- Redis 缓存 Pass `/me` 验证结果（中期优化，留衍生）
- `forgot-password` / `reset-password` 的 Pass 侧替代方案（密码重置由 PA 平台处理）
- Pass 管理 API（`/pass-management/*`）的集成（管理操作在 PA 后台完成）

---

### v0.44.16: KB 内部 `tenant_id` 全面重命名为 `kb_id`

**任务版本号：** v0.44.16
**优先级：** P1
**前置依赖：** 建议在 v0.44.14 / v0.44.15 解除阻塞前完成（以便 v0.44.14/15 实现时直接使用正确字段名）

---

#### 背景与动机

KB Platform 当前在整个代码库中使用 `tenant_id` 表示"一个 KB 注册账号所对应的独立知识库隔离单元"。在与 PA 中台进行集成（v0.44.14 审计日志上报、v0.44.15 PAPass 登录）时，PA 侧也有自己的 `tenant_id` 概念（代表 PA 中台的租户），两者含义不同，在联调时极易造成混淆。

**产品 Owner 决策（2026-03-28）：**
- 将 KB 内部的 `tenant_id` 字段统一重命名为 `kb_id`，明确其含义为"KB 平台内的隔离单元 ID"
- PA 侧字段名不变，KB 侧不得修改 PA 的任何接口或数据结构
- KB 向 PA 上报数据时（v0.44.14 / v0.44.15），将 KB 的 `kb_id` 值映射到 PA 约定的字段名（该字段名待 PA 提供接口规范后确认，v0.44.14 / v0.44.15 中明确写入映射逻辑）

---

#### 影响范围（全量扫描，执行前必须逐文件核对）

**数据库层（Alembic migration 必须覆盖所有表）：**

| 表名 | 重命名字段 |
|-----|-----------|
| `user` | `tenant_id` → `kb_id` |
| `project` | `tenant_id` → `kb_id` |
| `asset` | `tenant_id` → `kb_id` |
| `architecture` | `tenant_id` → `kb_id` |
| `architecture_node` | `tenant_id` → `kb_id`（若有） |
| `knowledge_doc` | `tenant_id` → `kb_id` |
| `knowledge_doc_version` | `tenant_id` → `kb_id`（若有） |
| `job` | `tenant_id` → `kb_id` |
| `api_key` | `tenant_id` → `kb_id` |
| `api_usage_log` | `tenant_id` → `kb_id`（v0.44.11 新建时可直接用 `kb_id`） |
| `audit_log` | `tenant_id` → `kb_id` |
| `cross_reference` | `tenant_id` → `kb_id`（若有） |
| `model_provider` | `tenant_id` → `kb_id`（若有） |
| `model_route` | `tenant_id` → `kb_id`（若有） |
| `batch_import` | `tenant_id` → `kb_id`（v0.44.5 新建时可直接用 `kb_id`） |

> ⚠️ **执行前必须先 `grep -rn "tenant_id" packages/shared-models/` 确认完整字段清单，以上列表为预估，实际以代码为准。**

**ORM 模型层（`packages/shared-models/`）：**
- 每个模型文件中的 `tenant_id: Mapped[uuid.UUID]` 列定义改为 `kb_id: Mapped[uuid.UUID]`
- `Column("tenant_id", ...)` → `Column("kb_id", ...)`
- 所有 relationship / backref / FK 引用同步更新

**依赖注入层（`services/api/app/deps.py`）：**
- `get_tenant_id()` 函数重命名为 `get_kb_id()`
- 函数内部：`current_user.tenant_id` → `current_user.kb_id`
- 所有 router 中的 `tenant_id: uuid.UUID = Depends(get_tenant_id)` → `kb_id: uuid.UUID = Depends(get_kb_id)`

**Router 层（`services/api/app/routers/`）：**
- 所有端点函数参数 `tenant_id` → `kb_id`
- 所有传给 service 的 `tenant_id=tenant_id` → `kb_id=kb_id`
- 所有 Query filter `.where(Model.tenant_id == tenant_id)` → `.where(Model.kb_id == kb_id)`

**Service 层（`services/api/app/services/`）：**
- 所有 service 类 / 方法参数 `tenant_id` → `kb_id`
- 内部所有 ORM 查询 / 写入字段同步

**JWT Payload（`services/api/app/routers/auth.py` 或 `auth_service.py`）：**
- JWT 中的 `{"tenant_id": ...}` → `{"kb_id": ...}`
- `get_current_user()` dep 中解析 JWT 时的字段键同步更新
- ⚠️ **JWT 字段变更会导致已颁发的旧 token 失效** — 需评估是否需要过渡期（建议：新版本上线时强制全部重新登录，在 v0.44.16 收尾说明中注明）

**前端（`apps/web/`）：**
- 所有调用后端 API 时传递 `tenant_id` 的请求 body / query param → 改用 `kb_id`（若有）
- Zustand / Context store 中存储的 `tenant_id` 字段 → `kb_id`
- TypeScript interface 中的 `tenant_id: string` → `kb_id: string`

**Worker 服务（`services/ingestion-worker/`、`services/pipeline-worker/`）：**
- 任何从消息队列 / Job 对象读取 `tenant_id` 的代码同步更新

---

#### 执行策略（必须严格遵守）

1. **单独开一个专用分支**：`feature/kb-id-rename`（不在 main 直接执行）
2. **执行顺序**：
   a. 先执行全仓库 `grep -rn "tenant_id"` 建立完整影响清单
   b. 先改 ORM 模型（`shared-models`）+ 写好全部 Alembic migration
   c. 再改 `deps.py`（`get_tenant_id` → `get_kb_id`）
   d. 再改所有 router / service（此时 IDE 会报类型错误，逐个修复）
   e. 再改 JWT payload + `get_current_user` 解析逻辑
   f. 再改前端 TypeScript 类型 + store + API 调用
   g. 再改 worker 服务
   h. 全部改完后运行测试（见验收标准）
3. **每一步改完后执行 `grep -rn "tenant_id"` 验证是否还有残留**
4. **禁止搜索替换全局 `sed -i`**：必须逐文件审阅，避免误改注释或 PA 侧变量名
5. **migration 命名**：`rename_tenant_id_to_kb_id_<table_name>`（每张表单独一个 migration，或一个统一 migration 含所有 `ALTER TABLE`）

---

#### 与 v0.44.14 / v0.44.15 的映射关系

当 KB 向 PA 上报数据时，需将 KB 的 `kb_id` 传给 PA：

| 上报场景 | KB 内部字段 | PA 侧期望字段名 | 映射处理 |
|---------|-----------|--------------|--------|
| v0.44.14 审计日志上报 | `kb_id` (UUID) | 待 PA 确认 | 在 `pa-logger.ts` / `audit_service.py` 推送时做字段别名映射 |
| v0.44.15 Pass 登录 | `kb_id` (UUID) | 不传给 PA（KB 内部字段） | KB 与 Pass 交互只用 `passId`（UUID）+ `productId`，不暴露 `kb_id` |

> **执行建议**：v0.44.16 先完成，v0.44.14/15 实现时直接使用 `kb_id`。v0.44.15 的 Pass 接入不向 PA 传 `kb_id`。

---

#### 验收标准

- [ ] `grep -rn "tenant_id" packages/shared-models/ services/ apps/` 结果为 **0 条**（PA 侧代码除外）
- [ ] 所有 Alembic migration 可正向执行（`alembic upgrade head` 成功）
- [ ] 所有 Alembic migration 可回滚（`alembic downgrade -1` 成功）
- [ ] 现有 API 端点（`/v1/projects`、`/v1/assets`、`/v1/docs` 等）返回正确数据，**tenant 隔离不变**（两个不同 `kb_id` 的账号互相看不到对方数据）
- [ ] 新注册账号可正常登录，JWT 中包含 `kb_id` 字段，`get_current_user` 正确解析
- [ ] 旧 JWT（含 `tenant_id` 字段）访问时，服务端返回 401（或明确的 "token 已失效" 提示）— 用户重新登录即可
- [ ] 前端 TypeScript 编译无错误（`tsc --noEmit` 通过）
- [ ] 前端 `useProjects`、`useAssets`、`useJobs` 等 hooks 正常工作

---

#### 工作范围

**包含：**
- `infra/sql/alembic/` — 所有含 `tenant_id` 列的表的 `ALTER TABLE ... RENAME COLUMN` migration
- `packages/shared-models/` — 所有模型文件
- `packages/shared-schemas/` — 所有含 `tenant_id` 字段的 Pydantic schema
- `services/api/app/deps.py` — `get_tenant_id` → `get_kb_id`
- `services/api/app/routers/` — 所有 router 文件
- `services/api/app/services/` — 所有 service 文件
- `services/api/app/routers/auth.py` / `auth_service.py` — JWT payload 字段名
- `services/ingestion-worker/` 和 `services/pipeline-worker/` — 读取 `tenant_id` 的相关代码
- `apps/web/src/` — TypeScript 接口定义 + store + API 调用层

**明确不包含：**
- PA 中台侧的任何代码或 API 字段（PA 侧字段名不变）
- 修改 `v0.44.14` / `v0.44.15` 中 PA 接口的字段期望（留在那两个任务实现时处理映射）
- 数据库中已有数据的值（`tenant_id` 的 UUID **值**不变，只改**列名**）

---

## 第六章 实现约束

### 6.1 目录规范

- 新增服务代码：`services/api/app/` 下对应的 router / middleware / services 子目录
- 新增数据模型：migration 在 `infra/sql/alembic/`，模型在 `packages/shared-models/`，schema 在 `packages/shared-schemas/`
- 新增前端组件：`apps/web/components/{FeatureName}/`，新增页面：`apps/web/app/`

### 6.2 字段命名约束（基于代码核实）

- 知识条目内容字段：`content_md`（不是 `content`）
- 版本变更说明字段：`change_reason`（不是 `change_summary`）
- 版本号字段：`version`（不是 `version_number`）
- 知识条目分类字段：`node_id`（不是 `architecture_id`）
- ArchitectureNode 软删除：`status = "archived"`（不是 `is_deleted`）
- Asset 状态字段：`parse_status`（不是 `status`）
- API Key 表名：`api_key`（单数）
- 新增表命名：遵循单数（`batch_import`、`batch_import_asset`、`api_usage_log`）
- **KB 内部隔离单元字段**：`kb_id`（v0.44.16 完成后全面替代旧字段名 `tenant_id`；v0.44.16 完成前，现有代码仍使用 `tenant_id`；v0.44.5/11 等新建的表，如 v0.44.16 先于其执行则直接用 `kb_id`，否则先建 `tenant_id` 后在 v0.44.16 统一迁移）

> **V2.3 新增（避免与已有表/字段冲突）：**

- CrossReference 表名：`cross_reference`（单数）— 已存在，v0.44 不新建
- CrossReference `relation_type` 枚举值：`related`、`depends_on`、`extends`、`contradicts`、`supersedes`（固定枚举，不可随意扩展）
- 审计日志表名：`audit_log`（单数）— 已存在，v0.44 各任务不重复创建
- 模型提供商表名：`model_provider`（单数）— 已存在
- 模型路由表名：`model_route`（单数）— 已存在

### 6.3 权限约束

- 所有新 API 端点必须接入已有的 `require_role()` 或 `get_api_key_project` 依赖
- 禁止硬编码权限检查；必须复用 `app/deps.py` 中的函数
- DELETE 操作优先使用 `status` 字段软删除

### 6.4 错误码约束

- 新错误码在 `packages/shared-errors/` 中注册
- 命名前缀：`VERSION_`、`BATCH_`、`GRAPH_`、`RATE_`、`PASS_`

---

## 第七章 任务领取规则

每次只能领取一个任务。完成后按第十一章格式汇报，等待确认后再领下一个。衍生发现仅记录不执行。

---

## 第八章 测试要求

- 后端：pytest，参考 `docs/tech-specs/testing-strategy.md`
- 前端：vitest
- 每个任务至少覆盖：happy path + 权限校验（at least 2 roles）+ 主要异常路径
- v0.44.7（ASR）：必须做实际文件上传的端到端测试，不能仅测 parser 函数

---

## 第九章 版本号管理

- 参考 `dev-governance-part1-version.md` §1.1–§1.4
- 本版本 16 个任务，版本号 `0.44.1` ~ `0.44.16`

---

## 第十章 文档产出要求

每个任务完成后同步更新：`TODO_NEXT.md`、`CHANGELOG.md`、本文件（任务状态 → Completed）

版本全部完成后产出：`docs/versions/phase-report-v0.44.md`；更新 WISHLIST.md 中已完成条目。

---

## 第十一章 汇报格式

参考 `dev-governance.md` §0.7，固定 9 项结构（计划 / 文件变更 / 用户可见能力 / 场景验证 / 开放问题 / 收尾说明 / 版本状态 / commit / 是否继续）。

---

## 第十二章 新增数据库表汇总

| 任务 | 新增表/字段 | 说明 |
|-----|-----------|------|
| v0.44.5 | `batch_import` | 批量导入批次记录 |
| v0.44.5 | `batch_import_asset` | 批次内文件关联 |
| v0.44.10 | `api_key.rate_limit_per_minute` | 已有表新增字段 |
| v0.44.11 | `api_usage_log` | API Key 调用日志 |

**合计：** 3 张新表 + 1 个已有表新增字段

---

## 第十三章 开始前必须先输出

领取第一个任务（v0.44.1）前，Claude Code 必须先输出：
1. **当前代码现状理解** — 确认 JWT payload 是否含 `role` 字段（读 `auth.py` token 生成逻辑）
2. **v0.44.1 的实施计划**
3. **v0.44.1 的预计修改文件清单**

在这三项输出之前，不要开始写代码。

---

## 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 优先级 | 实际完成日期 | 状态 |
|----------|--------|------|----------|------|
| v0.44.1 | 前端 RBAC 感知 | P0 | — | Planned |
| v0.44.2 | 前端用户管理页 | P0 | — | Planned |
| v0.44.3 | 版本历史 API 补全 | P0 | — | Planned |
| v0.44.4 | 前端版本历史 UI | P0 | — | Planned |
| v0.44.5 | 批量导入后端 | P1 | — | Planned |
| v0.44.6 | 前端批量导入 UI | P1 | — | Planned |
| v0.44.7 | ASR 端到端打通 | P1 | — | Planned |
| v0.44.8 | 图谱 ArchitectureNode 合并/拆分 API | P1 | — | Planned |
| v0.44.9 | 前端图谱编辑操作 | P1 | — | Planned |
| v0.44.10 | API Key 限流 | P1 | — | Planned |
| v0.44.11 | API 用量统计 | P1 | — | Planned |
| v0.44.12 | Q&A 对话界面 | P1 | — | Planned |
| v0.44.13 | 首次体验修复（仪表板统计 + 上传引导 + 表单说明） | P0 | — | Planned |
| v0.44.14 | 审计日志上报 PA 中台（服务端 + 客户端） | P0 | — | Blocked（待 PA 接口规范） |
| v0.44.15 | 登录接入 Pass（REST API 统一账号） | P0 | — | Planned（接入文档已确认，运维前置待完成） |
| v0.44.16 | KB 内部 `tenant_id` 全面重命名为 `kb_id` | P1 | — | Planned（建议在 v0.44.14/15 解除阻塞前完成） |

---

## 第十五章 变更记录

| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-27 | V1.0 初稿，未读代码（草稿） | 产品 Owner |
| 2026-03-28 | V2.0 全面修订：读代码核实后发现 5 处错误假设，RBAC 和版本历史各减少 1 个建表任务，总任务从 14 → 12，字段名全面修正 | 产品 Owner |
| 2026-03-28 | V2.1 规范审查修复：补 v0.44.4/v0.44.8/v0.44.10 的"不包含"边界段落（H-1）；修正 GET /versions 权限 editor+ → viewer+ 并加决策注释（H-2）；v0.44.1 补 JWT/me 三分支明确处理（H-3）；补 GET /batch-import/{batch_id} 返回结构（M-1）；v0.44.9 合并 parent_id 假设加注（M-2） | 产品 Owner |
| 2026-03-28 | V2.2 北极星过滤：砍出 W-007 SSE 进度推送（UX 优化，北极星三问不通过）；总任务 12 → 11；原 v0.44.9~v0.44.12 重编号为 v0.44.8~v0.44.11 | 产品 Owner |
| 2026-03-28 | V2.4 冲突修复：v0.44.10 移除新建 `rate_limiter.py`（与已有 `rate_limit.py` 冲突），改为在 `agent.py` 内联 per-key Redis INCR；错误码改用 `SYSTEM_RATE_LIMITED`（不新增 `RATE_LIMIT_EXCEEDED`）。 | 产品 Owner |
| 2026-03-28 | V2.5 新增任务 + 现状修正：① 新增 v0.44.12（Q&A 对话界面，后端 `POST /v1/qa/ask` SSE 已完整实现，仅缺前端）；② 新增 v0.44.13（首次体验修复：上传后自动触发 ingest job [P0-Critical]、仪表板统计、上传引导、表单说明、OnboardingGuide 修复）；③ v0.44.2 路径修正回滚；总任务数 11 → 13。 | 产品 Owner |
| 2026-03-28 | V2.6 产品决策 v0.44.2：将"用户管理入口隐藏"替换原"补全邀请/改角色/移除"方案。v1 单用户场景不需要用户管理；页面文件保留供企业版使用；侧边栏同步移除"审计日志"入口。 | 产品 Owner |
| 2026-03-28 | V2.7 新增 v0.44.16：KB 内部 `tenant_id` 全量重命名为 `kb_id`（DB migration + ORM + 所有 service/router/dep + JWT payload + 前端），PA 侧字段名不变；v0.44.14/15 与 PA 上报时做字段别名映射；总任务数 15 → 16。 | 产品 Owner |
| 2026-03-28 | V3.0 v0.44.15 全面重写：基于 PA Pass 接入文档 V1.0（2026-03-23）+ Q1-Q6 技术澄清。原 OAuth2/OIDC 假设全部替换为 Pass REST API 方案；认证信任根改为 Pass JWT（KB 不再自签 JWT）；验证方式为 `GET /pass/me`；KB 与 PA 交互只用 passId + productId，不传 tenant_id；状态从 Blocked → Planned。 | Claude Code |

---

## 第十六章 风险和缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|-----|------|--------|
| JWT payload 未含 role，v0.44.1 需先修 auth.py | 中 | 中 | Phase 1 先读 auth.py；若需修复，作为 v0.44.1 的前置微任务处理 |
| ASR 端到端发现 bug 超出预估工作量 | 中 | 中 | v0.44.7 设计为"验证+修复"闭环，若 bug 过多则拆为两个任务 |
| pipeline-worker SSE 推送结构复杂，改动超过 30 行 | 中 | 中 | Phase 1 先读 pipeline-worker 结构；若有统一 stage 回调则仅改一处 |
| 图谱合并/拆分跨表事务失败导致数据不一致 | 低 | 高 | 严格使用数据库事务，任何步骤失败全部回滚 |
| 16 个任务体量较大 | 中 | 中 | P0 任务（v0.44.1/2/13/14/15）可独立封版；P1 任务分批推进 |
| v0.44.16 tenant_id → kb_id 重命名漏改某处，导致 tenant 隔离失效（P0 安全风险） | 低 | 极高 | 执行前 grep 建立完整清单；每步改后再次 grep 验证；必须覆盖 tenant 隔离回归测试（两账号数据不互见）；必须单独分支独立 review |
| v0.44.16 JWT payload 字段变更导致所有已颁发 token 失效 | 高 | 低 | 属于预期行为；上线时安排所有用户重新登录；在 v0.44.16 收尾说明中注明并在前端展示"请重新登录"提示 |
| v0.44.15 Pass API 不可用时 KB 完全无法登录 | 中 | 高 | Pass 调用超时设 3s；错误信息明确提示"认证服务暂时不可用"；不做本地 fallback（Pass 是认证信任根） |
| v0.44.15 Pass `/me` 调用量随 KB API QPS 线性增长 | 中 | 中 | 短期无限流可直接调；中期加 Redis 缓存（pass_jwt_hash → passId 映射，TTL 5 分钟）；留衍生任务 |
| v0.44.15 切换后现有 KB 用户 JWT 全部失效 | 高 | 低 | 预期行为：v1 用户量极小，上线时所有用户通过 Pass 重新注册即可 |
