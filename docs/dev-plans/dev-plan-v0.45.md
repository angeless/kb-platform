# KB Platform v0.45 版本开发任务计划

**文档编号**: PLAN-2026-03-28-v045
**版本**: V1.0（代码核实版）
**日期**: 2026-03-28
**基线 commit**: main HEAD (v0.43.5) — 待 v0.44 完成后更新至 v0.44.11
**基线分支**: main
**依据**: 产品北极星（docs/tech-specs/product-north-star.md）+ WISHLIST.md + 代码实际读取核实（2026-03-28）
**作者**: 产品 Owner

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.44.11 完成后的现有代码增量增强。禁止重构无关模块、禁止重写已有业务逻辑、禁止变更已有 API 契约（除非本计划明确要求）。

### 1.2 继承已有能力（代码核实后的完整清单）

以下能力经代码读取确认真实存在（2026-03-28 核实）：

- **`services/api/app/routers/search.py`** — 三个搜索端点均已实现（JWT 认证）：
  - `POST /v1/search/text`（全文检索，GIN 索引）
  - `POST /v1/search/semantic`（pgvector 余弦相似度）
  - `POST /v1/search/hybrid`（混合搜索，分数融合 + 去重 + 排序）
- **`services/api/app/routers/export.py`** — Markdown 导出和 ZIP 批量导出均已实现：
  - `GET /v1/docs/{doc_id}/export`（单文档 → Markdown）
  - `GET /v1/projects/{project_id}/export`（全项目 → ZIP of Markdowns）
- **`services/api/app/routers/cross_refs.py`** — 跨文档关联 CRUD 完整实现：
  - `POST /v1/cross-refs`（创建关联，editor+）
  - `GET /v1/cross-refs/doc/{doc_id}`（查某文档的所有关联）
  - `DELETE /v1/cross-refs/{ref_id}`（删除关联，editor+）
  - `GET /v1/cross-refs/project/{project_id}/graph`（项目关联图数据）
  - `POST /v1/cross-refs/auto-suggest`（AI 自动建议关联）
- **`packages/shared-models/shared_models/cross_reference.py`** — `CrossReference` 模型，关系类型：`related` / `depends_on` / `extends` / `contradicts` / `supersedes`；字段：`confidence`、`note`、`created_by`
- **`services/api/app/routers/audit.py`** — 审计日志查询端点已实现：
  - `GET /v1/audit-logs`（分页列表，支持按 project_id / action / resource_type 过滤，tenant_admin+）
- **`services/api/app/services/audit_service.py`** — `AuditService.log()` 和 `AuditService.list()` 均已实现；`log()` 目前仅在 `model_providers.py` 中被调用
- **`services/api/app/routers/model_providers.py`** — 模型提供商 + 路由规则 CRUD 完整实现：
  - `POST /v1/model-providers`（创建提供商）
  - `GET /v1/model-providers`（列表）
  - `POST /v1/model-providers/test`（连通性测试）
  - `POST /v1/model-routes`（创建路由）
  - `GET /v1/model-routes`（列表）
  - `PATCH /v1/model-routes/{route_id}`（更新）
  - `DELETE /v1/model-routes/{route_id}`（删除）
- **`packages/shared-models/shared_models/knowledge.py`** — `KnowledgeDoc` 有 `keywords`（JSONB，AI 设置）字段，**无 `summary` 字段**（v0.45 新增）
- **`services/api/app/routers/docs.py`** — 文档列表 API 已有分页（`page` / `page_size` query params）；前端尚未实现虚拟滚动
- **`services/ai-orchestrator/orchestrator/tasks.py`** — `generate_docs()` 已生成完整 `content_md`；`keywords` 由 LLM 填充；**无 AI 摘要生成步骤**；使用 `content_md[:200]` 作为临时 summary（非 AI 生成）

### 1.3 最小改动原则

每个任务只改必须改的文件。如果发现无关问题，记录到衍生建议但不执行。

### 1.4 任务领取规则

每次只能领取一个任务。完成后按第十一章格式汇报，确认后再领下一个。

---

## 第二章 当前阶段事实

### 2.1 项目目标

将多模态原始资料自动整理为可追溯、可维护、可被 AI 使用的结构化知识系统。平台本质是带知识拆解和结构化层的数据库，对外提供输入接口（接收多模态内容）和输出接口（Agent 可检索）。

### 2.2 当前基线

- **版本**: 待 v0.44 完成后更新（本计划在 v0.44 完成后启动）
- **分支**: main

### 2.3 代码核实后的 Gap 分析

> 以下 Gap 基于 2026-03-28 代码实际读取，而非文档描述。

| WISHLIST | 需求 | 后端 Gap | 前端 Gap |
|---------|------|---------|---------|
| W-003 | 混合检索 | **无**（`POST /v1/search/hybrid` 完整实现） | **有**：搜索页调用 `/v1/search/text`，未使用 hybrid 端点 |
| W-006 | 多格式导出 | **有**：仅 Markdown 导出，无 PDF / DOCX | **有**：无格式选择器，当前仅"导出 Markdown" |
| W-009 | AI 摘要与标签 | **有**：无 `summary` 字段，无 AI 摘要 API；`keywords` 已由流水线生成 | **有**：文档详情页无摘要区块 + 无手动触发标签建议 |
| W-011 | 图谱关系手动编辑 | **无**（CrossReference CRUD + auto-suggest 完整实现） | **有**：图谱/文档页仅展示，无创建/删除关联 UI |
| W-018 | 大规模分页 + 虚拟滚动 | **无**（所有列表 API 已有 page/page_size） | **有**：文档列表无虚拟滚动，大数据量下渲染性能差 |
| W-020 | 操作审计日志 | **部分**：model 和查询 API 已有；写入仅覆盖 model_providers（其余 CRUD 路由未写入） | **有**：无审计日志查看页 |
| W-021 | 全局设置页 | **无**（模型提供商 + 路由规则 CRUD 完整实现） | **有**：无前端设置页 |

---

## 第三章 本轮目标与边界

### 3.1 版本主题

**v0.45：输出接口质量提升 + 图谱可维护性 + 运营可见性**

### 3.2 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | WISHLIST 来源 |
|----------|--------|------|------|------------|
| v0.45.1 | 前端搜索页切换到混合检索 | P1 | Planned | W-003 |
| v0.45.2 | 后端 PDF / DOCX 导出扩展 | P1 | Planned | W-006 |
| v0.45.3 | 前端导出格式选择器 | P1 | Planned | W-006 |
| v0.45.4 | AI 摘要 DB 迁移（`knowledge_doc.summary` 字段） | P1 | Planned | W-009 |
| v0.45.5 | AI 摘要后端 API + orchestrator 任务 | P1 | Planned | W-009 |
| v0.45.6 | 前端文档详情页摘要 + 标签展示 | P1 | Planned | W-009 |
| v0.45.7 | 前端文档详情页跨文档关联面板 | P1 | Planned | W-011 |
| v0.45.8 | 前端图谱页关系编辑操作 | P1 | Planned | W-011 |
| v0.45.9 | 前端文档列表虚拟滚动 | P2 | Planned | W-018 |
| v0.45.10 | 后端审计写入集成（docs / projects / users CRUD） | P1 | Planned | W-020 |
| v0.45.11 | 前端审计日志页 | P1 | Planned | W-020 |
| v0.45.12 | 前端全局设置页（模型提供商 + 路由配置） | P1 | Planned | W-021 |
| v0.45.13 | AI 摘要/标签生成反思循环 — 后端自检 + 置信度评分 | P1 | Planned | W-024 |
| v0.45.14 | 前端摘要/标签置信度展示 | P2 | Planned | W-024 |

### 3.3 北极星三问校验

| 任务 | Q1 强化输入→整合→图谱核心链路？ | Q2 强化输入/输出接口？ | Q3 是核心链路的必要支撑？ | 结论 |
|-----|--------------------------|---------------------|----------------------|------|
| v0.45.1 | - | ✅ 输出接口质量（搜索更准） | - | ✅ 通过 |
| v0.45.2 | - | ✅ 输出接口（更多格式） | - | ✅ 通过 |
| v0.45.3 | - | ✅ 输出接口体验 | - | ✅ 通过 |
| v0.45.4 | ✅ 整合端（摘要丰富知识条目） | - | - | ✅ 通过 |
| v0.45.5 | ✅ 整合端 | - | - | ✅ 通过 |
| v0.45.6 | ✅ 整合端 | - | - | ✅ 通过 |
| v0.45.7 | ✅ 图谱端可维护性 | - | - | ✅ 通过 |
| v0.45.8 | ✅ 图谱端可维护性 | - | - | ✅ 通过 |
| v0.45.9 | - | - | ✅ 稳定性支撑（大规模数据基础设施） | ✅ 通过（边界） |
| v0.45.10 | - | - | ✅ 安全 / 合规 / 可审计 | ✅ 通过 |
| v0.45.11 | - | - | ✅ 安全 / 合规可见性 | ✅ 通过 |
| v0.45.12 | - | - | ✅ AI 模型配置是整合端基础设施 | ✅ 通过 |
| v0.45.13 | ✅ 整合端质量（AI 生成质量提升） | - | - | ✅ 通过 |
| v0.45.14 | - | - | ✅ 质量可见性（用户可感知 AI 置信度） | ✅ 通过（边界） |

### 3.4 明确不做的事项

- 多人实时协作编辑（W-012）— 北极星明确不做（协作平台，非知识整合）
- 站内 / 邮件通知（W-013）— 北极星三问不通过
- 项目级数据仪表盘（W-014）— 北极星三问不通过（"用"知识库而非"建"）
- 插件系统（W-019）— 当前阶段基础设施不成熟，暂不启动
- 多语言国际化（W-016）— 北极星三问不通过（与核心链路无关）
- 移动端适配（W-017）— 北极星三问不通过（UI 优化）
- SSE 进度推送（W-007）— 已从 v0.44 移出，北极星三问不通过，候排

---

## 第四章 优先级与执行顺序

```
W-003（混合检索）：
v0.45.1                      ← 纯前端，独立

W-006（多格式导出）：
v0.45.2 → v0.45.3            ← v0.45.3 依赖 v0.45.2 新增的导出格式

W-009（AI 摘要）：
v0.45.4 → v0.45.5 → v0.45.6  ← 严格顺序：先迁移 DB，再实现 API，再写前端

W-011（图谱关系编辑）：
v0.45.7 → v0.45.8            ← 两个前端任务，v0.45.8 与 v0.45.7 可并行但建议顺序推进

W-018（虚拟滚动）：
v0.45.9                      ← 纯前端，独立，P2 最后做

W-020（审计日志）：
v0.45.10 → v0.45.11          ← v0.45.11 依赖 v0.45.10 写入数据才有意义

W-021（全局设置）：
v0.45.12                     ← 纯前端，独立（API 已完整）

W-024（AI 反思循环）：
v0.45.13 → v0.45.14          ← v0.45.13 依赖 v0.45.5（AI 摘要 API），v0.45.14 依赖 v0.45.13 + v0.45.6
```

建议执行顺序（兼顾依赖链和风险）：

```
v0.45.1 → v0.45.4 → v0.45.5 → v0.45.2 → v0.45.3
→ v0.45.10 → v0.45.6 → v0.45.13 → v0.45.7 → v0.45.8
→ v0.45.11 → v0.45.12 → v0.45.14 → v0.45.9
```

---

## 第五章 各任务详细定义

---

### v0.45.1: 前端搜索页切换到混合检索

**任务版本号：** v0.45.1
**优先级：** P1
**前置依赖：** 无（后端 `POST /v1/search/hybrid` 已完整实现）

---

#### 背景与目标

**后端现状（已有）：**
- `POST /v1/search/text`：全文检索（GIN 索引 + ILIKE 兜底）
- `POST /v1/search/hybrid`：混合检索（tsvector + pgvector 融合，分数合并，去重排序）
- 前端当前调用：`/v1/search/text`（仅关键词匹配，无语义）

**目标（Goal）：**
前端搜索页将 API 调用从 `/v1/search/text` 切换为 `/v1/search/hybrid`，使用户获得语义增强的搜索结果。

**Request / Response 对比：**

| | `/v1/search/text` | `/v1/search/hybrid` |
|--|-------------------|---------------------|
| Body | `{project_id, query, page, page_size}` | `{project_id, query, page, page_size}` — **完全相同** |
| 结果字段 | `SearchHit` | `HybridSearchHit`（多一个 `score` 字段） |

> ⚠️ **Phase 1 前置确认：** 读前端搜索组件，确认当前调用路径，检查 TypeScript 类型是否需要扩展（增加 `score?: number`）。

---

#### 前端变更

**修改文件：**
- 前端搜索 API 调用处（具体路径 Phase 1 读代码确认）
  - 将 URL 从 `/v1/search/text` 改为 `/v1/search/hybrid`
  - 将 Response 类型从 `SearchHit` 改为 `HybridSearchHit`（添加 `score?: number`）
  - （可选）搜索结果中展示相关性分数标识（如"语义匹配"角标）

---

#### 验收标准

- [ ] 搜索输入中文语义词（如"投资逻辑"），可以匹配到关键词中没有该词但语义相关的文档
- [ ] 搜索结果正确分页（page/page_size 参数生效）
- [ ] 搜索结果展示与切换前无视觉回归（布局不变，仅结果质量提升）
- [ ] `score` 字段不为 null，搜索结果按分数降序排列

---

#### 工作范围

**包含：**
- 前端搜索 API 调用切换（1 处）
- 前端 TypeScript 类型扩展

**不包含：**
- 后端 hybrid_search 逻辑修改
- 搜索结果高亮（独立优化，不在本任务）

---

#### 预估工作量

- Phase 1 读代码定位：0.5 小时
- Phase 2 执行：1.5 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| hybrid 端点响应略慢于 text（向量计算） | 中 | 低 | 可接受，搜索场景用户容忍延迟稍高 |
| 前端搜索调用散布多处 | 低 | 中 | Phase 1 全局 grep 确认 |

---

### v0.45.2: 后端 PDF / DOCX 导出扩展

**任务版本号：** v0.45.2
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**后端现状（已有）：**
- `GET /v1/docs/{doc_id}/export`：返回 Markdown 文本（`Content-Type: text/markdown`）
- `GET /v1/projects/{project_id}/export`：返回所有文档的 ZIP（Markdown 格式）

**目标（Goal）：**
在现有导出端点上增加 `format` 查询参数，支持 `pdf` 和 `docx` 格式导出。

---

#### 后端变更

**修改文件：**
- `services/api/app/routers/export.py` — 为 `GET /v1/docs/{doc_id}/export` 添加 `format: str = Query(default="markdown", pattern="^(markdown|pdf|docx)$")` 参数

**新增文件：**
- `services/api/app/services/export_service.py` — 封装 Markdown → PDF / DOCX 转换逻辑
  - PDF：使用 `weasyprint`（HTML → PDF）；或 `reportlab`（纯 Python）
  - DOCX：使用 `python-docx`
  - 输入：`content_md: str`，输出：`bytes`

**依赖新增：**
- `services/api/requirements.txt` 中新增 `weasyprint` 和 `python-docx`

> ⚠️ **Phase 1 前置确认：** 读 `services/api/requirements.txt`，确认是否已有 `weasyprint` / `python-docx`。如果已有，跳过依赖添加步骤。

---

#### API 契约

```
GET /v1/docs/{doc_id}/export?format=pdf
返回：application/pdf，bytes

GET /v1/docs/{doc_id}/export?format=docx
返回：application/vnd.openxmlformats-officedocument.wordprocessingml.document，bytes

GET /v1/docs/{doc_id}/export（原有）
返回：text/markdown，string
```

**错误处理：**
- `format` 非法值 → 422 Validation Error
- 文档不存在 → 404
- 转换失败（如 Markdown 格式异常）→ 500 + 错误描述

---

#### 验收标准

- [ ] `?format=markdown` 行为与现有完全一致（不回归）
- [ ] `?format=pdf` 返回合法 PDF 文件，Markdown 标题渲染为 PDF 标题，正文可阅读
- [ ] `?format=docx` 返回合法 DOCX 文件，可用 Word / LibreOffice 打开
- [ ] `?format=invalid` 返回 422
- [ ] 内容含 CJK 字符时不乱码

---

#### 工作范围

**包含：**
- `services/api/app/routers/export.py`（扩展现有端点）
- `services/api/app/services/export_service.py`（新增）
- `services/api/requirements.txt`（添加依赖，如尚未存在）

**不包含（延后至 v0.45.3）：**
- 前端格式选择器 UI

**不包含（不做）：**
- 项目级 ZIP 导出的 PDF/DOCX 支持（单文档优先，ZIP 批量导出暂不扩展）

---

#### 预估工作量

- Phase 1 读代码 + 依赖确认：1 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| weasyprint 在容器中缺少字体导致 PDF 乱码 | 中 | 中 | Dockerfile 添加 `fonts-noto-cjk` |
| 复杂 Markdown（表格/代码块）PDF 渲染不完美 | 高 | 低 | 可接受，先出基础版 |

---

### v0.45.3: 前端导出格式选择器

**任务版本号：** v0.45.3
**优先级：** P1
**前置依赖：** v0.45.2（后端支持 format 参数）

---

#### 背景与目标

**后端现状（v0.45.2 完成后）：**
- `GET /v1/docs/{doc_id}/export?format=markdown|pdf|docx` 均可用

**目标（Goal）：**
文档详情页"导出"按钮改为下拉菜单，用户可选择 Markdown / PDF / DOCX 三种格式。

---

#### 前端变更

**修改文件：**
- 文档详情页导出按钮（Phase 1 确认路径）
  - 将单一"导出"按钮改为三选项下拉菜单（Markdown / PDF / DOCX）
  - 点击后以 `format` 参数调用导出 API，触发浏览器文件下载

---

#### 验收标准

- [ ] 文档详情页"导出"按钮展开后显示三个选项
- [ ] 选择 Markdown：下载 `.md` 文件
- [ ] 选择 PDF：下载 `.pdf` 文件
- [ ] 选择 DOCX：下载 `.docx` 文件
- [ ] 下载中显示 loading 状态，完成后恢复正常

---

#### 工作范围

**包含：**
- 文档详情页导出按钮改为下拉菜单（1 处 UI 修改）

**不包含：**
- 列表页批量导出格式选择（单独需求）

---

#### 预估工作量

- Phase 1 + Phase 2 执行：2 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 下拉菜单在移动端展示不友好 | 低 | 低 | 可接受，当前阶段仅桌面端 |

---

### v0.45.4: AI 摘要 DB 迁移（`knowledge_doc.summary` 字段）

**任务版本号：** v0.45.4
**优先级：** P1
**前置依赖：** 无（可与 v0.45.1–v0.45.3 并行）

---

#### 背景与目标

**现状：**
- `KnowledgeDoc` 无 `summary` 字段
- AI orchestrator 使用 `content_md[:200]` 作为临时代理摘要（非 AI 生成，不持久化）
- `keywords` 字段已有（AI 生成，JSONB）

**目标（Goal）：**
向 `knowledge_doc` 表新增可空的 `summary` 字段（TEXT），为 v0.45.5 AI 摘要 API 提供存储支撑。

---

#### 后端变更

**修改文件：**
- `packages/shared-models/shared_models/knowledge.py` — `KnowledgeDoc` 新增：
  ```python
  summary: Mapped[str | None] = mapped_column(Text, nullable=True)
  ```

**新增文件：**
- `infra/sql/alembic/versions/{hash}_add_summary_to_knowledge_doc.py` — Alembic 迁移脚本
  ```sql
  ALTER TABLE knowledge_doc ADD COLUMN summary TEXT;
  ```

> ⚠️ Alembic 迁移命名规范：`{timestamp}_{hash}_add_summary_to_knowledge_doc.py`，与已有迁移文件命名风格一致。

---

#### 验收标准

- [ ] `alembic upgrade head` 成功执行，无报错
- [ ] `knowledge_doc` 表中 `summary` 字段存在（`\d knowledge_doc` 可见）
- [ ] 现有记录 `summary` 值为 NULL（不影响已有数据）
- [ ] `alembic downgrade -1` 回滚成功（迁移可逆）

---

#### 工作范围

**包含：**
- `packages/shared-models/shared_models/knowledge.py`（新增字段）
- Alembic 迁移脚本（新增）

**不包含：**
- AI 摘要生成逻辑（v0.45.5）
- 前端展示（v0.45.6）

---

#### 预估工作量

- 执行：1 小时
- 测试：0.5 小时

---

### v0.45.5: AI 摘要后端 API + orchestrator 任务

**任务版本号：** v0.45.5
**优先级：** P1
**前置依赖：** v0.45.4（`summary` 字段存在）

---

#### 背景与目标

**目标（Goal）：**
新增 `POST /v1/docs/{doc_id}/ai-summarize` 端点，触发 AI orchestrator 对指定文档生成结构化摘要（≤200 字），并写入 `knowledge_doc.summary` 字段。

---

#### 后端变更

**新增文件：**
- `services/api/app/routers/ai_actions.py` — 新路由文件
  ```
  POST /v1/docs/{doc_id}/ai-summarize
  POST /v1/docs/{doc_id}/ai-suggest-tags
  ```
- `services/ai-orchestrator/orchestrator/tasks.py` — 新增 `generate_summary(doc_id: str) -> dict` Celery task

**修改文件：**
- `services/api/app/main.py` — 注册 `ai_actions` router

**generate_summary task 逻辑：**
1. 读取 `KnowledgeDoc` 的最新版本 `content_md`
2. 构建摘要 prompt（"请用不超过200字概括以下知识条目的核心内容"）
3. 调用 `call_llm()`
4. 将结果写入 `knowledge_doc.summary`
5. 返回 `{"status": "success", "summary": "..."}`

**ai-suggest-tags task 逻辑：**
1. 读取 `KnowledgeDoc` 的最新版本 `content_md`
2. 构建标签建议 prompt（返回 JSON array of strings）
3. 调用 `call_llm()` + `parse_json_response()`
4. 将结果写入 `knowledge_doc.keywords`（覆盖）
5. 返回 `{"status": "success", "keywords": [...]}`

---

#### API 契约

```
POST /v1/docs/{doc_id}/ai-summarize
认证：JWT，editor+
Body：无（或 {} 空 JSON）
Response 200：
{
  "data": {
    "doc_id": "...",
    "summary": "不超过200字的AI摘要文本"
  }
}

POST /v1/docs/{doc_id}/ai-suggest-tags
认证：JWT，editor+
Body：无
Response 200：
{
  "data": {
    "doc_id": "...",
    "keywords": ["标签1", "标签2", ...]
  }
}
```

**错误处理：**
- 文档不存在 → 404
- 文档无版本内容（`content_md` 为空）→ 422
- LLM 调用失败 → 500 + 错误描述

---

#### 验收标准

- [ ] `POST /v1/docs/{doc_id}/ai-summarize` 调用后 DB 中 `summary` 字段被写入，非 NULL
- [ ] summary 长度 ≤ 200 字（中文）
- [ ] `POST /v1/docs/{doc_id}/ai-suggest-tags` 调用后 `keywords` 字段被更新
- [ ] 权限：viewer 调用返回 403
- [ ] 文档不存在返回 404

---

#### 工作范围

**包含：**
- `services/api/app/routers/ai_actions.py`（新增）
- `services/ai-orchestrator/orchestrator/tasks.py`（新增 2 个 task）
- `services/api/app/main.py`（注册新 router）

**不包含：**
- 自动触发（不在文档保存时自动调用）
- 前端展示（v0.45.6）

---

#### 预估工作量

- Phase 1 理解 orchestrator 调用模式：1 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM 摘要不稳定（超过200字或空响应） | 中 | 低 | 后处理截断，空响应保留原有 summary 不覆盖 |
| orchestrator 与 API service 共用 DB session 的并发问题 | 低 | 中 | 参考现有 `generate_docs` 使用 `_get_sync_session()` 模式 |

---

### v0.45.6: 前端文档详情页摘要 + 标签展示

**任务版本号：** v0.45.6
**优先级：** P1
**前置依赖：** v0.45.5（摘要 API 可用）

---

#### 背景与目标

**目标（Goal）：**
文档详情页新增摘要区块和标签区块，并提供"重新生成摘要"和"刷新标签建议"的触发按钮。

---

#### 前端变更

**修改文件：**
- 文档详情页（Phase 1 确认路径）
  - 新增 Summary 区块（在标题下方）：展示 `summary` 字段；若为 null 显示"暂无摘要"+ "生成摘要"按钮
  - 新增 Tags 区块（在摘要下方）：展示 `keywords` 数组为标签 chip；提供"刷新标签"按钮
  - "生成摘要"和"刷新标签"按钮调用 v0.45.5 对应端点，完成后刷新页面数据

---

#### 验收标准

- [ ] 文档有摘要时，详情页展示摘要文本
- [ ] 文档无摘要时，展示"暂无摘要"提示 + "生成摘要"按钮
- [ ] 点击"生成摘要"后，loading 状态展示，完成后摘要区块更新（无需刷新页面）
- [ ] 标签展示为 chip 形式，多个标签横排
- [ ] 以 viewer 角色登录，"生成摘要"和"刷新标签"按钮不可见（或 disabled 并 tooltip 说明）

---

#### 工作范围

**包含：**
- 文档详情页 Summary 区块 + Tags 区块（2 处 UI 新增）
- API 调用集成（ai-summarize + ai-suggest-tags）

**不包含：**
- 在文档保存时自动触发摘要生成

---

#### 预估工作量

- Phase 1 + Phase 2 执行：3 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| summary 为 null 的旧文档导致前端空状态不友好 | 中 | 低 | 空摘要显示"暂无摘要"+ 生成按钮（已在设计中） |

---

### v0.45.7: 前端文档详情页跨文档关联面板

**任务版本号：** v0.45.7
**优先级：** P1
**前置依赖：** 无（后端 CrossReference API 已完整）

---

#### 背景与目标

**后端现状（已有）：**
- `POST /v1/cross-refs`：创建关联（editor+）
- `GET /v1/cross-refs/doc/{doc_id}`：获取某文档的所有关联
- `DELETE /v1/cross-refs/{ref_id}`：删除关联（editor+）
- `POST /v1/cross-refs/auto-suggest`：AI 自动建议关联

**目标（Goal）：**
文档详情页新增"关联文档"侧面板，展示当前文档的所有跨文档关联，并允许 editor+ 创建/删除关联。

---

#### 前端变更

**修改文件：**
- 文档详情页（新增关联面板组件）

**新增组件（可放在同一文件或单独文件）：**
- `CrossRefPanel`：
  - 列出当前文档的所有关联（`GET /v1/cross-refs/doc/{doc_id}`）
  - 每条关联展示：关联方向（from/to）、关联类型（related/depends_on/extends/contradicts/supersedes 中文标签）、目标文档标题
  - editor+ 可见：删除按钮（调用 `DELETE /v1/cross-refs/{ref_id}`）
  - editor+ 可见："添加关联"按钮 → 打开 Modal
    - Modal 内：文档 ID 或标题搜索框 + 关联类型下拉 + 可选备注 + 提交按钮
  - "AI 建议关联"按钮（调用 `POST /v1/cross-refs/auto-suggest`）→ 展示建议列表，用户可一键确认创建

---

#### 验收标准

- [ ] 文档详情页展示"关联文档"面板，显示已有关联列表
- [ ] 关联类型以中文标签展示（如"依赖"、"扩展"、"矛盾"）
- [ ] editor+ 可创建新关联（Modal 表单）
- [ ] editor+ 可删除已有关联
- [ ] "AI 建议关联"返回建议后，用户可确认/忽略
- [ ] viewer 角色下，添加/删除按钮不渲染

---

#### 工作范围

**包含：**
- 文档详情页关联面板

**不包含（v0.45.8）：**
- 图谱页上的关联编辑操作

---

#### 预估工作量

- Phase 1 读前端文档详情页结构：1 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| AI auto-suggest 响应慢（向量计算） | 中 | 低 | 异步触发，显示 loading，建议结果可延迟展示 |

---

### v0.45.8: 前端图谱页关系编辑操作

**任务版本号：** v0.45.8
**优先级：** P1
**前置依赖：** v0.45.7（关联面板已实现，可复用组件逻辑）

---

#### 背景与目标

**目标（Goal）：**
图谱可视化页面从只读变为可编辑：支持查看边的关联类型、删除关联、跳转到创建关联操作。

> ⚠️ **Phase 1 前置确认：** 读图谱页实现，确认当前用什么图谱库（cytoscape.js / vis-network / d3 / react-force-graph 等），确认边的点击事件是否已实现。

---

#### 前端变更

**修改文件：**
- 图谱页

**新增功能：**
- 边（CrossReference）上展示关联类型标签（`relation_type` 中文）
- 点击边 → 侧边 PopupPanel 显示关联详情（source 标题、target 标题、类型、备注、创建者）
- PopupPanel 中 editor+ 可见删除按钮（调用 `DELETE /v1/cross-refs/{ref_id}`，删除后刷新图谱数据）
- 图谱工具栏增加"添加关联"入口 → 与 v0.45.7 复用相同 CreateCrossRefModal 组件

---

#### 验收标准

- [ ] 图谱中的边展示关联类型标签（至少鼠标悬停可见）
- [ ] 点击边弹出详情面板
- [ ] editor+ 在详情面板中可删除关联
- [ ] 删除后图谱即时刷新（关联边消失）
- [ ] viewer 角色下无删除按钮

---

#### 工作范围

**包含：**
- 图谱页边标签 + 点击详情面板 + 删除操作

**不包含：**
- 图谱布局算法优化（独立需求）
- 节点过滤器（独立需求）

---

#### 预估工作量

- Phase 1 读图谱库实现：1.5 小时
- Phase 2 执行：4 小时
- Phase 3 测试：1.5 小时

---

### v0.45.9: 前端文档列表虚拟滚动

**任务版本号：** v0.45.9
**优先级：** P2
**前置依赖：** 无

---

#### 背景与目标

**现状：**
- 后端文档列表 API 已有分页（`page` / `page_size`），默认每页 20 条
- 前端文档列表加载后直接渲染所有 DOM 元素，数据量大时性能差

**目标（Goal）：**
文档列表使用虚拟滚动（仅渲染可视区域内的行），在 1000+ 条文档的项目中保持流畅滚动。

> ⚠️ **Phase 1 前置确认：** 读前端文档列表组件，确认当前渲染方式（Table / List / 自定义）；确认是否已引入 `react-window` 或 `@tanstack/react-virtual`。

---

#### 前端变更

**修改文件：**
- 文档列表组件
  - 引入 `react-window` 的 `FixedSizeList` 或 `@tanstack/react-virtual`（根据现有依赖优先选已有的）
  - 改为虚拟渲染：只渲染可视区域 ± buffer 的行

**新增依赖（若尚未存在）：**
- `react-window` 或 `@tanstack/react-virtual`

---

#### 验收标准

- [ ] 加载 500 条文档时，列表首屏渲染耗时 < 500ms（Chrome DevTools Performance）
- [ ] 快速滚动时无明显白屏/卡顿
- [ ] 文档点击、选择、排序等交互行为无回归
- [ ] 分页控制器（下一页/上一页）行为不变

---

#### 工作范围

**包含：**
- 文档列表虚拟滚动实现

**不包含：**
- 无限滚动（保留现有分页控制器）
- 审计日志列表 / 资产列表的虚拟滚动（可后续跟进）

---

#### 预估工作量

- Phase 1 读代码 + 方案确认：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| react-window 与现有表格组件（如 Table）不兼容 | 中 | 中 | Phase 1 确认组件类型；若为 Table，改用 @tanstack/react-virtual |
| 虚拟滚动破坏键盘导航 / 无障碍访问 | 低 | 低 | 可接受，当前无无障碍要求 |

---

### v0.45.10: 后端审计写入集成

**任务版本号：** v0.45.10
**优先级：** P1
**前置依赖：** 无（AuditService 已完整实现，仅需调用）

---

#### 背景与目标

**现状：**
- `AuditService.log()` 存在且可用，但仅在 `model_providers.py` 中被调用（create provider 时）
- `docs.py`、`projects.py`、`users.py` 中的 CRUD 操作无审计记录

**目标（Goal）：**
在核心 CRUD 路由中集成审计写入，覆盖以下操作：

| 路由文件 | 操作 | action 值 |
|---------|------|----------|
| `docs.py` | 创建文档 | `create_doc` |
| `docs.py` | 更新文档内容 | `update_doc` |
| `docs.py` | 回滚文档版本 | `rollback_doc` |
| `docs.py` | 删除文档 | `delete_doc` |
| `projects.py` | 创建项目 | `create_project` |
| `projects.py` | 更新项目 | `update_project` |
| `projects.py` | 删除项目 | `delete_project` |
| `users.py` | 邀请用户 | `invite_user` |
| `users.py` | 修改用户角色 | `update_user_role` |
| `users.py` | 移除用户 | `remove_user` |

> ⚠️ **Phase 1 前置确认：** 读 `docs.py` / `projects.py` / `users.py` 路由，确认：
> 1. 哪些操作有 `current_user`（有则可直接构建 AuditService）
> 2. 哪些操作无 `current_user` 依赖（可能需要添加 `get_current_user` 依赖）

---

#### 后端变更

**修改文件：**
- `services/api/app/routers/docs.py`
- `services/api/app/routers/projects.py`
- `services/api/app/routers/users.py`

**修改模式（以 docs.py 为例）：**
```python
# 在需要审计的操作末尾、db.commit() 之前调用：
audit = AuditService(db, tenant_id, current_user.id)
await audit.log("create_doc", "knowledge_doc", doc.id, project_id=project_id)
```

---

#### 验收标准

- [ ] 创建文档后，`audit_log` 表中出现 `action=create_doc` 的记录
- [ ] 删除文档后，`audit_log` 表中出现 `action=delete_doc` 的记录
- [ ] 邀请用户后，`audit_log` 表中出现 `action=invite_user` 的记录
- [ ] `audit_log` 记录的 `user_id` 与执行操作的用户一致
- [ ] `audit_log` 记录的 `tenant_id` 正确
- [ ] 审计写入失败时（DB 异常），主操作不回滚（AuditService.log 已设计为 fire-and-forget）

---

#### 工作范围

**包含：**
- `docs.py`、`projects.py`、`users.py` 审计调用集成（约 10 处）

**不包含：**
- `assets.py`、`cross_refs.py`、`graph.py` 等其他路由的审计集成（优先级较低，可后续跟进）
- 审计日志前端页面（v0.45.11）

---

#### 预估工作量

- Phase 1 读 3 个路由文件：1 小时
- Phase 2 执行（每处约 3 行，10 处）：2 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 部分路由无 current_user 依赖，需添加 | 中 | 低 | Phase 1 确认，逐一处理，不影响主功能 |

---

### v0.45.11: 前端审计日志页

**任务版本号：** v0.45.11
**优先级：** P1
**前置依赖：** v0.45.10（写入集成，否则页面为空，测试无意义）

---

#### 背景与目标

**后端现状（已有）：**
- `GET /v1/audit-logs`：分页列表，支持 `project_id` / `action` / `resource_type` 过滤，需 `tenant_admin` 角色

**目标（Goal）：**
在管理后台新增审计日志页面（`/admin/audit-logs`），仅 `tenant_admin` 可见，展示操作记录。

---

#### 前端变更

**新增文件/页面：**
- `/admin/audit-logs` 页面

**页面内容：**
- 操作日志表格（列：时间、用户、操作类型（中文）、资源类型、资源 ID、项目）
- 筛选器：操作类型（下拉）、资源类型（下拉）、项目（下拉，可选）
- 分页控制器

---

#### 验收标准

- [ ] `tenant_admin` 登录后，导航栏"管理"菜单出现"操作日志"入口
- [ ] 操作日志页展示审计记录，列表时间倒序
- [ ] 筛选操作类型为"创建文档"时，只显示相关记录
- [ ] viewer 角色访问 `/admin/audit-logs` → 重定向到 403 或首页
- [ ] 分页功能正常

---

#### 工作范围

**包含：**
- 审计日志页（新增）
- 导航菜单入口（tenant_admin 可见）

**不包含：**
- 导出审计日志 CSV（独立需求）

---

#### 预估工作量

- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 审计日志数据量大时列表加载慢 | 低 | 低 | 后端已有分页；前端使用服务端分页 |

---

### v0.45.12: 前端全局设置页

**任务版本号：** v0.45.12
**优先级：** P1
**前置依赖：** 无（后端 model-providers + model-routes CRUD 已完整）

---

#### 背景与目标

**后端现状（已有）：**
- `POST /v1/model-providers`、`GET /v1/model-providers`、`POST /v1/model-providers/test`
- `POST /v1/model-routes`、`GET /v1/model-routes`、`PATCH /v1/model-routes/{id}`、`DELETE /v1/model-routes/{id}`
- 均需 `tenant_admin` 角色（创建/修改操作）

**目标（Goal）：**
在管理后台新增全局设置页（`/admin/settings`），仅 `tenant_admin` 可访问，包含两个 Tab：模型提供商管理、路由规则配置。

---

#### 前端变更

**新增文件/页面：**
- `/admin/settings` 页面（两个 Tab：模型提供商 + 路由规则）

**Tab 1 — 模型提供商：**
- 提供商列表（名称、状态、base_url）
- "添加提供商"按钮 → Modal（provider_name、api_key_encrypted 输入、base_url 可选）
- 每行"测试连通性"按钮（调用 `POST /v1/model-providers/test`，显示成功/失败）

**Tab 2 — 路由规则：**
- 规则列表（task_type 中文标签、绑定提供商名称、model_name、优先级）
- "添加路由"按钮 → Modal（task_type 下拉、provider 下拉、model_name 文本）
- 每行"修改"按钮 → 编辑 Modal
- 每行"删除"按钮 → 确认后删除

**task_type 中文映射（参考 model_route 模型定义）：**

| task_type | 中文标签 |
|-----------|---------|
| embedding | 向量嵌入 |
| classification | 内容分类 |
| architecture | 架构生成 |
| doc_generation | 文档生成 |
| summary | 摘要生成 |
| qa | 知识问答 |

---

#### 验收标准

- [ ] `tenant_admin` 可访问 `/admin/settings`，其他角色重定向
- [ ] 可添加新的模型提供商（API Key 输入框为 password 类型）
- [ ] "测试连通性"返回成功/失败提示
- [ ] 可添加/修改/删除路由规则
- [ ] task_type 以中文标签展示

---

#### 工作范围

**包含：**
- `/admin/settings` 页面（新增）
- 导航菜单入口（tenant_admin 可见）

**不包含：**
- 其他系统配置（邮件/存储等）— 相关 API 未实现，不在本版本做

---

#### 预估工作量

- Phase 2 执行：5 小时
- Phase 3 测试：2 小时

---

### v0.45.13: AI 摘要/标签生成反思循环 — 后端自检 + 置信度评分

**任务版本号：** v0.45.13
**优先级：** P1
**前置依赖：** v0.45.5（AI 摘要 API 可用）
**WISHLIST 来源：** W-024（Shiji-KB 借鉴 — 反思循环）

---

#### 背景与目标

**现状：**
- v0.45.5 的 `generate_summary` task 调用 LLM 一次后直接写入 DB，无质量校验
- `ai-suggest-tags` task 同理，一次生成即最终结果
- pipeline `quality_check.py`（Stage 6）仅做规则校验（内容长度、标题存在），无 AI 自检

**借鉴来源：**
Shiji-KB 通过 5 轮反思循环将事件年代准确率从 90% 提升到 99.1%。核心模式：`AI 初始生成 → 自检 prompt → 对比修正 → 置信度评分`。

**目标（Goal）：**
在 `generate_summary` 和 `ai-suggest-tags` 两个 task 中引入 **一轮 AI 自检**（reflection），并为每次生成结果附加 `confidence` 置信度评分（0.0–1.0）。低于阈值的结果自动触发一次返工。

---

#### 后端变更

**修改文件：**
- `services/ai-orchestrator/orchestrator/tasks.py` — 修改 `generate_summary` 和 `ai-suggest-tags` task

**`generate_summary` task 修改逻辑（伪代码）：**
```python
# Step 1: 初始生成
raw_summary = call_llm(build_summary_prompt(content_md))

# Step 2: 自检 — 用另一个 prompt 让 LLM 评估自身输出
reflection = call_llm(build_reflection_prompt(content_md, raw_summary))
# reflection 返回 JSON: {"confidence": 0.85, "issues": ["..."], "revised_summary": "..."}
parsed = parse_json_response(reflection)

# Step 3: 决策
confidence = parsed.get("confidence", 0.5)
if confidence < 0.7 and parsed.get("revised_summary"):
    final_summary = parsed["revised_summary"]
else:
    final_summary = raw_summary

# Step 4: 写入 DB（附加 confidence）
doc.summary = final_summary
```

**新增 prompt 函数：**
- `services/ai-orchestrator/orchestrator/prompts.py` — 新增：
  - `build_reflection_prompt(original_content: str, generated_output: str) -> str`
    - 要求 LLM 评估：① 是否忠于原文（无幻觉）② 是否覆盖核心内容 ③ 是否简洁（≤200字）
    - 返回 JSON：`{"confidence": float, "issues": [str], "revised_summary": str | null}`
  - `build_tags_reflection_prompt(original_content: str, generated_tags: list[str]) -> str`
    - 要求 LLM 评估：① 标签是否准确 ② 是否遗漏关键概念 ③ 是否有冗余/模糊标签
    - 返回 JSON：`{"confidence": float, "issues": [str], "revised_tags": [str] | null}`

**数据库字段（必需）：**
- `KnowledgeDoc` 新增 `summary_confidence: float | None`（需 Alembic 迁移，建议与 v0.45.4 合并为一次迁移脚本）

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `orchestrator/prompts.py`，确认现有 prompt 构建模式
> 2. 读 `orchestrator/llm_client.py`，确认 `call_llm()` 调用方式和错误处理
> 3. 确认是否新增 DB 字段（需与 v0.45.4 迁移协调）

---

#### 验收标准

- [ ] `POST /v1/docs/{doc_id}/ai-summarize` 返回结果中包含 `confidence` 字段
- [ ] 当 LLM 自检发现问题（confidence < 0.7）时，返回的 summary 是修正后的版本
- [ ] 当 LLM 自检通过（confidence ≥ 0.7）时，返回原始生成结果
- [ ] `POST /v1/docs/{doc_id}/ai-suggest-tags` 同样包含 `confidence` 字段和自检逻辑
- [ ] 自检 prompt 失败（JSON 解析错误）时，降级为直接使用初始生成结果（不阻塞主流程）

---

#### 工作范围

**包含：**
- `orchestrator/tasks.py`（修改 2 个 task）
- `orchestrator/prompts.py`（新增 2 个 prompt 构建函数）
- Alembic 迁移新增 `summary_confidence` 字段

**不包含：**
- 多轮反思（本版本仅引入 1 轮自检，效果验证后再考虑多轮）
- pipeline Stage 6 quality_check 的 AI 化改造（v0.46 范围）

---

#### 预估工作量

- Phase 1 读 orchestrator 代码 + prompt 设计：1.5 小时
- Phase 2 执行：3 小时
- Phase 3 测试（含手动验证 LLM 输出质量）：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 自检 prompt 返回非法 JSON | 中 | 低 | `parse_json_response` 已有容错；失败时降级为原始结果 |
| 自检消耗额外 token（成本翻倍） | 确定 | 中 | 可接受：摘要/标签为低频手动触发操作，非批量自动触发 |
| LLM 自检总是给高分（自我认同偏差） | 中 | 低 | prompt 中明确要求"严格评审，列出具体问题"；后续可引入不同模型交叉检验 |

---

### v0.45.14: 前端摘要/标签置信度展示

**任务版本号：** v0.45.14
**优先级：** P2
**前置依赖：** v0.45.13（后端返回 confidence 字段）+ v0.45.6（前端摘要/标签 UI 已有）
**WISHLIST 来源：** W-024（Shiji-KB 借鉴 — 反思循环）

---

#### 背景与目标

**目标（Goal）：**
在 v0.45.6 已有的摘要区块和标签区块中，展示 AI 置信度指示器。让用户直观了解 AI 生成质量，低置信度结果提示用户手动审核或重新生成。

---

#### 前端变更

**修改文件：**
- 文档详情页（v0.45.6 新增的 Summary 区块和 Tags 区块）

**新增交互：**
- Summary 区块右上角展示置信度 badge：
  - `confidence ≥ 0.8` → 绿色 badge "AI 高置信"
  - `0.6 ≤ confidence < 0.8` → 黄色 badge "AI 中置信"
  - `confidence < 0.6` → 红色 badge "AI 低置信 — 建议人工审核"
- Tags 区块同理
- 低置信度时，"重新生成"按钮高亮提示

---

#### 验收标准

- [ ] 文档有 AI 摘要且 confidence ≥ 0.8 时，显示绿色 badge
- [ ] confidence < 0.6 时，显示红色 badge + "建议人工审核"提示
- [ ] 无 confidence 值（旧数据）时，不显示 badge（降级兼容）
- [ ] badge 不影响现有摘要/标签展示布局

---

#### 工作范围

**包含：**
- 文档详情页 Summary 区块 + Tags 区块添加置信度 badge（2 处 UI 修改）

**不包含：**
- 在文档列表页展示置信度（独立需求）
- 批量重新生成低置信度文档的操作（独立需求）

---

#### 预估工作量

- Phase 2 执行：1.5 小时
- Phase 3 测试：0.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 无 confidence 的旧数据不显示 badge | 确定 | 低 | 降级兼容：无值时不渲染 badge（已在验收标准中要求） |

---

## 第六章 Alembic 迁移注意事项

v0.45 引入 2 次数据库迁移（v0.45.4 新增 `summary` 字段，v0.45.13 新增 `summary_confidence` 字段）。执行前必须：

1. 备份 DB（或在 staging 环境先验证）
2. `alembic upgrade head` 前确认无未完成的 pending 迁移
3. 验证 `alembic downgrade -1` 可回滚
4. 生产环境迁移需独立排期，不与代码发布同一时间窗口

---

## 第七章 新增依赖说明

| 依赖 | 版本建议 | 用途 | 服务 | 需在 staging 验证 |
|------|---------|------|------|-----------------|
| `weasyprint` | ≥ 61.0 | Markdown → PDF | services/api | CJK 字体 |
| `python-docx` | ≥ 1.1.0 | Markdown → DOCX | services/api | - |
| `react-window` 或 `@tanstack/react-virtual` | latest | 虚拟滚动 | apps/web | - |

> ⚠️ 添加依赖前必须确认 `requirements.txt` / `package.json` 中尚不存在。

---

## 第八章 v0.45 与 v0.44 的边界

- v0.45 不修改 v0.44 实现的功能（RBAC、版本历史、批量导入、ASR、图谱节点合并拆分、API限流统计）
- v0.45.7/v0.45.8 与 v0.44.8/v0.44.9（图谱节点合并拆分）是独立功能：
  - v0.44.8/9 操作的是 `ArchitectureNode`（架构层）
  - v0.45.7/8 操作的是 `CrossReference`（文档关联层）
  - 两者通过不同 API，不冲突

---

## 第九章 测试要求

> 引用项目技术规范：`docs/tech-specs/testing-strategy.md`

### 9.1 测试层次

| 层次 | 工具 | 覆盖重点 |
|------|------|---------|
| 后端单元测试 | pytest | 新增 service / router / task 函数 |
| 后端集成测试 | pytest + TestClient | API 端点 + 数据库交互 |
| 前端组件测试 | vitest + React Testing Library | 新增 UI 组件渲染与交互 |
| 前端集成测试 | vitest | API 调用 mock + 页面级行为 |

### 9.2 覆盖策略

- 每个任务至少覆盖其验收标准中列出的场景
- 新增 API 端点必须有 happy path + 权限拒绝 + 参数非法 三类测试
- 纯前端任务至少覆盖渲染 + 交互 + 空状态
- AI 相关任务（v0.45.5/13）需 mock LLM 响应，测试正常 / 空响应 / 异常 三种路径

---

## 第十章 版本号管理与文档产出

### 10.1 版本号管理

> 引用项目技术规范：`docs/tech-specs/dev-governance-part1-version.md` §1.1–§1.4

- 版本号格式：`v0.45.{Z}`，Z 为任务序号（1–14）
- 每完成一个任务，VERSION 文件更新为 `0.45.{Z}`
- CHANGELOG.md 追加该任务的变更记录
- Commit message 格式：`feat|fix|refactor: 简要描述 (v0.45.{Z})`

### 10.2 文档产出要求

> 引用项目技术规范：`docs/tech-specs/dev-governance-part0-automation.md` §0.7

每个任务完成后必须同步更新：
- `VERSION`
- `CHANGELOG.md`
- `TODO_NEXT.md`
- 本计划文件中该任务的状态（Planned → Completed）

版本全部完成后必须产出：
- `docs/versions/phase-report-v0.45.md`（版本总结报告）
- `docs/versions/seal-audit-v0.45.md`（封板审计报告）

---

## 第十一章 任务汇报格式

每个 `vX.Y.Z` 任务完成后，按以下 9 项结构报告：

1. **计划 / 当前迭代目标**（目标 + 最小闭环 + 排除范围）
2. **文件变更清单**（路径 | 新增/修改/删除 | 职责描述）
3. **用户可见能力**（用户现在可以做什么）
4. **真实场景验证**（至少 5 个场景，每个含明确验证点）
5. **开放问题**（高/中/低优先级）
6. **收尾说明**（是否闭环 + 残留风险）
7. **版本状态更新**（VERSION / CHANGELOG / TODO_NEXT.md）
8. **commit 信息**
9. **是否继续下一个任务**

---

## 第十二章 新增数据库表汇总

v0.45 不新增独立表，仅对已有表新增字段：

| 任务 | 表名 | 变更类型 | 字段 | 类型 | 约束 | 说明 |
|------|------|---------|------|------|------|------|
| v0.45.4 | `knowledge_doc` | 新增字段 | `summary` | TEXT | nullable | AI 生成的文档摘要 |
| v0.45.13 | `knowledge_doc` | 新增字段 | `summary_confidence` | FLOAT | nullable | AI 摘要置信度（0.0–1.0） |

合计：0 张新表，2 个新增字段，2 次 Alembic 迁移。

---

## 第十三章 开始前必须先输出

Agent 在进入 Phase 2 编码之前，必须先输出以下三项内容：

1. **当前代码现状理解** — 列出与第一个任务相关的已有文件、函数、API 端点现状
2. **第一个任务的实施计划** — 按 `docs/tech-specs/dev-governance-part3-guides.md` §3.1 模板输出
3. **第一个任务的预计修改文件清单** — 明确新增 / 修改 / 不动的文件

**在这三项输出并经确认之前，不要开始写代码。**

---

## 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 计划周期 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|--------|----------|--------|------|
| v0.45.1 | 前端搜索页切换到混合检索 | — | 2026-03-31 | 0 | Done（已实现，跳过） |
| v0.45.2 | 后端 PDF / DOCX 导出扩展 | — | — | 0 | Planned |
| v0.45.3 | 前端导出格式选择器 | — | — | 0 | Planned |
| v0.45.4 | AI 摘要 DB 迁移 | — | 2026-03-31 | 1 | Done |
| v0.45.5 | AI 摘要后端 API + orchestrator 任务 | — | 2026-03-31 | 1 | Done |
| v0.45.6 | 前端文档详情页摘要 + 标签展示 | — | — | 0 | Planned |
| v0.45.7 | 前端文档详情页跨文档关联面板 | — | — | 0 | Planned |
| v0.45.8 | 前端图谱页关系编辑操作 | — | — | 0 | Planned |
| v0.45.9 | 前端文档列表虚拟滚动 | — | — | 0 | Planned |
| v0.45.10 | 后端审计写入集成 | — | — | 0 | Planned |
| v0.45.11 | 前端审计日志页 | — | — | 0 | Planned |
| v0.45.12 | 前端全局设置页 | — | — | 0 | Planned |
| v0.45.13 | AI 反思循环 — 后端自检 + 置信度 | — | — | 0 | Planned |
| v0.45.14 | 前端摘要/标签置信度展示 | — | — | 0 | Planned |

**Phase 封板记录：**

| 功能项 | 包含任务 | 封板日期 | 封板版本号 | 回归测试结果 |
|-------|--------|--------|----------|-----------|
| v0.45 输出接口质量提升 + 图谱可维护性 + 运营可见性 | v0.45.1–v0.45.14 | — | — | — |

---

## 第十五章 变更记录

| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-28 | V1.0 初始版本，基于代码核实编写 | 产品 Owner |
| 2026-03-30 | 追加 v0.45.13–v0.45.14（Shiji-KB 反思循环借鉴） | 产品 Owner |
| 2026-03-31 | 补齐缺失章节（测试/版本号/文档产出/状态追踪/变更记录/决策/风险），修复章节编号 | 产品 Owner |

---

## 第十六章 决策与假设

**关键决策：**
- PDF 导出使用 `weasyprint`（HTML→PDF 路线），而非 `reportlab`（纯 Python）— 原因：weasyprint 对 Markdown→HTML→PDF 链路更自然，CJK 支持更好
- AI 反思循环（v0.45.13）仅引入 1 轮自检，不做多轮 — 原因：先验证单轮效果，多轮成本翻倍且收益不确定
- `summary_confidence` 作为独立 DB 字段而非存入 JSONB — 原因：v0.45.14 前端需直接查询和展示，独立字段更便于排序和过滤

**重要假设：**
- v0.44 全部完成后才启动 v0.45（基线为 v0.44.16）
- LLM 摘要 prompt 在 200 字限制下产出质量可接受
- weasyprint 在 Docker 容器中可正常运行（需安装 CJK 字体）

---

## 第十七章 版本级风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| weasyprint Docker 兼容性问题（字体/渲染） | 中 | 中 | v0.45.2 Phase 1 先在容器中验证 weasyprint 可用性 |
| LLM 反思循环自检质量不稳定（自我认同偏差） | 中 | 低 | prompt 明确要求严格评审；后续可引入交叉模型检验 |
| 14 个任务总量较大，可能延期 | 中 | 中 | 严格按依赖顺序执行，P2 任务（v0.45.9/14）可延后 |
| 前端虚拟滚动与现有表格组件冲突 | 低 | 中 | Phase 1 确认现有组件兼容性，必要时降级为优化分页 |
| AI orchestrator 与 API service 共享 DB 的并发问题 | 低 | 高 | 参考现有 `_get_sync_session()` 模式，每个 task 独立 session |
