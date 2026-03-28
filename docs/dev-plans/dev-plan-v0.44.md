# KB Platform v0.44 版本开发任务计划

**文档编号**: PLAN-2026-03-28-v044
**版本**: V2.0（代码核实版，读代码后修订）
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
| W-015 | API 限流 + 用量统计 | **有**：`api_key` 无限速字段；无限流中间件；无用量记录 | **无** |

---

## 第三章 本轮目标与边界

### 3.1 版本主题

**v0.44：权限体系前端化 + 核心链路强化**

### 3.2 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 |
|----------|--------|------|------|
| v0.44.1 | 前端 RBAC 感知（角色上下文 + 权限门控 UI） | P0 | Planned |
| v0.44.2 | 前端用户管理页（邀请/改角色/移除，基于已有 API） | P0 | Planned |
| v0.44.3 | 版本历史 API 补全（`GET /versions` 列表 + `POST /rollback`） | P0 | Planned |
| v0.44.4 | 前端版本历史 UI（版本列表 + diff + 回滚） | P0 | Planned |
| v0.44.5 | 批量导入后端（ZIP 解压 + 批量任务调度 + batch API） | P1 | Planned |
| v0.44.6 | 前端批量导入 UI（拖拽上传 + 批次进度列表） | P1 | Planned |
| v0.44.7 | ASR 端到端打通（验证 + 修复 + 前端状态展示） | P1 | Planned |
| v0.44.8 | SSE 流水线进度推送（endpoint + pipeline-worker 推送 + 前端切换） | P1 | Planned |
| v0.44.9 | 图谱 ArchitectureNode 合并/拆分 API | P1 | Planned |
| v0.44.10 | 前端图谱编辑操作（选节点 + 合并/拆分面板） | P1 | Planned |
| v0.44.11 | API Key 限流（Redis token bucket，per key 速率限制） | P1 | Planned |
| v0.44.12 | API 用量统计（`api_usage_log` 表 + 查询端点） | P1 | Planned |

### 3.3 明确不做的事项

- ~~新建 RBAC 数据模型/中间件~~（已存在）
- ~~新建版本历史数据表~~（已存在 `knowledge_doc_version`）
- 项目级独立角色（user_project_roles 表）— 现有系统是 tenant-wide 角色，不在本版本引入 project-level 分层
- 图谱关系手动编辑（W-011）— 延后
- 多人协作编辑（W-012）— 北极星明确不做
- 多格式导出（W-006）— 延后
- AI 对话式 RAG / 自动摘要（W-008/009）— 延后

---

## 第四章 优先级与执行顺序

```
P0 优先：

v0.44.1 → v0.44.2    ← RBAC 前端（v0.44.2 依赖 v0.44.1 的角色上下文）
v0.44.3 → v0.44.4    ← 版本历史（v0.44.4 依赖 v0.44.3 的 API）

P1 独立，可按顺序推进：

v0.44.5 → v0.44.6    ← 批量导入（v0.44.6 依赖 v0.44.5 的 API）
v0.44.7              ← ASR 独立
v0.44.8              ← SSE 独立（参考 qa.py 已有实现）
v0.44.9 → v0.44.10  ← 图谱编辑（v0.44.10 依赖 v0.44.9 的 API）
v0.44.11 → v0.44.12 ← API 限流 + 统计（v0.44.12 可与 v0.44.11 同步进行）
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

### v0.44.2: 前端用户管理页

**任务版本号：** v0.44.2
**优先级：** P0
**前置依赖：** v0.44.1（需要角色上下文，否则无法控制页面访问）

---

#### 背景与目标

**后端现状（已有，无需修改）：**
- `GET /v1/users` — 列出租户内所有用户（分页）
- `POST /v1/users` — 邀请用户（入参：email + role）
- `PATCH /v1/users/{id}` — 修改用户角色或状态
- `DELETE /v1/users/{id}` — 软删除用户
- 以上全部要求 `tenant_admin` 角色

**目标（Goal）：**
为 tenant_admin 提供用户管理页面，通过已有 API 完成邀请成员、修改角色、移除成员操作。

---

#### 新增页面/组件

**新增页面：** `apps/web/app/settings/users/page.tsx`（路径待确认，与现有 settings 路由结构对齐）

**页面功能：**
1. 成员列表：邮箱、角色标签、状态（active/inactive）、邀请时间
2. "邀请成员" 按钮（tenant_admin 可见）→ Modal：输入邮箱 + 下拉选角色（不含 tenant_admin，防止越权）
3. 每行操作：
   - 修改角色（下拉，tenant_admin 可见）
   - 移除成员（确认对话框，tenant_admin 可见）
4. 自身不可修改/删除自己的角色（前端校验）

**新增组件：**
- `apps/web/components/UserManagement/InviteModal.tsx`
- `apps/web/components/UserManagement/UserTable.tsx`

---

#### 验收标准

- [ ] tenant_admin 登录后，导航中可进入用户管理页
- [ ] 用户列表正确展示成员邮箱、角色、状态
- [ ] 邀请新成员：输入 email + 选角色 → 提交 → 列表刷新 → 新成员出现
- [ ] 修改成员角色：下拉选择新角色 → 保存 → 角色标签更新
- [ ] 移除成员：确认对话框 → 确认 → 成员从列表中消失
- [ ] 非 tenant_admin 用户无法访问该页面（跳转到 403 或首页）

---

#### 工作范围

**包含：**
- `apps/web/app/settings/users/page.tsx`
- `apps/web/components/UserManagement/` 组件
- 导航栏中添加用户管理入口（tenant_admin 可见）

**不包含：**
- 任何后端修改
- SSO / 批量导入用户 / 用户注册流程修改

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

### v0.44.8: SSE 流水线进度推送

**任务版本号：** v0.44.8
**优先级：** P1
**前置依赖：** 无（独立任务；参考 `qa.py` 的 `StreamingResponse` 实现）

---

#### 需求定义

**目标（Goal）：**
为流水线任务新增 SSE 端点，pipeline-worker 在每个 stage 完成时向 Redis 发布消息，API 层订阅后推送给前端，替换现有的客户端轮询。

---

#### 新增 API 端点

| 端点 | 方法 | 权限 | 说明 |
|-----|------|------|------|
| `/v1/jobs/{job_id}/stream` | GET | JWT 认证 (`viewer+`) | SSE 流，推送 job 状态变化 |

**SSE 事件格式（参照 qa.py 已有 `text/event-stream` 实现）：**
```
event: progress
data: {"job_id": "uuid", "stage": "stage_3_classify", "progress_pct": 33, "message": "正在分类知识条目..."}

event: completed
data: {"job_id": "uuid", "knowledge_doc_count": 12}

event: failed
data: {"job_id": "uuid", "error": "ASR provider timeout"}

event: heartbeat
data: {}
```

**推送机制：**
- Redis channel：`job_progress:{job_id}`
- pipeline-worker 在每个 stage 完成时：`redis.publish(f"job_progress:{job_id}", json.dumps(payload))`
- API SSE endpoint：订阅该 channel，逐条转换为 SSE event 推送
- 无消息超过 30 秒时推送 `heartbeat` 事件
- job 结束（completed/failed）后，服务端主动关闭连接
- 连接最长保持 10 分钟

---

#### pipeline-worker 变更

**改动范围：** `services/pipeline-worker/` 内各 stage 完成处，追加 `redis.publish()` 调用

> Phase 1 必须先读 pipeline-worker 代码，确认：
> 1. 当前 stage 实现结构（是否有统一的 stage 完成回调？还是每个 stage 独立文件？）
> 2. pipeline-worker 是否已有 Redis 客户端可复用
> 根据实际结构决定最小改动方式，不重构 stage 架构。

---

#### 前端变更

- 现有轮询代码（`setInterval` + `GET /v1/jobs/{id}`）→ 替换为 `EventSource('/v1/jobs/{job_id}/stream')`
- `EventSource` 原生支持自动重连
- 收到 `completed` 或 `failed` 事件后，关闭 `EventSource`
- heartbeat 30s 无响应时视为超时，显示提示

---

#### 验收标准

- [ ] 触发流水线后，`Network` 面板中出现 SSE 连接（`/v1/jobs/{id}/stream`），无重复轮询 GET
- [ ] 前端进度随 stage 推送实时更新（不等待全部完成）
- [ ] job 完成后 SSE 连接自动关闭
- [ ] 30 秒 heartbeat 正常推送
- [ ] 现有 `GET /v1/jobs/{id}` 轮询端点保留（不删除，兼容其他调用方）

---

#### 工作范围

**包含：**
- `services/api/app/routers/jobs.py`（或等效路由文件）— 新增 `GET /v1/jobs/{job_id}/stream` SSE 端点
- `services/pipeline-worker/` — 各 stage 完成处追加 `redis.publish()` 调用（Phase 1 先读确认改动点）
- `apps/web/` — 将现有轮询替换为 `EventSource`

**不包含（延后）：**
- WebSocket 实现（本版本仅做 SSE，不引入 WebSocket 基础设施）
- 删除现有轮询端点 `GET /v1/jobs/{id}`（保留，兼容其他调用方）
- 批量 job 进度聚合推送（仅单个 job 的 stream）

---

### v0.44.9: 图谱 ArchitectureNode 合并/拆分 API

**任务版本号：** v0.44.9
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

---

### v0.44.10: 前端图谱编辑操作

**任务版本号：** v0.44.10
**优先级：** P1
**前置依赖：** v0.44.9（API 可用）

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
- 图谱边（CrossReference）的手动编辑与审核（W-011，独立版本）
- ArchitectureNode 重命名/描述修改（非本任务，可通过已有后端接口处理，不在此次 UI 中引入）
- 合并/拆分的撤销（Undo）功能

---

### v0.44.11: API Key 限流

**任务版本号：** v0.44.11
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

**新增文件：** `services/api/app/middleware/rate_limiter.py`

**算法：** 滑动窗口计数（用 Redis INCR + TTL 模拟）

**Redis Key 格式：** `rl:api:{api_key_id}:{unix_timestamp_minute}`
（每个整分钟一个 Key，TTL = 120 秒，避免时钟偏差导致 Key 过早过期）

**业务规则：**
1. 请求到达 `/v1/agent/*`，提取 `api_key.id` 和 `rate_limit_per_minute`
2. 若 `rate_limit_per_minute == 0`，跳过限流
3. 否则：`count = INCR rl:api:{api_key_id}:{minute}`；首次 INCR 时设置 TTL = 120s
4. 若 `count > rate_limit_per_minute`：返回 429 + header `Retry-After: {60 - current_second}` + 错误码 `RATE_LIMIT_EXCEEDED`
5. 否则：放行

**接入方式：** 在 `services/api/app/routers/agent.py` 的两个端点依赖链中注入 rate limiter（而不是全局 middleware，避免影响其他路由）

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
- `services/api/app/middleware/rate_limiter.py`（新建）
- `services/api/app/routers/agent.py` — 注入限流依赖
- `packages/shared-errors/` — 注册 `RATE_LIMIT_EXCEEDED`

**不包含：**
- 管理员修改 API Key 限流值的 UI（已有 `PATCH /v1/api-keys/{id}` 可覆盖，若不存在则作为衍生建议）

---

### v0.44.12: API 用量统计

**任务版本号：** v0.44.12
**优先级：** P1
**前置依赖：** v0.44.11（限流中间件已建立，可在同位置追加统计逻辑）

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

### 6.3 权限约束

- 所有新 API 端点必须接入已有的 `require_role()` 或 `get_api_key_project` 依赖
- 禁止硬编码权限检查；必须复用 `app/deps.py` 中的函数
- DELETE 操作优先使用 `status` 字段软删除

### 6.4 错误码约束

- 新错误码在 `packages/shared-errors/` 中注册
- 命名前缀：`VERSION_`、`BATCH_`、`GRAPH_`、`RATE_`

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
- 本版本 12 个任务，版本号 `0.44.1` ~ `0.44.12`

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
| v0.44.11 | `api_key.rate_limit_per_minute` | 已有表新增字段 |
| v0.44.12 | `api_usage_log` | API Key 调用日志 |

**合计：** 3 张新表 + 1 个已有表新增字段（相比 V1.0 草稿减少 3 张错误规划的表）

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
| v0.44.8 | SSE 流水线进度推送 | P1 | — | Planned |
| v0.44.9 | 图谱 ArchitectureNode 合并/拆分 API | P1 | — | Planned |
| v0.44.10 | 前端图谱编辑操作 | P1 | — | Planned |
| v0.44.11 | API Key 限流 | P1 | — | Planned |
| v0.44.12 | API 用量统计 | P1 | — | Planned |

---

## 第十五章 变更记录

| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-27 | V1.0 初稿，未读代码（草稿） | 产品 Owner |
| 2026-03-28 | V2.0 全面修订：读代码核实后发现 5 处错误假设，RBAC 和版本历史各减少 1 个建表任务，总任务从 14 → 12，字段名全面修正 | 产品 Owner |
| 2026-03-28 | V2.1 规范审查修复：补 v0.44.4/v0.44.8/v0.44.10 的"不包含"边界段落（H-1）；修正 GET /versions 权限 editor+ → viewer+ 并加决策注释（H-2）；v0.44.1 补 JWT/me 三分支明确处理（H-3）；补 GET /batch-import/{batch_id} 返回结构（M-1）；v0.44.9 合并 parent_id 假设加注（M-2） | 产品 Owner |

---

## 第十六章 风险和缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|-----|------|--------|
| JWT payload 未含 role，v0.44.1 需先修 auth.py | 中 | 中 | Phase 1 先读 auth.py；若需修复，作为 v0.44.1 的前置微任务处理 |
| ASR 端到端发现 bug 超出预估工作量 | 中 | 中 | v0.44.7 设计为"验证+修复"闭环，若 bug 过多则拆为两个任务 |
| pipeline-worker SSE 推送结构复杂，改动超过 30 行 | 中 | 中 | Phase 1 先读 pipeline-worker 结构；若有统一 stage 回调则仅改一处 |
| 图谱合并/拆分跨表事务失败导致数据不一致 | 低 | 高 | 严格使用数据库事务，任何步骤失败全部回滚 |
| 12 个任务体量仍较大 | 中 | 中 | P0 任务（v0.44.1–4）可独立封版；P1 任务可分批推进 |
