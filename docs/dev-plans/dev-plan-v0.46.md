# KB Platform v0.46 版本开发任务计划

**文档编号**: PLAN-2026-03-30-v046
**版本**: V1.0（初始版）
**日期**: 2026-03-30
**基线 commit**: 待 v0.45 完成后更新
**基线分支**: main
**依据**: 产品北极星 + WISHLIST W-025/W-026 + 竞品分析（shiji-kb 借鉴）
**作者**: 产品 Owner

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.45 完成后的现有代码增量增强。禁止重构无关模块、禁止重写已有业务逻辑、禁止变更已有 API 契约（除非本计划明确要求）。

### 1.2 继承已有能力

以下能力需在 v0.46 启动前代码核实（待 v0.45 完成后更新）：

- **Pipeline Worker**（`services/pipeline-worker/`）— 7 阶段 pipeline，Stage 6 `quality_check.py` 做规则校验
- **AI Orchestrator**（`services/ai-orchestrator/`）— `call_llm()` + `parse_json_response()` 基础设施
- **v0.45.5 AI 摘要 API** — `POST /v1/docs/{doc_id}/ai-summarize` + `ai-suggest-tags`
- **v0.45.13 反思循环** — `build_reflection_prompt()` + confidence 评分机制
- **CrossReference CRUD** — 完整的跨文档关联 API（5 个端点）+ `auto-suggest`
- **KnowledgeDoc** — `summary`、`keywords`（JSONB）、`summary_confidence` 字段
- **Pipeline stages 目录** — `services/pipeline-worker/worker/stages/`，每个 stage 为独立 Python 模块

### 1.3 最小改动原则

每个任务只改必须改的文件。如果发现无关问题，记录到衍生建议但不执行。

### 1.4 任务领取规则

每次只能领取一个任务。完成后按第九章格式汇报，确认后再领下一个。

---

## 第二章 当前阶段事实

### 2.1 版本主题

**v0.46：知识工程质量提升 — Pipeline 配置化 + 跨文档知识推理**

> 借鉴 Shiji-KB 项目的两大核心方法论：① SKILL 系统（方法论即配置），② 四层语义模型的第三层（知识语义：矛盾检测、模式发现）。

### 2.2 Gap 分析

| WISHLIST | 需求 | 后端 Gap | 前端 Gap |
|---------|------|---------|---------|
| W-025 | Pipeline stage 配置化 | **有**：stages 为硬编码 Python 模块，用户无法自定义提取规则 | **有**：无 pipeline 配置 UI |
| W-026 | 跨文档知识推理 | **有**：无矛盾检测逻辑、无模式发现 API | **有**：图谱页无矛盾/模式展示 |

---

## 第三章 本轮目标与边界

### 3.1 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | WISHLIST 来源 |
|----------|--------|------|------|------------|
| v0.46.1 | Pipeline stage 配置 DB 模型 + CRUD API | P1 | Planned | W-025 |
| v0.46.2 | Pipeline stage 运行时加载用户配置 | P1 | Planned | W-025 |
| v0.46.3 | 用户自定义实体类型支持 | P1 | Planned | W-025 |
| v0.46.4 | 前端 Pipeline 配置页 | P1 | Planned | W-025 |
| v0.46.5 | 跨文档矛盾检测 — 后端 API + AI task | P1 | Planned | W-026 |
| v0.46.6 | 跨文档模式发现 — 后端 API + AI task | P1 | Planned | W-026 |
| v0.46.7 | 前端图谱页矛盾/模式展示 | P1 | Planned | W-026 |

### 3.2 北极星三问校验

| 任务 | Q1 强化输入→整合→图谱核心链路？ | Q2 强化输入/输出接口？ | Q3 是核心链路的必要支撑？ | 结论 |
|-----|--------------------------|---------------------|----------------------|------|
| v0.46.1 | ✅ 整合端（用户可配置知识提取） | - | - | ✅ 通过 |
| v0.46.2 | ✅ 整合端（pipeline 按配置执行） | - | - | ✅ 通过 |
| v0.46.3 | ✅ 整合端（自定义实体丰富图谱） | - | - | ✅ 通过 |
| v0.46.4 | - | - | ✅ 配置化基础设施体验 | ✅ 通过 |
| v0.46.5 | ✅ 图谱端质量（矛盾检测强化图谱可信度） | - | - | ✅ 通过 |
| v0.46.6 | ✅ 图谱端深度（模式发现是知识语义第三层） | - | - | ✅ 通过 |
| v0.46.7 | - | ✅ 输出接口（用户可感知跨文档洞察） | - | ✅ 通过 |

### 3.3 明确不做的事项

- Pipeline 可视化编排器（拖拽式 DAG 编辑）— 过度设计，v0.46 仅做配置表单
- 多轮反思循环的可配置化 — v0.45.13 引入单轮反思，v0.46 不扩展轮数
- 知识语义第四层（应用语义：推理引擎）— 超出当前阶段
- Neo4j / 图数据库迁移 — 当前 PostgreSQL + CrossReference 满足需求

---

## 第四章 优先级与执行顺序

```
W-025（Pipeline 配置化）：
v0.46.1 → v0.46.2 → v0.46.3 → v0.46.4
← 严格顺序：先建模型，再改运行时，再支持自定义实体，最后做 UI

W-026（跨文档知识推理）：
v0.46.5 → v0.46.6 → v0.46.7
← v0.46.5/6 可并行但建议顺序推进，v0.46.7 依赖两者
```

建议执行顺序：

```
v0.46.1 → v0.46.2 → v0.46.3 → v0.46.5 → v0.46.6
→ v0.46.4 → v0.46.7
```

---

## 第五章 各任务详细定义

---

### v0.46.1: Pipeline stage 配置 DB 模型 + CRUD API

**任务版本号：** v0.46.1
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**现状：**
- Pipeline 的 7 个 stage 定义在 `services/pipeline-worker/worker/tasks.py` 的 `STAGES` 列表中，硬编码
- 每个 stage 的参数（如 `quality_check` 的 `MIN_CONTENT_LENGTH = 50`）在代码中写死
- 用户无法配置"跳过某个 stage"或"调整 stage 参数"

**目标（Goal）：**
新增 `pipeline_stage_config` 表，存储每个项目的 pipeline stage 配置；提供 CRUD API 供前端管理。

---

#### 后端变更

**新增文件：**
- `packages/shared-models/shared_models/pipeline_config.py` — 新模型：
  ```python
  class PipelineStageConfig(Base):
      __tablename__ = "pipeline_stage_config"

      id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
      project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project.id"), nullable=False)
      stage_name: Mapped[str] = mapped_column(String(50), nullable=False)  # "classify" | "quality_check" | ...
      enabled: Mapped[bool] = mapped_column(default=True)
      params: Mapped[dict] = mapped_column(JSONB, default=dict)  # stage 特有参数
      created_at: Mapped[datetime] = mapped_column(default=func.now())
      updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

      # 联合唯一：每个项目每个 stage 只有一条配置
      __table_args__ = (UniqueConstraint("project_id", "stage_name"),)
  ```

- `services/api/app/routers/pipeline_config.py` — 新 router：
  ```
  GET /v1/projects/{project_id}/pipeline-config         ← 获取项目 pipeline 配置（返回 7 个 stage 的配置，未配置的返回默认值）
  PUT /v1/projects/{project_id}/pipeline-config/{stage}  ← 更新某 stage 配置（enabled, params）
  POST /v1/projects/{project_id}/pipeline-config/reset   ← 重置为默认配置
  ```

- Alembic 迁移：`create_pipeline_stage_config_table`

**修改文件：**
- `packages/shared-models/shared_models/__init__.py` — 导出 `PipelineStageConfig`
- `services/api/app/main.py` — 注册 `pipeline_config` router

**默认 stage 参数定义：**
```python
DEFAULT_STAGE_PARAMS = {
    "classify": {"confidence_threshold": 0.7},
    "architecture_draft": {},
    "doc_generate": {"max_length": 5000},
    "quality_check": {"min_content_length": 50, "require_title": True},
    "conflict_detect": {"similarity_threshold": 0.85},
    "embed": {"model": "default"},
    "review_notify": {},
}
```

---

#### API 契约

```
GET /v1/projects/{project_id}/pipeline-config
认证：JWT，viewer+
Response 200：
{
  "data": {
    "stages": [
      {"stage_name": "classify", "enabled": true, "params": {"confidence_threshold": 0.7}},
      {"stage_name": "quality_check", "enabled": true, "params": {"min_content_length": 50, "require_title": true}},
      ...
    ]
  }
}

PUT /v1/projects/{project_id}/pipeline-config/quality_check
认证：JWT，editor+
Body：{"enabled": true, "params": {"min_content_length": 100}}
Response 200：{"data": {"stage_name": "quality_check", "enabled": true, "params": {...}}}
```

---

#### 验收标准

- [ ] `GET /v1/projects/{pid}/pipeline-config` 返回 7 个 stage 的配置（含默认值）
- [ ] `PUT` 更新某 stage 的 `enabled` 和 `params` 后，再次 GET 返回更新后的值
- [ ] `POST .../reset` 后，所有配置恢复默认
- [ ] 新建项目时无 config 记录 → GET 返回默认值（不报错）
- [ ] `stage_name` 非法值 → 404

---

#### 工作范围

**包含：**
- DB 模型 + Alembic 迁移
- CRUD API（3 个端点）
- 默认参数定义

**不包含：**
- Pipeline 运行时读取配置（v0.46.2）
- 前端 UI（v0.46.4）

---

#### 预估工作量

- Phase 1 读 pipeline 代码确认 stage 参数：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

### v0.46.2: Pipeline stage 运行时加载用户配置

**任务版本号：** v0.46.2
**优先级：** P1
**前置依赖：** v0.46.1（`PipelineStageConfig` 模型和 API 存在）

---

#### 背景与目标

**目标（Goal）：**
修改 `pipeline-worker` 的 `run_pipeline` task，使其在执行每个 stage 前读取项目的 `PipelineStageConfig`，根据 `enabled` 决定是否跳过，根据 `params` 传入 stage 函数。

---

#### 后端变更

**修改文件：**
- `services/pipeline-worker/worker/tasks.py` — `run_pipeline` task：
  - 在执行 stage 前查询 `PipelineStageConfig`
  - `enabled == False` → 跳过该 stage（记日志）
  - `params` 传入 stage 函数（需修改各 stage 函数签名，接受 `**kwargs` 或 `config: dict` 参数）

- `services/pipeline-worker/worker/stages/quality_check.py` — 修改函数签名：
  ```python
  def quality_check(db: Session, doc_ids: list[uuid.UUID], config: dict | None = None) -> dict:
      min_length = (config or {}).get("min_content_length", MIN_CONTENT_LENGTH)
      require_title = (config or {}).get("require_title", True)
      ...
  ```

- 其他 stage 文件同理：函数签名新增 `config: dict | None = None`，用 `.get()` 读取参数，未配置时使用原有默认值

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `run_pipeline` task 的完整逻辑，确认 stage 调用方式
> 2. 读每个 stage 函数签名，规划 config 参数注入方式
> 3. 确认 pipeline-worker 能访问 DB（已有 `sync_session_factory`）

---

#### 验收标准

- [ ] 项目 pipeline config 中 `quality_check.enabled = false` → 执行 pipeline 时跳过 quality_check stage
- [ ] `quality_check.params.min_content_length = 100` → 内容 60 字的文档被 flagged（默认 50 不会被 flagged）
- [ ] 未配置 pipeline config 的项目 → 所有 stage 使用默认参数执行（行为不变）
- [ ] Stage 跳过时，job 进度事件中标记该 stage 为 `skipped`

---

#### 工作范围

**包含：**
- `tasks.py` 加载配置逻辑
- 各 stage 函数签名扩展（`config` 参数）
- `quality_check.py` 参数化改造（作为示范，其他 stage 参数有限，改动小）

**不包含：**
- 新增 stage 类型（用户创建自定义 stage 脚本 — 超出范围）
- Pipeline DAG 编排（stage 顺序固定，不支持重排）

---

#### 预估工作量

- Phase 1 读 pipeline 完整流程：1.5 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 跳过关键 stage（如 embed）导致后续功能异常 | 中 | 中 | UI 中对 embed 等核心 stage 标记"建议不跳过"提示 |
| Config 读取增加 pipeline 执行耗时 | 低 | 低 | 单次 DB 查询，可忽略 |

---

### v0.46.3: 用户自定义实体类型支持

**任务版本号：** v0.46.3
**优先级：** P1
**前置依赖：** v0.46.2（pipeline 运行时可读取 config params）

---

#### 背景与目标

**现状：**
- AI orchestrator 的 `build_classify_prompt` 和 `build_generate_doc_prompt` 中硬编码了实体分类逻辑
- 用户无法告诉系统"我的知识库中关注的实体类型是人名、地名、专有名词..."

**借鉴来源：**
Shiji-KB 定义了 18 类实体（人名/地名/官职/时间/朝代...），每类有独立的 vocabulary 表。核心思想：**实体类型应由领域决定，而非系统硬编码**。

**目标（Goal）：**
在 `PipelineStageConfig` 的 `classify` stage 和 `doc_generate` stage 的 `params` 中支持 `entity_types` 字段，允许用户定义项目级的实体类型列表。AI prompt 中动态插入这些实体类型。

---

#### 后端变更

**修改文件：**
- `services/ai-orchestrator/orchestrator/prompts.py` — 修改以下 prompt 构建函数：
  - `build_classify_prompt()` — 接受 `entity_types: list[str] | None` 参数，若提供则在 prompt 中列出用户定义的实体类型作为分类指引
  - `build_generate_doc_prompt()` — 同理，在文档生成 prompt 中引导 LLM 关注用户定义的实体类型

- `services/ai-orchestrator/orchestrator/tasks.py` — `generate_docs` task 中读取项目的 pipeline config，提取 `entity_types` 传入 prompt

**params 格式示例：**
```json
{
  "classify": {
    "confidence_threshold": 0.7,
    "entity_types": ["人名", "地名", "组织", "时间", "概念"]
  },
  "doc_generate": {
    "max_length": 5000,
    "entity_types": ["人名", "地名", "组织", "时间", "概念"]
  }
}
```

**默认值：** 不提供 `entity_types` 时，prompt 行为与当前完全一致（不限定实体类型，由 LLM 自行判断）。

---

#### 验收标准

- [ ] 项目 pipeline config 中设置 `entity_types: ["投资机构", "创始人", "融资轮次"]` → AI 生成文档时 keywords 中出现这些类型的标签
- [ ] 未设置 `entity_types` → 行为与 v0.45 完全一致（不回归）
- [ ] `entity_types` 列表为空 `[]` → 等价于未设置（使用默认行为）
- [ ] `entity_types` 中的类型在 AI 摘要和标签建议中也被参考

---

#### 工作范围

**包含：**
- `prompts.py` prompt 模板修改（动态插入 entity_types）
- `tasks.py` 读取 config 并传递参数

**不包含：**
- 实体类型的 CRUD 管理（entity_types 作为 params 字段的值，通过 v0.46.1 的 PUT API 管理）
- NER 模型训练（依赖 LLM prompt 工程，不引入额外模型）
- 实体字典/同义词表（独立需求，超出范围）

---

#### 预估工作量

- Phase 1 读 prompt 模板 + classify 逻辑：1 小时
- Phase 2 执行：2.5 小时
- Phase 3 测试（需实际 LLM 调用验证）：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM 未按 entity_types 指引生成标签 | 中 | 低 | prompt 中强调"必须优先使用用户定义的实体类型"；未设置时行为不变 |
| entity_types 过多时 prompt 超长 | 低 | 低 | 限制 entity_types 最大 20 个 |

---

### v0.46.4: 前端 Pipeline 配置页

**任务版本号：** v0.46.4
**优先级：** P1
**前置依赖：** v0.46.1（API 可用）+ v0.46.3（entity_types 参数存在）

---

#### 背景与目标

**目标（Goal）：**
在项目设置中新增"知识提取配置"页签，允许 editor+ 配置 pipeline 的各 stage 参数（启用/禁用、参数调整、自定义实体类型）。

---

#### 前端变更

**新增文件/页面：**
- 项目设置页新增 Tab："知识提取配置"

**页面内容：**
- 7 个 stage 卡片，每个卡片包含：
  - Stage 名称（中文标签）+ 启用/禁用开关
  - 参数表单（根据 stage 不同展示不同字段）：
    - `classify`：置信度阈值（slider 0.0–1.0）+ 自定义实体类型（tag input，可添加/删除）
    - `quality_check`：最小内容长度（数字输入）+ 要求标题（checkbox）
    - `conflict_detect`：相似度阈值（slider 0.0–1.0）
    - 其他 stage：仅启用/禁用开关（params 为空或无用户可配字段）
- "重置为默认"按钮（调用 `POST .../reset`）
- 保存按钮（调用 `PUT` 逐 stage 更新）

**stage 中文映射：**

| stage_name | 中文标签 | 用户描述 |
|-----------|---------|---------|
| classify | 内容分类 | 将原始片段分类为新增/补充/修正/冲突 |
| architecture_draft | 架构生成 | AI 自动生成知识体系架构 |
| doc_generate | 文档生成 | AI 将片段整合为结构化知识文档 |
| quality_check | 质量检查 | 校验生成内容的基本质量 |
| conflict_detect | 冲突检测 | 检测跨文档的内容冲突 |
| embed | 向量嵌入 | 生成语义向量用于检索 |
| review_notify | 审核通知 | 通知审核者新生成的内容 |

---

#### 验收标准

- [ ] 项目设置页展示"知识提取配置"Tab（editor+ 可见）
- [ ] 可切换 stage 启用/禁用，保存后再次加载状态正确
- [ ] `classify` stage 可添加/删除自定义实体类型标签
- [ ] `quality_check` stage 可调整最小内容长度参数
- [ ] viewer 角色下配置为只读（开关和输入 disabled）
- [ ] "重置为默认"后所有 stage 恢复默认配置

---

#### 工作范围

**包含：**
- 项目设置页新增 Tab
- 7 个 stage 配置卡片

**不包含：**
- Pipeline 执行历史（独立需求）
- Pipeline 实时进度展示（W-007，未排期）

---

#### 预估工作量

- Phase 1 读项目设置页结构：1 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 7 个 stage 卡片 UI 复杂度高 | 中 | 中 | 先实现通用开关 + 参数表单框架，各 stage 用同一组件渲染 |
| 用户误禁用 embed stage 导致搜索失效 | 中 | 中 | UI 中对 embed/doc_generate 标注"核心 stage，建议不禁用" |

---

### v0.46.5: 跨文档矛盾检测 — 后端 API + AI task

**任务版本号：** v0.46.5
**优先级：** P1
**前置依赖：** 无（依赖 v0.45 完成后的 CrossReference + AI orchestrator）

---

#### 背景与目标

**现状：**
- `CrossReference` 关系类型中已有 `contradicts`（矛盾），但无自动检测逻辑
- Pipeline Stage 5（conflict_detect）做的是 chunk 级重复检测（基于 embedding 相似度），不是知识级矛盾检测

**借鉴来源：**
Shiji-KB 的矛盾分析系统可以检测跨章节的数据不一致（如长平之战中数字矛盾、秦始皇无皇后的缺失记录）。核心方法：① 提取可验证事实（数字、时间、因果关系），② 跨文档交叉比对，③ 标记不一致。

**目标（Goal）：**
新增 `POST /v1/projects/{project_id}/ai-detect-contradictions` 端点，触发 AI 对项目内所有已发布文档进行跨文档矛盾检测，检测结果自动创建 `contradicts` 类型的 `CrossReference` 记录。

---

#### 后端变更

**新增文件：**
- `services/api/app/routers/ai_actions.py` — 新增端点（在 v0.45.5 已创建的文件中追加）：
  ```
  POST /v1/projects/{project_id}/ai-detect-contradictions
  ```

- `services/ai-orchestrator/orchestrator/tasks.py` — 新增 task：
  ```python
  @celery_app.task(name="orchestrator.detect_contradictions")
  def detect_contradictions(project_id: str, job_id: str) -> dict:
  ```

**detect_contradictions task 逻辑：**
1. 加载项目所有 `published` 状态的 `KnowledgeDoc`（取 `summary` + `keywords` + `content_md[:500]`）
2. 按文档两两组合（或使用 embedding 相似度筛选出 Top-N 最相关文档对）
3. 对每对相关文档，构建矛盾检测 prompt：
   - 提取可验证事实（数字、时间、因果声明）
   - 比对两篇文档的事实是否存在不一致
4. LLM 返回 JSON：`{"contradictions": [{"doc_a_id": ..., "doc_b_id": ..., "description": ..., "severity": "high|medium|low", "evidence_a": "...", "evidence_b": "..."}]}`
5. 对每条矛盾，自动创建 `CrossReference`（`relation_type="contradicts"`，`note` 存入描述和证据）
6. 返回检测结果摘要

**新增 prompt 函数：**
- `orchestrator/prompts.py` — `build_contradiction_prompt(doc_a_summary: str, doc_a_content: str, doc_b_summary: str, doc_b_content: str) -> str`

---

#### API 契约

```
POST /v1/projects/{project_id}/ai-detect-contradictions
认证：JWT，editor+
Body：无（或 {"max_pairs": 50} 可选限制比对数量）
Response 200：
{
  "data": {
    "total_pairs_checked": 45,
    "contradictions_found": 3,
    "cross_refs_created": [
      {"ref_id": "...", "doc_a": "...", "doc_b": "...", "description": "..."}
    ]
  }
}
```

---

#### 验收标准

- [ ] 调用后返回检测结果，包含矛盾数量和详情
- [ ] 检测到的矛盾自动创建 `CrossReference`（`relation_type="contradicts"`）
- [ ] 矛盾的 `note` 字段包含具体证据引用
- [ ] 项目文档数 < 2 时返回空结果（无报错）
- [ ] 文档数量大时（> 50 篇），使用 embedding 相似度预筛选而非全量两两比对

---

#### 工作范围

**包含：**
- AI 矛盾检测 API 端点
- Celery task + prompt
- 自动创建 CrossReference 记录

**不包含：**
- 矛盾解决工作流（人工确认/忽略 — 独立需求）
- 实时矛盾检测（每次文档更新自动触发 — 性能考量，独立需求）

---

#### 预估工作量

- Phase 1 读 CrossReference 模型 + embedding 查询方式：1.5 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 文档对数量爆炸（N*(N-1)/2） | 中 | 高 | 先用 embedding 相似度 Top-K 筛选，限制 max_pairs |
| LLM 幻觉导致误报（检测到不存在的矛盾） | 中 | 中 | 矛盾记录标记为"AI 建议"，需人工确认 |
| Token 消耗大 | 确定 | 中 | 使用 summary + content 前 500 字而非全文 |

---

### v0.46.6: 跨文档模式发现 — 后端 API + AI task

**任务版本号：** v0.46.6
**优先级：** P1
**前置依赖：** 无（与 v0.46.5 独立，但建议顺序执行以复用 prompt 模式）

---

#### 背景与目标

**借鉴来源：**
Shiji-KB 在跨章节分析中发现 20+ 非显而易见的洞察（如秦始皇无皇后记录、战争数字规律性夸大等）。核心方法：对大量文档的 keywords/summary 做聚类分析 → 提取重复出现的模式。

**目标（Goal）：**
新增 `POST /v1/projects/{project_id}/ai-discover-patterns` 端点，对项目知识库进行跨文档模式发现，返回主题聚类、高频关联和知识缺口。

---

#### 后端变更

**新增端点：**
- `services/api/app/routers/ai_actions.py` — 新增：
  ```
  POST /v1/projects/{project_id}/ai-discover-patterns
  ```

**新增 Celery task：**
- `orchestrator.discover_patterns`

**discover_patterns task 逻辑：**
1. 加载项目所有文档的 `keywords` + `summary`（轻量数据，不加载 content_md 全文）
2. 构建分析 prompt，要求 LLM：
   - 识别 **主题聚类**：哪些文档属于同一主题群？
   - 识别 **高频关联**：哪些关键词/实体频繁共现？
   - 识别 **知识缺口**：文档集合中是否有明显缺失的知识领域？
3. LLM 返回 JSON：
   ```json
   {
     "clusters": [{"theme": "...", "doc_ids": [...], "keywords": [...]}],
     "frequent_associations": [{"entity_a": "...", "entity_b": "...", "co_occurrence": 5}],
     "knowledge_gaps": ["缺少关于X的文档", "Y和Z之间的关系未被记录"]
   }
   ```
4. 结果存入项目级缓存（Redis，TTL 24h）或新建 `project_insights` 表

**新增 prompt 函数：**
- `orchestrator/prompts.py` — `build_pattern_discovery_prompt(doc_summaries: list[dict]) -> str`

---

#### API 契约

```
POST /v1/projects/{project_id}/ai-discover-patterns
认证：JWT，editor+
Body：无
Response 200：
{
  "data": {
    "clusters": [...],
    "frequent_associations": [...],
    "knowledge_gaps": [...],
    "analyzed_docs_count": 42
  }
}
```

---

#### 验收标准

- [ ] 调用后返回主题聚类结果，每个 cluster 包含文档 ID 列表
- [ ] 高频关联列表反映了文档中关键词的共现关系
- [ ] 知识缺口建议可读且有参考价值（非通用套话）
- [ ] 项目文档数 < 5 时仍能返回结果（降级为简化分析）
- [ ] 结果缓存到 Redis，24h 内重复调用直接返回缓存

---

#### 工作范围

**包含：**
- AI 模式发现 API 端点
- Celery task + prompt
- Redis 缓存结果

**不包含：**
- 持久化存储（不建 insights 表，先用 Redis 缓存验证需求）
- 自动触发（不在 pipeline 中自动执行，仅手动触发）

---

#### 预估工作量

- Phase 1 读文档数据结构 + 设计 prompt：1.5 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

### v0.46.7: 前端图谱页矛盾/模式展示

**任务版本号：** v0.46.7
**优先级：** P1
**前置依赖：** v0.46.5 + v0.46.6（矛盾检测和模式发现 API 可用）

---

#### 背景与目标

**目标（Goal）：**
在图谱可视化页面和项目仪表盘中展示 AI 发现的矛盾和模式洞察，使知识库的深层关系可视化。

---

#### 前端变更

**修改文件：**
- 图谱页 + 项目仪表盘（Phase 1 确认具体路径）

**新增功能 — 图谱页：**
- 矛盾关系（`contradicts` 类型的 CrossReference）以红色虚线边展示（区别于普通蓝色实线边）
- 鼠标悬停矛盾边 → tooltip 展示矛盾描述和证据摘要
- 图谱工具栏新增"检测矛盾"按钮 → 调用 `POST .../ai-detect-contradictions`，完成后刷新图谱

**新增功能 — 项目仪表盘（新增"知识洞察"卡片）：**
- "发现模式"按钮 → 调用 `POST .../ai-discover-patterns`
- 展示结果：
  - 主题聚类列表（每个 cluster 显示主题名 + 文档数 + 关键词标签）
  - 高频关联列表（entity_a ↔ entity_b，共现次数）
  - 知识缺口列表（文字提示）
- 展示矛盾统计（当前项目中 `contradicts` 类型的 CrossReference 数量）

---

#### 验收标准

- [ ] 图谱页中矛盾边以红色虚线展示，与普通边视觉区分明确
- [ ] 悬停矛盾边显示矛盾描述
- [ ] "检测矛盾"按钮调用 API 后图谱刷新，新发现的矛盾边出现
- [ ] 项目仪表盘"知识洞察"卡片展示聚类 + 关联 + 缺口
- [ ] "发现模式"调用中展示 loading 状态，结果缓存后再次点击即时展示
- [ ] viewer 角色下"检测矛盾"和"发现模式"按钮不可见

---

#### 工作范围

**包含：**
- 图谱页矛盾边渲染 + 工具栏按钮
- 项目仪表盘"知识洞察"卡片

**不包含：**
- 矛盾解决工作流 UI（标记矛盾为"已解决"— 独立需求）
- 聚类可视化（如气泡图）— 独立需求，v0.46 用列表展示

---

#### 预估工作量

- Phase 1 读图谱页 + 仪表盘结构：1.5 小时
- Phase 2 执行：6 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 图谱库对矛盾边（红色虚线）的样式支持有限 | 中 | 中 | Phase 1 确认图谱库 API，退而求其次用不同颜色实线 |
| 知识洞察卡片数据量大时渲染慢 | 低 | 低 | 限制展示 Top 5 cluster + Top 10 关联 |
| 矛盾检测和模式发现 API 响应慢 | 中 | 低 | 异步触发 + loading 状态，结果缓存后即时展示 |

---

## 第六章 Alembic 迁移注意事项

v0.46 引入 1 次数据库迁移（v0.46.1 `pipeline_stage_config` 表）。执行前必须：

1. 备份 DB（或在 staging 环境先验证）
2. `alembic upgrade head` 前确认无未完成的 pending 迁移
3. 验证 `alembic downgrade -1` 可回滚

---

## 第七章 新增依赖说明

v0.46 **不引入新外部依赖**。所有功能基于已有的 SQLAlchemy + Celery + Redis + LLM client 实现。

---

## 第八章 v0.46 与 v0.45 的边界

- v0.46 不修改 v0.45 实现的功能（混合检索 UI、导出格式、AI 摘要 + 反思循环、关联面板、审计日志、全局设置）
- v0.46.5 矛盾检测创建的 `CrossReference` 与 v0.45.7/8 手动创建的 `CrossReference` 使用同一模型和 API，不冲突
- v0.46.2 修改的 stage 函数签名向后兼容（新增 `config: dict | None = None` 参数，默认值不改变行为）

---

## 第九章 任务汇报格式

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

## 第十章 测试要求

> 引用项目技术规范：`docs/tech-specs/testing-strategy.md`

### 10.1 测试层次

| 层次 | 工具 | 覆盖重点 |
|------|------|---------|
| 后端单元测试 | pytest | 新增 DB 模型 / service / task 函数 |
| 后端集成测试 | pytest + TestClient | API 端点（pipeline-config CRUD、矛盾检测、模式发现） |
| 前端组件测试 | vitest + React Testing Library | Pipeline 配置页、图谱矛盾渲染、知识洞察卡片 |
| 前端集成测试 | vitest | API 调用 mock + 页面级行为 |

### 10.2 覆盖策略

- 新增 API 端点必须有 happy path + 权限拒绝 + 参数非法 三类测试
- AI 相关任务（v0.46.5/6）需 mock LLM 响应，测试正常 / 空响应 / 异常 三种路径
- Pipeline 配置改动（v0.46.2）需测试：有配置 / 无配置（默认值）/ 部分配置 三种场景
- 前端新增页面至少覆盖渲染 + 交互 + 空状态 + 权限控制

---

## 第十一章 版本号管理与文档产出

### 11.1 版本号管理

> 引用项目技术规范：`docs/tech-specs/dev-governance-part1-version.md` §1.1–§1.4

- 版本号格式：`v0.46.{Z}`，Z 为任务序号（1–7）
- 每完成一个任务，VERSION 文件更新为 `0.46.{Z}`
- CHANGELOG.md 追加该任务的变更记录
- Commit message 格式：`feat|fix|refactor: 简要描述 (v0.46.{Z})`

### 11.2 文档产出要求

> 引用项目技术规范：`docs/tech-specs/dev-governance-part0-automation.md` §0.7

每个任务完成后必须同步更新：
- `VERSION`
- `CHANGELOG.md`
- `TODO_NEXT.md`
- 本计划文件中该任务的状态（Planned → Completed）

版本全部完成后必须产出：
- `docs/versions/phase-report-v0.46.md`（版本总结报告）
- `docs/versions/seal-audit-v0.46.md`（封板审计报告）

---

## 第十二章 新增数据库表汇总

| 任务 | 表名 | 变更类型 | 字段 | 类型 | 约束 | 说明 |
|------|------|---------|------|------|------|------|
| v0.46.1 | `pipeline_stage_config` | **新增表** | `id` | UUID | PK, default uuid4 | 主键 |
| v0.46.1 | `pipeline_stage_config` | | `project_id` | UUID | FK→project.id, NOT NULL | 所属项目 |
| v0.46.1 | `pipeline_stage_config` | | `stage_name` | VARCHAR(50) | NOT NULL | Stage 标识（classify/quality_check/...） |
| v0.46.1 | `pipeline_stage_config` | | `enabled` | BOOLEAN | default True | 是否启用 |
| v0.46.1 | `pipeline_stage_config` | | `params` | JSONB | default {} | Stage 特有参数 |
| v0.46.1 | `pipeline_stage_config` | | `created_at` | TIMESTAMP | default now() | 创建时间 |
| v0.46.1 | `pipeline_stage_config` | | `updated_at` | TIMESTAMP | default now(), onupdate | 更新时间 |

**联合唯一约束：** `(project_id, stage_name)`

合计：1 张新表（7 个字段），1 次 Alembic 迁移。

---

## 第十三章 开始前必须先输出

Agent 在进入 Phase 2 编码之前，必须先输出以下三项内容：

1. **当前代码现状理解** — 列出 pipeline-worker stages 目录结构、tasks.py 中 STAGES 列表、AI orchestrator 调用模式、CrossReference 模型现状
2. **第一个任务的实施计划** — 按 `docs/tech-specs/dev-governance-part3-guides.md` §3.1 模板输出
3. **第一个任务的预计修改文件清单** — 明确新增 / 修改 / 不动的文件

**在这三项输出并经确认之前，不要开始写代码。**

---

## 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 计划周期 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|--------|----------|--------|------|
| v0.46.1 | Pipeline stage 配置 DB 模型 + CRUD API | — | — | 0 | Planned |
| v0.46.2 | Pipeline stage 运行时加载用户配置 | — | — | 0 | Planned |
| v0.46.3 | 用户自定义实体类型支持 | — | — | 0 | Planned |
| v0.46.4 | 前端 Pipeline 配置页 | — | — | 0 | Planned |
| v0.46.5 | 跨文档矛盾检测 — 后端 API + AI task | — | — | 0 | Planned |
| v0.46.6 | 跨文档模式发现 — 后端 API + AI task | — | — | 0 | Planned |
| v0.46.7 | 前端图谱页矛盾/模式展示 | — | — | 0 | Planned |

**Phase 封板记录：**

| 功能项 | 包含任务 | 封板日期 | 封板版本号 | 回归测试结果 |
|-------|--------|--------|----------|-----------|
| v0.46 Pipeline 配置化 + 跨文档知识推理 | v0.46.1–v0.46.7 | — | — | — |

---

## 第十五章 变更记录

| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-30 | V1.0 初始版本，基于 Shiji-KB 竞品分析编写 | 产品 Owner |
| 2026-03-31 | 补齐缺失章节（测试/版本号/文档产出/DB 汇总/状态追踪/变更记录/决策/风险） | 产品 Owner |

---

## 第十六章 决策与假设

**关键决策：**
- Pipeline 配置存 DB（`pipeline_stage_config` 表）而非 YAML 文件 — 原因：支持多项目独立配置、API 管理、运行时动态加载
- 矛盾检测先用 embedding 相似度预筛选文档对，再送 LLM 比对 — 原因：避免 N*(N-1)/2 全量比对的 token 爆炸
- 模式发现结果存 Redis 缓存（TTL 24h）而非持久化到 DB — 原因：先验证需求价值，避免过早建表
- `entity_types` 作为 `PipelineStageConfig.params` 的 JSON 字段而非独立表 — 原因：灵活性高，避免额外建表和 JOIN

**重要假设：**
- v0.45 全部完成后才启动 v0.46（基线为 v0.45.14）
- Pipeline worker 可访问 DB（已有 `sync_session_factory`）
- LLM 矛盾检测 prompt 在 500 字摘要输入下准确率可接受
- Redis 已在生产环境部署且可用

---

## 第十七章 版本级风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 文档对数量爆炸（N*(N-1)/2）导致矛盾检测超时 | 中 | 高 | 先用 embedding Top-K 筛选 + max_pairs 上限参数 |
| LLM 幻觉导致矛盾误报 | 中 | 中 | 矛盾记录标记为"AI 建议"，需人工确认后生效 |
| 跳过关键 stage（embed）导致后续功能异常 | 中 | 中 | v0.46.4 UI 中 embed stage 标记"建议不跳过"提示 |
| entity_types prompt 工程效果不稳定 | 中 | 低 | 默认不限定实体类型（与 v0.45 行为一致），用户可选配置 |
| v0.46 任务依赖 v0.45 中多个任务的产出 | 确定 | 高 | v0.46 启动前必须完成 §1.2 能力核实 |
