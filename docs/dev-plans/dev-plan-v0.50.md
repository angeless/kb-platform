# KB Platform v0.50 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v050
**版本**: V2.0（规范重写版）
**日期**: 2026-03-31
**基线**: v0.49 完成后
**依据**: PRD §7（审批工作流）+ §4.6（高危操作）+ §8（核心产出）
**作者**: Claude Code（自动生成）

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

基于 v0.49 完成后的代码增量增强。禁止重构无关模块。

### 1.2 继承已有能力

- **KnowledgeDoc**（`packages/shared-models/shared_models/knowledge.py`）— status 字段（draft / reviewing / published）+ update_type
- **CrossReference**（`packages/shared-models/`）— 5 种关系类型 CRUD
- **Pipeline 配置化**（v0.46）— PipelineStageConfig enable/disable + params
- **反思循环 v2**（v0.49.4-5）— 规则校验 + AI 自检 + 多轮循环
- **PipelineStageLog**（v0.47.6）— per-stage 执行日志 + token_usage
- **成本追踪**（v0.49.9）— cost_tracker + 预算限制
- **审计日志**（`services/api/app/services/audit_service.py`）— state-changing 操作记录
- **RBAC**（viewer / editor / project_admin / kb_admin）— JWT 角色校验
- **Redis**（已部署）— 缓存 / 限流 / 成本追踪

### 1.3 最小改动 / 1.4 任务领取规则

同 v0.47。

---

## 第二章 当前阶段事实

### 2.1 版本主题

**v0.50：工作流 & 治理 — 审批引擎 + 高危操作确认 + 文档模板扩展**

> 从"工具平台"升级为"治理平台"：引入正式的审批工作流、高危操作二次确认、术语表/维护指南文档模板。

---

## 第三章 本轮目标与边界

### 3.1 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.50.1 | 审批工作流 DB 模型 — ReviewTask 表 + 状态机 | P0 | 待开发 | PRD §7 |
| v0.50.2 | 审批工作流 API — 分配/批准/驳回/重新提交 | P0 | 待开发 | PRD §7 |
| v0.50.3 | 审批工作流前端 — 审批看板页 | P0 | 待开发 | PRD §7 |
| v0.50.4 | 审批工作流前端 — 审批操作组件 | P0 | 待开发 | PRD §7 |
| v0.50.5 | 高危操作二次确认 — 确认码机制 | P1 | 待开发 | PRD §4.6 |
| v0.50.6 | 术语表文档模板 — doc_type="glossary" | P1 | 待开发 | PRD §8 |
| v0.50.7 | 维护指南文档模板 — doc_type="maintenance_guide" | P2 | 待开发 | PRD §8 |
| v0.50.8 | 模型成本看板前端页 | P2 | 待开发 | PRD §5 UX |

### 3.2 北极星三问校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ |
|-----|----------------|-------------|-------------|
| v0.50.1 | ✅ 图谱质量（审批保障发布质量） | - | - |
| v0.50.2 | ✅ 图谱质量 | ✅ 输出接口 | - |
| v0.50.3 | - | ✅ 输出接口 | - |
| v0.50.4 | - | ✅ 输出接口 | - |
| v0.50.5 | - | - | ✅ 安全治理 |
| v0.50.6 | ✅ 图谱端（术语统一） | ✅ 输出接口 | - |
| v0.50.7 | - | ✅ 输出接口 | - |
| v0.50.8 | - | ✅ 输出接口 | - |

### 3.3 明确不做

- 多级审批（总监→VP→CEO）— v0.50 仅单级审批
- 审批 SLA（超时自动升级）— 留给未来
- 审批规则引擎（自动选择审批人）— 留给未来

---

## 第四章 执行顺序

```
审批链：v0.50.1 → v0.50.2 → v0.50.3 → v0.50.4
安全链：v0.50.5（依赖 v0.50.2 的确认模式可复用）
文档链：v0.50.6 → v0.50.7（独立）
看板：v0.50.8（依赖 v0.49.9 成本数据）
```

建议：`v0.50.1 → v0.50.2 → v0.50.3 → v0.50.4 → v0.50.5 → v0.50.6 → v0.50.7 → v0.50.8`

---

## 第五章 各任务详细定义

---

### v0.50.1: 审批工作流 DB 模型 — ReviewTask 表 + 状态机

**任务版本号：** v0.50.1
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**目标（Goal）：** 新增 `review_task` 表，建模审批工作流的状态机（pending → assigned → approved/rejected → resubmitted）。

---

#### 数据库变更

**新增文件：**
- `packages/shared-models/shared_models/review_task.py` — 新模型：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, default uuid4 | 主键 |
| project_id | UUID | FK→project.id, NOT NULL | 所属项目 |
| doc_id | UUID | FK→knowledge_doc.id, NOT NULL | 待审批文档 |
| reviewer_id | UUID | FK→user.id, nullable | 审批人（分配后填充） |
| status | VARCHAR(20) | NOT NULL, default 'pending' | pending/assigned/approved/rejected/resubmitted |
| assigned_at | TIMESTAMP | nullable | 分配时间 |
| reviewed_at | TIMESTAMP | nullable | 审批完成时间 |
| review_note | TEXT | nullable | 审批备注/驳回原因 |
| created_by | UUID | FK→user.id, NOT NULL | 创建者 |
| created_at | TIMESTAMP | default now() | 创建时间 |
| updated_at | TIMESTAMP | default now(), onupdate | 更新时间 |

- `infra/sql/alembic/versions/` — migration：`create_review_task_table`

**修改文件：**
- `packages/shared-models/shared_models/__init__.py` — 导出 ReviewTask

**状态机定义：**
```
pending → assigned（分配审批人）
assigned → approved（审批通过）
assigned → rejected（驳回）
rejected → resubmitted（作者修改后重新提交）
resubmitted → assigned（自动重新分配给原审批人）
approved → (触发 doc.status = "published")
```

**业务规则：**
① 创建 ReviewTask 时 status=pending，reviewer_id=NULL
② 分配审批人时 status→assigned，reviewer_id 填充
③ 审批通过时 status→approved，同时更新对应 doc 的 status 为 published
④ 驳回时 status→rejected，review_note 必填
⑤ 重新提交时 status→resubmitted，然后自动→assigned（原审批人）
⑥ 状态流转严格单向，不允许逆向（如 approved 不能回到 assigned）

---

#### 验收标准

- [ ] ReviewTask 表创建成功，包含 11 个字段
- [ ] 状态机流转：pending→assigned→approved 正常
- [ ] 状态机流转：pending→assigned→rejected→resubmitted→assigned 正常
- [ ] 非法状态转换（如 approved→pending）被拒绝
- [ ] `alembic downgrade -1` 可回滚

---

#### 工作范围

**包含：** 模型定义 + migration（~40 行）
**不包含：** API 端点（v0.50.2）；前端（v0.50.3-4）

---

#### 预估工作量

- Phase 1 读 KnowledgeDoc 模型 + User 模型确认 FK：0.5 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 状态机复杂度导致 edge case | 中 | 中 | 状态转换写成枚举+校验函数 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 KnowledgeDoc 模型确认 status 字段值
> 2. 读 User 模型确认 FK 可用
> 3. 确认当前 Alembic head revision

---

### v0.50.2: 审批工作流 API — 分配/批准/驳回/重新提交

**任务版本号：** v0.50.2
**优先级：** P0
**前置依赖：** v0.50.1（ReviewTask 模型存在）

---

#### 背景与目标

**目标（Goal）：** 提供审批工作流的完整 API（6 个端点），支持创建审批任务、分配审批人、批准/驳回、重新提交、列表查询。

---

#### 后端变更

**新增文件：**
- `services/api/app/routers/review.py` — 6 个端点
- `services/api/app/services/review_service.py` — 业务逻辑 + 状态转换

**API 契约：**

```
POST /v1/projects/{project_id}/reviews
认证：JWT，editor+
Body：{"doc_id": "uuid"}
Response 201：{"data": {"id": "uuid", "status": "pending", "doc_id": "...", "created_at": "..."}}
Response 400：文档不是 reviewing 状态
Response 404：文档不存在

POST /v1/projects/{project_id}/reviews/{review_id}/assign
认证：JWT，project_admin+
Body：{"reviewer_id": "uuid"}
Response 200：{"data": {"id": "...", "status": "assigned", "reviewer_id": "...", "assigned_at": "..."}}
Response 400：review 不是 pending/resubmitted 状态
Response 404：review 不存在

POST /v1/projects/{project_id}/reviews/{review_id}/approve
认证：JWT，reviewer 本人
Body：{"note": "可选备注"}
Response 200：{"data": {"id": "...", "status": "approved", "reviewed_at": "..."}}
Response 400：review 不是 assigned 状态
Response 403：非审批人本人

POST /v1/projects/{project_id}/reviews/{review_id}/reject
认证：JWT，reviewer 本人
Body：{"note": "驳回原因（必填）"}
Response 200：{"data": {"id": "...", "status": "rejected", "review_note": "..."}}
Response 400：review 不是 assigned 状态 / note 为空
Response 403：非审批人本人

POST /v1/projects/{project_id}/reviews/{review_id}/resubmit
认证：JWT，review 创建者
Body：无
Response 200：{"data": {"id": "...", "status": "assigned", "reviewer_id": "原审批人"}}
Response 400：review 不是 rejected 状态
Response 403：非创建者

GET /v1/projects/{project_id}/reviews
认证：JWT，viewer+
Query：?status=pending&page=1&page_size=20
Response 200：{"data": [...], "total": N, "page": 1}
```

**业务规则：**
① 创建审批：校验 doc 状态为 reviewing → 创建 ReviewTask(status=pending)
② 分配审批人：校验 reviewer_id 为有效用户 → status=assigned + assigned_at
③ 批准：校验调用者 = reviewer_id → status=approved + reviewed_at → **自动更新 doc.status='published'**
④ 驳回：校验调用者 = reviewer_id + note 非空 → status=rejected
⑤ 重新提交：校验调用者 = created_by → status=resubmitted → 自动 assigned（原 reviewer）
⑥ 列表查询：支持按 status 筛选 + 分页
⑦ 所有 state-changing 操作记录审计日志

---

#### 验收标准

- [ ] 创建审批 → 返回 pending 状态的 ReviewTask
- [ ] 分配审批人 → reviewer_id 正确设置
- [ ] 批准 → doc.status 变为 published
- [ ] 驳回 → review_note 记录驳回原因
- [ ] 重新提交 → 自动重新分配给原审批人
- [ ] 非法状态转换 → 400 错误
- [ ] 非审批人批准/驳回 → 403 权限拒绝
- [ ] 列表查询支持 status 筛选 + 分页

---

#### 工作范围

**包含：** 6 个 API 端点 + review_service.py（~150 行）
**不包含：** 前端 UI（v0.50.3-4）；审批通知（邮件/消息）

---

#### 预估工作量

- Phase 1 读 KnowledgeDoc 状态变更逻辑 + 审计日志记录方式：1 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 审批通过时 doc 状态更新并发问题 | 低 | 中 | 数据库事务保证原子性 |
| 审批增加文档发布延迟 | 确定 | 低 | 审批功能默认关闭，项目级配置开启 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 KnowledgeDoc 模型的 status 字段和更新方式
> 2. 读现有 router 注册方式确认路由模式
> 3. 确认审计日志记录接口

---

### v0.50.3: 审批工作流前端 — 审批看板页

**任务版本号：** v0.50.3
**优先级：** P0
**前置依赖：** v0.50.2（API 可用）

---

#### 背景与目标

**目标（Goal）：** 新增审批中心页面，以看板形式展示待分配/待审批/已完成的审批任务，支持按状态筛选和分页。

---

#### 前端变更

**修改文件：**
- `apps/web/src/app/(dashboard)/projects/[id]/review/page.tsx` — 重构为看板页：
  - 三列看板：待分配（pending） | 待审批（assigned） | 已完成（approved + rejected）
  - 每张卡片显示：文档标题、创建者、创建时间、审批人（如有）
  - 点击卡片 → 跳转到文档详情页
  - 分页加载（每列默认 10 条）

**业务规则：**
① 调用 `GET /v1/projects/{pid}/reviews?status={status}` 获取各列数据
② 待分配列：project_admin 可见"分配"按钮
③ 待审批列：显示审批人名称 + 分配时间
④ 已完成列：显示审批结果（通过/驳回）+ 审批备注
⑤ viewer 角色：只能查看，无操作按钮

---

#### 验收标准

- [ ] 审批中心页显示三列看板
- [ ] 每列正确显示对应状态的审批任务
- [ ] 卡片信息完整（文档标题、创建者、时间）
- [ ] 分页加载正常（超过 10 条时）
- [ ] 空状态（无审批任务）显示友好提示
- [ ] viewer 角色下操作按钮不可见

---

#### 工作范围

**包含：** review/page.tsx 看板布局 + 数据加载（~100 行）
**不包含：** 审批操作（分配/批准/驳回弹窗 — v0.50.4）

---

#### 预估工作量

- Phase 1 读 review/page.tsx 当前结构：0.5 小时
- Phase 2 执行：4 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 看板 UI 复杂度高 | 中 | 中 | 使用简单三列 CSS grid，不用拖拽库 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 review/page.tsx 当前内容
> 2. 确认项目页面导航结构

---

### v0.50.4: 审批工作流前端 — 审批操作组件

**任务版本号：** v0.50.4
**优先级：** P0
**前置依赖：** v0.50.3（看板页存在）

---

#### 背景与目标

**目标（Goal）：** 在审批看板上实现分配审批人弹窗、审批/驳回表单、审批历史时间线组件。

---

#### 前端变更

**修改文件：**
- `apps/web/src/app/(dashboard)/projects/[id]/review/page.tsx` — 新增交互组件：
  - **分配审批人弹窗**：选择用户下拉 → 调用 `POST .../assign`
  - **审批/驳回表单**：通过/驳回按钮 + 备注输入 → 调用 `POST .../approve` 或 `reject`
  - **审批历史时间线**：展示状态流转记录（创建→分配→审批，含时间和操作人）

**业务规则：**
① 分配弹窗：project_admin 点击"分配" → 弹窗显示项目成员列表 → 选择后调用 assign API
② 审批表单：审批人点击"通过"/"驳回" → 驳回时 note 必填 → 调用对应 API
③ 审批历史：根据 ReviewTask 的字段（created_at / assigned_at / reviewed_at）渲染时间线
④ 操作成功后刷新看板数据
⑤ 操作失败显示错误提示

---

#### 验收标准

- [ ] 分配弹窗显示项目成员列表，选择后分配成功
- [ ] 审批人可通过/驳回，驳回时备注必填
- [ ] 审批历史时间线展示状态流转过程
- [ ] 操作成功后看板自动刷新
- [ ] 非 project_admin 不能分配；非审批人不能审批
- [ ] 网络错误时显示错误提示

---

#### 工作范围

**包含：** 弹窗组件 + 表单组件 + 时间线组件（~100 行）
**不包含：** 审批通知（邮件/站内信）；拖拽看板交互

---

#### 预估工作量

- Phase 1 确认用户列表 API + 弹窗组件模式：0.5 小时
- Phase 2 执行：4 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 用户列表 API 不存在 | 中 | 中 | Phase 1 确认，如不存在需先实现 |

> ⚠️ **Phase 1 前置确认：**
> 1. 确认是否有获取项目成员列表的 API
> 2. 确认现有弹窗/modal 组件库（shadcn/radix/自定义）

---

### v0.50.5: 高危操作二次确认 — 确认码机制

**任务版本号：** v0.50.5
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**现状：** 发布架构、回滚文档、删除项目等高危操作无二次确认。

**目标（Goal）：** 实现确认码机制：高危操作第一次请求返回确认码，第二次请求携带确认码才真正执行。

---

#### 后端变更

**新增文件：**
- `services/api/app/utils/confirmation.py` — 确认码工具：
  ```
  def generate_confirmation(action: str, user_id: str) -> dict:
      # 生成 6 位随机码，存 Redis（TTL 5 分钟）
      # 返回 {"confirmation_id": "uuid", "expires_in": 300}

  def verify_confirmation(confirmation_id: str, code: str) -> bool:
      # 验证确认码，验证后删除（一次性）
  ```

- `services/api/app/utils/require_confirmation.py` — 装饰器：
  ```
  @require_confirmation
  async def dangerous_endpoint(...):
      # 第一次调用（无 confirmation_id）→ 返回 {"requires_confirmation": true, "confirmation_id": "xxx", "code": "123456"}
      # 第二次调用（携带 confirmation_id + code）→ 校验通过后执行原逻辑
  ```

**修改文件：** 以下端点加 `@require_confirmation` 装饰器：
- `POST /v1/architectures/{id}/publish`
- `POST /v1/docs/{id}/versions/{v}/rollback`
- `DELETE /v1/projects/{id}`
- `PATCH /v1/model-routes/{id}`（修改默认路由时）

**前端变更：**
- 通用确认弹窗组件：高危操作 API 返回 `requires_confirmation` 时，弹窗显示确认码 + 输入框

**业务规则：**
① 第一次调用高危端点 → 生成 6 位随机码存 Redis（key: `confirm:{confirmation_id}`，TTL 300s）
② 返回 `{"requires_confirmation": true, "confirmation_id": "uuid", "code": "123456"}`
③ 前端弹窗展示确认码，用户手动输入确认
④ 第二次调用携带 `X-Confirmation-ID` + `X-Confirmation-Code` header
⑤ 验证通过 → 执行原逻辑；失败 → 403
⑥ 确认码一次性使用，验证后从 Redis 删除
⑦ 超时（5 分钟）→ 需重新发起

---

#### 验收标准

- [ ] 删除项目 → 第一次返回确认码
- [ ] 第二次携带正确确认码 → 执行删除
- [ ] 确认码错误 → 403 拒绝
- [ ] 确认码过期（5 分钟后）→ 需重新发起
- [ ] 确认码一次性使用，重复提交 → 403
- [ ] 非高危操作不受影响
- [ ] 前端弹窗正确展示和输入确认码

---

#### 工作范围

**包含：** confirmation.py + require_confirmation 装饰器 + 4 个端点适配 + 前端弹窗（~60 行后端 + ~40 行前端）
**不包含：** 短信/邮件发送确认码（直接在响应中返回）

---

#### 预估工作量

- Phase 1 读 4 个高危端点逻辑 + Redis 使用方式：1 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 确认码存 Redis 依赖 | 低 | 中 | 降级方案：内存 dict（单实例限制） |
| 装饰器与 FastAPI 依赖注入冲突 | 中 | 中 | Phase 1 测试装饰器模式 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 4 个高危端点的完整逻辑
> 2. 确认 Redis 连接方式
> 3. 测试 FastAPI 装饰器与 Depends 的兼容性

---

### v0.50.6: 术语表文档模板 — doc_type="glossary"

**任务版本号：** v0.50.6
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**目标（Goal）：** 新增"术语表"文档模板，从项目所有 chunk 中提取专业术语，按字母/拼音排序，生成结构化术语表。

---

#### 后端变更

**修改文件：**
- `services/pipeline-worker/worker/stages/doc_generate.py` — 新增函数：
  ```
  def generate_glossary(db: Session, project_id: str, chunks: list, config: dict) -> str:
      # 从 chunks 中提取专业术语
      # 每个术语包含：名称、定义、首次出现文档
      # 按字母/拼音排序
      # 返回 Markdown 格式术语表
  ```

- `services/ai-orchestrator/orchestrator/prompts.py` — 新增 `build_glossary_extraction_prompt()`

**业务规则：**
① 从项目所有 published 文档的 chunks 中收集内容
② 调用 LLM 提取专业术语（名称 + 简短定义）
③ 去重：同义词合并（LLM 判断）
④ 按首字母/拼音排序
⑤ 生成 Markdown 表格：`| 术语 | 定义 | 首次出现 |`
⑥ 创建 KnowledgeDoc（doc_type="glossary"）存储结果
⑦ 触发方式：`POST /v1/projects/{pid}/ai-generate-glossary`（editor+）

---

#### API 契约

```
POST /v1/projects/{project_id}/ai-generate-glossary
认证：JWT，editor+
Body：无
Response 200：{"data": {"doc_id": "uuid", "terms_count": 42}}
Response 400：项目无 published 文档
```

---

#### 验收标准

- [ ] 调用 API 后生成 glossary 类型的 KnowledgeDoc
- [ ] 术语表包含术语名称、定义、首次出现文档
- [ ] 术语按字母排序
- [ ] 项目无 published 文档 → 400 错误
- [ ] 术语去重（同义词不重复列出）

---

#### 工作范围

**包含：** generate_glossary 函数 + prompt + API 端点（~60 行）
**不包含：** 术语表的前端专属展示页；术语的 CRUD 管理

---

#### 预估工作量

- Phase 1 读 doc_generate.py 结构 + KnowledgeDoc 创建方式：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM 术语提取不准确 | 中 | 低 | 人工可编辑生成的文档 |
| 大量 chunk 导致 token 超限 | 中 | 中 | 分批处理，每批 50 chunks |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 doc_generate.py 确认文档生成模式
> 2. 确认 KnowledgeDoc 的 doc_type 字段是否存在

---

### v0.50.7: 维护指南文档模板 — doc_type="maintenance_guide"

**任务版本号：** v0.50.7
**优先级：** P2
**前置依赖：** v0.50.6（复用术语表的生成模式）

---

#### 背景与目标

**目标（Goal）：** 新增"维护指南"文档模板，分析架构节点的更新策略和审批流程，生成维护建议文档。

---

#### 后端变更

**修改文件：**
- `services/pipeline-worker/worker/stages/doc_generate.py` — 新增函数：
  ```
  def generate_maintenance_guide(db: Session, project_id: str, config: dict) -> str:
      # 分析架构节点的 update_policy、review_policy
      # 生成：更新频率建议、审批流程说明、质量标准
      # 返回 Markdown
  ```

**API 契约：**
```
POST /v1/projects/{project_id}/ai-generate-maintenance-guide
认证：JWT，editor+
Response 200：{"data": {"doc_id": "uuid"}}
```

**业务规则：**
① 加载项目架构节点及其策略配置
② 调用 LLM 生成维护建议（更新频率、审批流程、质量标准）
③ 创建 KnowledgeDoc（doc_type="maintenance_guide"）

---

#### 验收标准

- [ ] 生成的维护指南包含更新频率建议
- [ ] 包含审批流程说明
- [ ] 包含质量标准检查清单
- [ ] 项目无架构节点 → 生成通用维护建议

---

#### 工作范围

**包含：** generate_maintenance_guide 函数 + API 端点（~40 行）
**不包含：** 维护指南的自动执行/提醒

---

#### 预估工作量

- Phase 1 读架构节点模型：0.5 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 架构节点无 policy 字段 | 中 | 中 | Phase 1 确认，无则生成通用建议 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读架构节点模型确认 update_policy / review_policy 字段是否存在

---

### v0.50.8: 模型成本看板前端页

**任务版本号：** v0.50.8
**优先级：** P2
**前置依赖：** v0.49.9（成本追踪数据可用）

---

#### 背景与目标

**目标（Goal）：** 新增成本看板页面，展示按模型/按任务类型/按日期的 token 消耗图表和预算使用情况。

---

#### 后端变更

**新增端点：**
```
GET /v1/model-usage/summary
认证：JWT，kb_admin
Query：?days=30
Response 200：{
  "data": {
    "by_model": [{"model": "gpt-4", "tokens": 100000, "cost_usd": 3.0}],
    "by_task_type": [{"task": "classify", "tokens": 50000}],
    "by_date": [{"date": "2026-03-30", "tokens": 10000}],
    "budget_used_pct": 65.0,
    "budget_limit_usd": 100.0
  }
}
```

#### 前端变更

**新增文件：**
- `apps/web/src/app/(dashboard)/settings/costs/page.tsx` — 成本看板页：
  - 按模型的 token 消耗柱状图
  - 按 task_type 的消耗饼图
  - 按日期的消耗折线图
  - 预算使用进度条（百分比）
  - 超限告警历史列表

**业务规则：**
① 从 `GET /v1/model-usage/summary` 获取数据
② 图表使用简单 CSS 柱状图/进度条（不引入图表库）
③ 预算 > 80% 时进度条变为橙色，> 100% 变为红色
④ 仅 kb_admin 可见

---

#### 验收标准

- [ ] 成本页展示按模型/任务/日期的消耗数据
- [ ] 预算进度条正确显示百分比
- [ ] 超过 80% 时视觉变化（橙色/红色）
- [ ] 非 kb_admin 访问 → 403 或重定向
- [ ] 无成本数据时显示空状态

---

#### 工作范围

**包含：** 聚合 API 端点 + 前端页面（~100 行前端 + ~30 行后端）
**不包含：** 图表库（recharts 等）；导出功能；实时更新

---

#### 预估工作量

- Phase 1 读 cost_tracker 数据结构 + Redis 存储格式：1 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Redis 中成本数据聚合查询性能 | 低 | 低 | 数据量有限（日级粒度） |
| 无图表库导致 UI 简陋 | 中 | 低 | CSS 进度条 + 简单表格足够 MVP |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 cost_tracker.py 确认 Redis 中数据存储格式
> 2. 确认 settings 页面导航结构

---

## 第六章 ~ 第十七章

### 第六章 实现约束
同 v0.47。

### 第七章 任务领取规则
同 v0.47。

### 第八章 测试要求
| 层次 | 覆盖重点 |
|------|---------|
| 后端单元测试 | 状态机转换、确认码生成/验证、术语提取 |
| 后端集成测试 | 审批 API 6 个端点（happy path + 权限 + 状态校验）、确认码端到端 |
| 前端组件测试 | 审批看板渲染、确认弹窗、成本看板 |

### 第九章 ~ 第十一章
同 v0.47。版本号：`v0.50.{Z}`，Z = 1-8。

### 第十二章 新增数据库表汇总

| 任务 | 表名 | 变更类型 | 字段 | 类型 | 约束 | 说明 |
|------|------|---------|------|------|------|------|
| v0.50.1 | review_task | **新增表** | id | UUID | PK | 主键 |
| v0.50.1 | review_task | | project_id | UUID | FK→project.id, NOT NULL | 所属项目 |
| v0.50.1 | review_task | | doc_id | UUID | FK→knowledge_doc.id, NOT NULL | 待审批文档 |
| v0.50.1 | review_task | | reviewer_id | UUID | FK→user.id, nullable | 审批人 |
| v0.50.1 | review_task | | status | VARCHAR(20) | NOT NULL, default 'pending' | 状态 |
| v0.50.1 | review_task | | assigned_at | TIMESTAMP | nullable | 分配时间 |
| v0.50.1 | review_task | | reviewed_at | TIMESTAMP | nullable | 审批时间 |
| v0.50.1 | review_task | | review_note | TEXT | nullable | 备注 |
| v0.50.1 | review_task | | created_by | UUID | FK→user.id, NOT NULL | 创建者 |
| v0.50.1 | review_task | | created_at | TIMESTAMP | default now() | 创建时间 |
| v0.50.1 | review_task | | updated_at | TIMESTAMP | default now() | 更新时间 |

合计：1 张新表（11 个字段），1 次 Alembic migration。

### 第十三章 开始前必须先输出
1. KnowledgeDoc / User / 审计日志当前代码理解
2. 第一个任务的实施计划
3. 预计修改文件清单

### 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|----------|--------|------|
| v0.50.1 | 审批 DB 模型 | — | 0 | Planned |
| v0.50.2 | 审批 API | — | 0 | Planned |
| v0.50.3 | 审批看板页 | — | 0 | Planned |
| v0.50.4 | 审批操作组件 | — | 0 | Planned |
| v0.50.5 | 高危操作确认 | — | 0 | Planned |
| v0.50.6 | 术语表模板 | — | 0 | Planned |
| v0.50.7 | 维护指南模板 | — | 0 | Planned |
| v0.50.8 | 成本看板 | — | 0 | Planned |

### 第十五章 变更记录
| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-31 | V1.0 初始版本 | Claude Code |
| 2026-03-31 | V2.0 规范重写：审批前端拆为看板+操作 2 任务，补齐必填字段 | Claude Code |

### 第十六章 决策与假设
**关键决策：**
- 单级审批 — v0.50 不支持多级审批，简化状态机
- 确认码直接返回给前端 — 不发短信/邮件，简化实现
- 成本看板不用图表库 — CSS 足够 MVP，避免额外依赖
- 审批功能默认关闭 — 需项目级配置开启

**假设：**
- 项目成员列表 API 已存在（用于分配审批人）
- Redis 可存储确认码（已部署）
- cost_tracker 的 Redis 数据格式可直接聚合

### 第十七章 版本级风险
| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 审批增加发布延迟 | 确定 | 低 | 默认关闭，项目级开启 |
| 确认码存 Redis 依赖 | 低 | 中 | 降级：内存 dict |
| 术语提取 LLM 成本 | 中 | 低 | 复用已有 chunk，分批处理 |
