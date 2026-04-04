# KB Platform v0.49 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v049
**版本**: V2.0（规范重写版）
**日期**: 2026-03-31
**基线**: v0.48 完成后
**依据**: PRD §2.3（IR）+ §5（成本）+ WISHLIST W-01/W-04/W-11/W-13
**作者**: Claude Code（自动生成）

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划基于 v0.48 完成后的代码增量增强。禁止重构无关模块。

### 1.2 继承已有能力

- **AssetChunk**（`packages/shared-models/shared_models/asset.py`）— content_text + tags JSONB + embedding
- **Pipeline stages**（`services/pipeline-worker/worker/stages/`）— 7 个 stage + config 参数化（v0.46）
- **PipelineStageConfig**（v0.46.1）— enable/disable + params
- **PipelineStageLog**（v0.47.6）— per-stage 执行日志
- **quality_check**（`stages/quality_check.py`）— 规则校验 + PII 检测 + confidence 评分
- **LLM client**（`services/ai-orchestrator/orchestrator/llm_client.py`）— call_llm + token 日志
- **反思循环 v1**（v0.45.13）— `build_reflection_prompt()` + confidence 机制
- **DocEmbedding**（`packages/shared-models/`）— embedding 字段（JSONB 存储）
- **Readability**（v0.48.1 `services/api/app/utils/readability.py`）— trafilatura 正文提取
- **video_parser**（v0.48.3 `services/ingestion-worker/worker/parsers/video_parser.py`）— FFmpeg 音频提取 + 字幕检测
- **URL import 正文提取**（v0.48.2）— import_url 使用 readability 替代原始 HTML
- **Prometheus 无**（v0.47 仅做 per-stage DB 日志）

### 1.3 最小改动原则 / 1.4 任务领取规则

同 v0.47。

---

## 第二章 当前阶段事实

### 2.1 版本主题

**v0.49：Pipeline 智能化 — IR 中间表示 + 反思循环 v2 + 语义搜索升级**

> 三大升级：① 统一 IR 让 Pipeline 各 stage 共享结构化数据；② 多轮反思循环将知识生成准确率从 ~85% 提升至 95%+；③ pgvector 将语义搜索从 O(n) 降至 O(log n)。

---

## 第三章 本轮目标与边界

### 3.1 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.49.1 | IR 中间表示 — AssetChunk schema 升级 | P0 | ✅ Done | PRD §2.3 |
| v0.49.2 | IR 适配 — 解析器填充 IR 字段 | P0 | ✅ Done | PRD §2.3 |
| v0.49.3 | IR 适配 — classify + doc_generate 利用 IR 数据 | P0 | 待开发 | PRD §2.3 |
| v0.49.4 | 反思循环 v2 — 规则校验层 | P0 | 待开发 | W-13 |
| v0.49.5 | 反思循环 v2 — AI 自检 + 循环集成 | P0 | 待开发 | W-13 |
| v0.49.6 | pgvector 原生迁移 | P1 | 待开发 | W-04 |
| v0.49.7 | Per-stage 幂等性保障 | P1 | 待开发 | W-11 |
| v0.49.8 | Prometheus 指标导出 | P1 | 待开发 | W-01 |
| v0.49.9 | 模型成本限制执行 | P1 | 待开发 | PRD §5 |

### 3.2 北极星三问校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ |
|-----|----------------|-------------|-------------|
| v0.49.1 | ✅ 整合端（结构化数据流） | - | - |
| v0.49.2 | ✅ 整合端（解析器输出 IR） | - | - |
| v0.49.3 | ✅ 整合端（stage 利用 IR） | - | - |
| v0.49.4 | ✅ 整合端（规则校验质量） | - | - |
| v0.49.5 | ✅ 整合端（85%→95% 准确率） | - | - |
| v0.49.6 | - | ✅ 搜索性能 | - |
| v0.49.7 | - | - | ✅ 重跑安全性 |
| v0.49.8 | - | - | ✅ 生产可观测 |
| v0.49.9 | - | - | ✅ 成本控制 |

### 3.3 明确不做

- OpenTelemetry 分布式追踪 — 仅做 Prometheus 指标，全链路追踪留给 v0.51
- SKILL 驱动 Pipeline — 留给 v0.51
- 知识本体建模 — 留给 v0.51
- 前端新页面 — v0.49 无新页面

---

## 第四章 执行顺序

```
IR 链：v0.49.1 → v0.49.2 → v0.49.3
反思链：v0.49.4 → v0.49.5（v0.49.5 依赖 v0.49.3 的 IR 数据辅助验证）
搜索链：v0.49.6（独立）
基础设施：v0.49.7 / v0.49.8 / v0.49.9（可并行）
```

建议：`v0.49.1 → v0.49.2 → v0.49.3 → v0.49.6 → v0.49.4 → v0.49.5 → v0.49.7 → v0.49.8 → v0.49.9`

---

## 第五章 各任务详细定义

---

### v0.49.1: IR 中间表示 — AssetChunk schema 升级

**任务版本号：** v0.49.1
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**现状：** AssetChunk 仅有 `content_text`（raw text）+ `tags`（JSONB），缺少结构化解析元数据。

**目标（Goal）：** 扩展 AssetChunk 模型，新增 5 个 IR 字段，使 chunk 携带解析来源、结构类型、置信度等结构化信息。

---

#### 数据库变更

**修改文件：**
- `packages/shared-models/shared_models/asset.py` — AssetChunk 新增字段：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| original_format | VARCHAR(20) | nullable | "text" / "pdf" / "ocr" / "asr" / "video_frame" / "url" |
| structure_type | VARCHAR(20) | nullable | "paragraph" / "heading" / "table" / "list" / "code" / "caption" |
| extraction_confidence | FLOAT | nullable | 解析器对提取质量的置信度 (0.0-1.0) |
| semantic_boundaries | JSONB | nullable | `{"start_page": 1, "end_page": 2, "timestamp_ms": 30000}` |
| language | VARCHAR(10) | nullable | "zh" / "en" / "mixed" |

- `infra/sql/alembic/versions/` — migration：`add_ir_fields_to_asset_chunk`

**业务规则：**
① 5 个新字段全部 nullable — 旧 chunk 不受影响（向后兼容）
② 新上传的文件，解析器在创建 chunk 时填充 IR 字段（v0.49.2 实现）
③ 本任务仅做 schema 升级，不改解析器逻辑

---

#### 验收标准

- [ ] Alembic migration 成功执行
- [ ] AssetChunk 模型包含 5 个新字段
- [ ] 旧 chunk 的 IR 字段为 NULL（不影响已有流程）
- [ ] 新建 chunk 可写入 IR 字段值
- [ ] `alembic downgrade -1` 可回滚

---

#### 工作范围

**包含：** AssetChunk 模型扩展 + migration（~30 行模型 + ~25 行 migration）
**不包含：** 解析器适配（v0.49.2）；stage 利用 IR 数据（v0.49.3）

---

#### 预估工作量

- Phase 1 读 AssetChunk 模型当前字段：0.5 小时
- Phase 2 执行：1.5 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Migration 影响旧数据 | 低 | 低 | 全部 nullable，不影响已有记录 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `packages/shared-models/shared_models/asset.py` AssetChunk 完整定义
> 2. 确认当前 Alembic head revision

---

### v0.49.2: IR 适配 — 解析器填充 IR 字段

**任务版本号：** v0.49.2
**优先级：** P0
**前置依赖：** v0.49.1（IR 字段存在）

---

#### 背景与目标

**目标（Goal）：** 修改各解析器（text / pdf / ocr / asr / video / url），在创建 AssetChunk 时填充 IR 字段。

---

#### 后端变更

**修改文件：**
- `services/ingestion-worker/worker/parsers/text_parser.py` — 设置：
  - `original_format="text"`, `structure_type` 根据内容推断（heading / paragraph / list）
  - `extraction_confidence=1.0`（纯文本无损）, `language` 根据内容检测

- `services/ingestion-worker/worker/parsers/pdf_parser.py` — 设置：
  - `original_format="pdf"`, `structure_type` 根据 PDF 结构推断
  - `extraction_confidence` 根据 PDF 质量（扫描版低、原生高）
  - `semantic_boundaries={"start_page": N, "end_page": M}`

- `services/ingestion-worker/worker/parsers/ocr_parser.py` — 设置：
  - `original_format="ocr"`, `extraction_confidence` 根据 OCR 引擎置信度

- `services/ingestion-worker/worker/parsers/asr_parser.py` — 设置：
  - `original_format="asr"`, `semantic_boundaries={"timestamp_ms": N}`

- `services/ingestion-worker/worker/parsers/video_parser.py`（v0.48.3 新增）— 设置：
  - `original_format="video_frame"` / `"asr"`，按来源区分

**业务规则：**
① 每个解析器在创建 AssetChunk 时，根据自身解析能力填充 IR 字段
② `original_format` 由解析器类型决定（确定值）
③ `structure_type` 由内容分析推断（可为 NULL 如果无法判断）
④ `extraction_confidence` 反映解析质量（1.0=无损，0.5=OCR 低质量）
⑤ `language` 使用简单规则检测（中文字符占比 > 50% → "zh"，否则 "en"，混合 → "mixed"）
⑥ 不引入额外 NLP 依赖做语言检测

---

#### 验收标准

- [ ] 上传 TXT 文件 → chunk.original_format="text", extraction_confidence=1.0
- [ ] 上传 PDF → chunk.original_format="pdf", semantic_boundaries 包含页码
- [ ] OCR 图片 → chunk.original_format="ocr", extraction_confidence < 1.0
- [ ] ASR 音频 → chunk.original_format="asr", semantic_boundaries 包含 timestamp_ms
- [ ] 中文内容 → chunk.language="zh"
- [ ] 未修改的解析器（如果有）→ IR 字段为 NULL，不报错

---

#### 工作范围

**包含：** 5-6 个解析器的 IR 字段填充（每个 ~10 行，共 ~60 行）
**不包含：** 高精度语言检测（NLP 模型）；structure_type 的 AI 推断

---

#### 预估工作量

- Phase 1 读各解析器创建 chunk 的位置：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 解析器 API 不统一导致改动量大 | 中 | 中 | Phase 1 确认各解析器的 chunk 创建方式 |
| language 检测不准确 | 低 | 低 | 简单规则足够，不追求完美 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读每个解析器文件，确认 AssetChunk 创建位置
> 2. 确认各解析器是否有置信度信息可用

---

### v0.49.3: IR 适配 — classify + doc_generate 利用 IR 数据

**任务版本号：** v0.49.3
**优先级：** P0
**前置依赖：** v0.49.2（解析器已填充 IR 字段）

---

#### 背景与目标

**目标（Goal）：** 修改 classify 和 doc_generate stage，利用 IR 字段（structure_type / extraction_confidence / language）生成更准确的分类和更结构化的文档。

---

#### 后端变更

**修改文件：**
- `services/pipeline-worker/worker/stages/classify.py` — 利用 IR：
  - `structure_type="heading"` 的 chunk 权重更高（标题比正文更能代表分类）
  - `extraction_confidence < 0.5` 的 chunk 降权或标记为低质量
  - 在分类 prompt 中包含 structure_type 信息

- `services/pipeline-worker/worker/stages/doc_generate.py` — 利用 IR：
  - 按 structure_type 组织生成文档结构（heading → 文档标题候选，table → 结构化数据段）
  - 使用 language 字段指导生成语言（中文输入 → 中文输出）
  - 低 extraction_confidence 的 chunk 在生成 prompt 中标注"此段可能有 OCR 错误"

**业务规则：**
① classify stage：`structure_type="heading"` chunk 在分类决策中权重 2x
② classify stage：`extraction_confidence < 0.5` 的 chunk 标记为低质量，不影响主分类
③ doc_generate stage：按 structure_type 排序 chunk（heading → paragraph → list → table）
④ doc_generate stage：低置信度 chunk 的内容在 prompt 中添加 `[OCR uncertainty]` 标注
⑤ IR 字段为 NULL 时（旧数据）→ 使用默认行为，不回归

---

#### 验收标准

- [ ] heading chunk 在分类中获得更高权重（可通过日志验证）
- [ ] 低 extraction_confidence chunk 不导致错误分类
- [ ] doc_generate 输出中 heading 信息被用于文档标题
- [ ] IR 字段全部为 NULL 的旧数据 → 行为与 v0.48 完全一致
- [ ] 分类和文档生成质量主观提升（对比测试）

---

#### 工作范围

**包含：** classify.py + doc_generate.py 中利用 IR 字段的逻辑（~40 行）
**不包含：** 其他 stage 的 IR 适配（quality_check / embed 等 — 当前不需要）

---

#### 预估工作量

- Phase 1 读 classify + doc_generate 完整逻辑：1.5 小时
- Phase 2 执行：3 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 权重调整导致分类偏差 | 中 | 中 | IR 字段为 NULL 时 fallback 默认行为 |
| prompt 增加 IR 信息导致 token 增长 | 低 | 低 | 仅添加简短标注，不显著增加 token |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 classify.py 完整逻辑，确认分类决策方式
> 2. 读 doc_generate.py 完整逻辑，确认 chunk 组织方式
> 3. 确认 prompt 构建位置（prompts.py 或内联）

---

### v0.49.4: 反思循环 v2 — 规则校验层

**任务版本号：** v0.49.4
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**现状：** quality_check 仅做基本规则（内容长度 / 标题检查 / PII 检测），缺少格式一致性、来源引用、术语一致性检查。

**目标（Goal）：** 扩展 quality_check 的规则校验层，新增 3 类检查规则：格式一致性、来源引用完整性、术语一致性。

---

#### 后端变更

**修改文件：**
- `services/pipeline-worker/worker/stages/quality_check.py` — 新增 3 个检查函数：

```
def _check_format_consistency(content_md: str) -> list[dict]:
    # 检查标题层级（H1 → H2 → H3，不跳级）
    # 检查列表格式（统一使用 - 或 1. ，不混用）
    # 返回 [{"type": "format", "severity": "low", "message": "..."}]

def _check_source_references(content_md: str, source_chunks: list) -> list[dict]:
    # 检查每个结论段落是否有 SourceRef
    # 无来源引用的结论 → issue
    # 返回 issues 列表

def _check_terminology_consistency(content_md: str, project_docs: list) -> list[dict]:
    # 检查同一概念是否用同一名称（如"机器学习"和"ML"不统一）
    # 返回 issues 列表
```

**业务规则：**
① 格式检查：H1 后必须是 H2（不能直接跳到 H3）；列表风格统一
② 来源检查：包含断言性语句的段落应有 chunk 来源引用
③ 术语检查：同一文档中同一概念应使用统一名称
④ 每类检查返回 issues 列表（type / severity / message）
⑤ issues 汇总到 quality_check 结果中，不阻断 pipeline（仅标记）
⑥ 可通过 pipeline config 的 quality_check.params 单独开关每类检查

---

#### 验收标准

- [ ] 标题跳级（H1 → H3）→ 产生格式 issue
- [ ] 无来源引用的结论段落 → 产生来源 issue
- [ ] 术语不一致（同一文档中 "机器学习" / "ML" 混用）→ 产生术语 issue
- [ ] 通过 params `{"check_format": false}` 可关闭格式检查
- [ ] 无问题的文档 → 无 issues 产生
- [ ] 旧文档（无 IR 数据）→ 规则仍可运行（仅基于 content_md）

---

#### 工作范围

**包含：** quality_check.py 新增 3 个检查函数 + 汇总逻辑（~60 行）
**不包含：** AI 自检修正（v0.49.5）；反思循环集成（v0.49.5）

---

#### 预估工作量

- Phase 1 读 quality_check.py 当前结构 + 了解检查规则逻辑：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 规则误报（正常格式被标记） | 中 | 低 | severity=low 的 issue 不影响发布 |
| 术语检测过于简单导致漏报 | 中 | 低 | v0.49 做基础规则，高精度留给 v0.51 SKILL |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `quality_check.py` 完整逻辑，确认 issue 返回格式
> 2. 确认 quality_check params 的扩展方式

---

### v0.49.5: 反思循环 v2 — AI 自检 + 循环集成

**任务版本号：** v0.49.5
**优先级：** P0
**前置依赖：** v0.49.3（IR 适配完成）+ v0.49.4（规则校验层完成）

---

#### 背景与目标

**目标（Goal）：** 新增 `reflect_and_revise` Celery task，接收 quality_check 的 issues，调用 LLM 自检修正，自动修正后重新提交 quality_check，最多 3 轮。

---

#### 后端变更

**新增逻辑：**
- `services/ai-orchestrator/orchestrator/tasks.py` — 新增 Celery task：
  ```
  @celery_app.task(name="orchestrator.reflect_and_revise")
  def reflect_and_revise(doc_id: str, issues: list[dict], round_num: int = 1) -> dict:
      # 1. 构建反思 prompt："以下是质量检查发现的问题：{issues}。请分析原因并修正文档。"
      # 2. 调用 LLM 获取修正后的内容
      # 3. 更新文档内容
      # 4. 重新运行 quality_check
      # 5. 如仍有 issues 且 round_num < max_rounds → 递归调用
      # 6. 返回最终结果 {"rounds": N, "remaining_issues": [...]}
  ```

**修改文件：**
- `services/pipeline-worker/worker/tasks.py` — quality_check 后接入反思循环：
  - quality_check 返回 issues → 调用 `reflect_and_revise.delay()`
  - max_rounds 从 pipeline config 读取（默认 3）
- `services/ai-orchestrator/orchestrator/prompts.py` — 新增 `build_reflection_v2_prompt()`

**业务规则：**
① quality_check 发现 issues 时，触发反思循环
② 第 1 轮：先尝试规则自动修正（格式问题可自动修复，不调 LLM）
③ 规则修正后仍有 issues → 调用 LLM 自检修正
④ LLM 返回修正后的内容 → 更新文档 → 重新 quality_check
⑤ 最多 max_rounds 轮（默认 3，从 `pipeline_stage_config.quality_check.params.max_reflection_rounds` 读取）
⑥ 所有 issues 清除或达到 max_rounds → 结束循环
⑦ 每轮记录到 PipelineStageLog（stage_name="reflection_round_{N}"）

---

#### 验收标准

- [ ] 文档有格式问题 → 规则自动修正（不调 LLM），quality_check 通过
- [ ] 文档有来源缺失问题 → LLM 自检后补充来源引用
- [ ] 经过 3 轮仍有 issues → 循环结束，remaining_issues 记录
- [ ] `max_reflection_rounds=0` → 跳过反思循环（与 v0.48 行为一致）
- [ ] 反思每轮记录到 PipelineStageLog

---

#### 工作范围

**包含：** reflect_and_revise task + prompt + tasks.py 集成（~80 行）
**不包含：** 反思循环的前端可视化；反思结果的用户通知

---

#### 预估工作量

- Phase 1 读 quality_check 输出格式 + v0.45 反思机制：1.5 小时
- Phase 2 执行：5 小时
- Phase 3 测试：2.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 反思循环增加 LLM 成本 | 确定 | 中 | 默认 max_rounds=3；先规则修正再调 LLM |
| LLM 修正引入新错误 | 中 | 中 | 每轮重新 quality_check，确保不恶化 |
| 递归调用导致无限循环 | 低 | 高 | 硬限制 max_rounds=5 上限 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 v0.45.13 反思循环机制（build_reflection_prompt）
> 2. 读 quality_check 的 issues 输出格式
> 3. 确认 tasks.py 中 quality_check 后的流转逻辑

---

### v0.49.6: pgvector 原生迁移

**任务版本号：** v0.49.6
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**现状：** DocEmbedding 已有 `embedding`（JSONB）和 `embedding_vec`（pgvector Vector(1536)，nullable）两列共存。pgvector extension 和列已通过迁移 `a1b2c3d4e5f6` / `b2c3d4e5f6a7` 创建。但尚未建立 HNSW 索引，搜索仍使用 JSONB 全表扫描。

**目标（Goal）：** 为已有 `embedding_vec` 列创建 HNSW 索引，将语义搜索改用 `<=>` 运算符，回填历史数据。

---

#### 数据库变更

- `infra/sql/alembic/versions/` — migration 分 2 步（列已存在，无需 ADD COLUMN）：
  1. 数据回填：`UPDATE doc_embedding SET embedding_vec = embedding::vector WHERE embedding IS NOT NULL AND embedding_vec IS NULL`
  2. `CREATE INDEX CONCURRENTLY idx_doc_embedding_vec ON doc_embedding USING hnsw (embedding_vec vector_cosine_ops)`
  > ⚠️ 注意：`embedding_vec` 列和 pgvector extension 已通过迁移 `a1b2c3d4e5f6` / `b2c3d4e5f6a7` 创建，此处 **不要** 重复 `CREATE EXTENSION` 或 `ADD COLUMN`。

**修改文件：**
- `packages/shared-models/shared_models/embedding.py`（DocEmbedding）— `embedding_vec` 列已存在，无需修改模型定义
- `services/api/app/services/search_service.py` — 语义搜索改用 `embedding_vec <=> query_vec` 运算符
- 依赖文件 — 新增 `pgvector` Python 包

**业务规则：**
① 使用 `CREATE INDEX CONCURRENTLY` 避免锁表
② 保留旧 `embedding` JSONB 列（不删除，后续版本清理）
③ 新写入的 embedding 同时写入两列
④ 搜索优先使用 `embedding_vec`（有值时），fallback 旧 JSONB 列
⑤ HNSW 索引参数：`m=16, ef_construction=64`（默认值）

---

#### 验收标准

- [ ] Migration 成功执行，`doc_embedding` 表包含 `embedding_vec` 列
- [ ] 已有 embedding 数据成功复制到新列
- [ ] 语义搜索使用 pgvector `<=>` 运算符（可通过 EXPLAIN 验证）
- [ ] 1000 篇文档搜索延迟 < 100ms（之前可能 > 500ms）
- [ ] 无 embedding 数据的记录 → 搜索不报错
- [ ] `alembic downgrade` 可回滚（删除 vector 列和索引）

---

#### 工作范围

**包含：** migration + 模型修改 + search_service 适配（~40 行）
**不包含：** 旧 JSONB 列删除（未来版本）；多维度向量支持

---

#### 预估工作量

- Phase 1 读 DocEmbedding 模型 + search_service 查询逻辑：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| HNSW 索引构建耗时（大数据量） | 中 | 中 | CONCURRENTLY 不锁表 |
| pgvector 扩展未安装 | 中 | 高 | Migration 中 CREATE EXTENSION IF NOT EXISTS |
| embedding 维度不是 1536 | 低 | 高 | Phase 1 确认实际维度 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 DocEmbedding 模型确认 embedding 字段类型和维度
> 2. 确认 PostgreSQL 是否已安装 pgvector 扩展
> 3. 读 search_service.py 确认搜索查询方式

---

### v0.49.7: Per-stage 幂等性保障

**任务版本号：** v0.49.7
**优先级：** P1
**前置依赖：** v0.47.6（PipelineStageLog 表存在）

---

#### 背景与目标

**目标（Goal）：** 在 PipelineStageLog 中新增 `input_hash` 字段，每个 stage 执行前检查是否已有相同输入的成功记录，有则跳过（幂等性）。

---

#### 数据库变更

- `packages/shared-models/shared_models/pipeline_stage_log.py` — 新增字段：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| input_hash | VARCHAR(64) | nullable | 输入数据的 SHA-256 hash |

- `infra/sql/alembic/versions/` — migration

**修改文件：**
- `services/pipeline-worker/worker/tasks.py` — 每个 stage 执行前：
  - 计算 input hash（job_id + stage_name + 输入数据 hash）
  - 查询 PipelineStageLog：是否存在 (job_id, stage_name, input_hash, status='completed')
  - 若存在 → 跳过，返回上次结果
  - 若不存在 → 正常执行

**业务规则：**
① input_hash = SHA-256(stage_name + 输入数据序列化)
② 查询条件：同一 job_id + 同一 stage_name + 同一 input_hash + status='completed'
③ 匹配到 → 记录 stage log 为 skipped（reason: idempotent），跳过执行
④ 未匹配到 → 正常执行

---

#### 验收标准

- [ ] 同一 job 的同一 stage 重跑时（输入不变），第二次跳过
- [ ] 输入数据变化后 → 正常重新执行
- [ ] 跳过时 PipelineStageLog 记录 status=skipped
- [ ] 不影响首次执行性能

---

#### 工作范围

**包含：** input_hash 字段 + migration + tasks.py 幂等性检查（~30 行）
**不包含：** 幂等性缓存的 TTL 清理；跨 job 的幂等性

---

#### 预估工作量

- Phase 1 读 tasks.py stage 执行逻辑 + PipelineStageLog 查询方式：1 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Hash 碰撞导致误跳过 | 极低 | 高 | SHA-256 碰撞概率可忽略 |
| 幂等性检查增加 DB 查询 | 低 | 低 | 单次查询，有索引 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 tasks.py 中 stage 执行和输入数据的结构
> 2. 确认 PipelineStageLog 查询方式

---

### v0.49.8: Prometheus 指标导出

**任务版本号：** v0.49.8
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**目标（Goal）：** 集成 `prometheus_client`，替代内存指标，暴露 `/metrics` 端点输出 Prometheus 格式的关键指标。

---

#### 后端变更

**修改文件：**
- `services/api/app/middleware/metrics.py` — 使用 `prometheus_client` 替代内存指标：
  - `request_duration_seconds`（Histogram）
  - `request_count_total`（Counter，按 method / status / path）
  - `active_connections`（Gauge）
  - `llm_calls_total`（Counter，按 model）
  - `llm_tokens_total`（Counter，按 model / type=prompt|completion）

- `services/api/app/main.py` — 注册 `/metrics` 端点
- 依赖文件 — 新增 `prometheus-client`

**业务规则：**
① `/metrics` 端点输出 Prometheus 文本格式
② 5 个核心指标覆盖 HTTP + LLM 两大维度
③ `/metrics` 端点限制为内网访问（不对公网暴露）
④ 不影响现有 API 性能（Counter/Histogram 开销可忽略）

---

#### 验收标准

- [ ] `GET /metrics` 返回 Prometheus 格式文本
- [ ] 发送 HTTP 请求后 request_count_total 增加
- [ ] LLM 调用后 llm_calls_total / llm_tokens_total 增加
- [ ] Prometheus server 可抓取 `/metrics`（`curl` 验证）
- [ ] `/metrics` 不需要 JWT 认证（但限制内网 IP）

---

#### 工作范围

**包含：** metrics.py 改造 + /metrics 端点 + prometheus-client 依赖（~40 行）
**不包含：** Grafana dashboard 配置；Prometheus 部署

---

#### 预估工作量

- Phase 1 读 metrics.py 当前实现：0.5 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| /metrics 暴露内部指标 | 低 | 中 | 限制内网 IP 访问 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/middleware/metrics.py` 当前实现
> 2. 确认 LLM 调用的 hook 点（在哪里统计 token）

---

### v0.49.9: 模型成本限制执行

**任务版本号：** v0.49.9
**优先级：** P1
**前置依赖：** v0.47.6（stage log 含 token_usage）

---

#### 背景与目标

**目标（Goal）：** 新增成本追踪器，按 model route 累计 token 消耗，与预算上限比较，超限时拒绝 LLM 调用。

---

#### 后端变更

**新增文件：**
- `services/ai-orchestrator/orchestrator/cost_tracker.py` — 成本追踪器：
  ```
  class CostTracker:
      def record_usage(model_route: str, prompt_tokens: int, completion_tokens: int): ...
      def check_budget(model_route: str) -> bool: ...  # True = 可继续, False = 超限
      def get_usage_summary(model_route: str) -> dict: ...
  ```

**修改文件：**
- `services/ai-orchestrator/orchestrator/llm_client.py` — call_llm 调用后：
  - 调用 `cost_tracker.record_usage()` 记录消耗
  - 调用前检查 `cost_tracker.check_budget()`，超限时拒绝
  - 返回 token 用量给调用方（不仅记日志）

**业务规则：**
① 每次 LLM 调用后，按 model_route 累计 token 消耗（存 Redis，key: `cost:{route}:{date}`）
② 调用前检查当日累计是否超过 `cost_limit_usd`（从 model route 配置读取）
③ 超限时：拒绝调用 + 返回 `{"error": "budget_exceeded", "detail": "Daily budget for {route} exceeded"}`
④ 记录超限事件到日志（WARNING 级别）
⑤ token → USD 转换使用简单费率表（每个 model 配置 price_per_1k_tokens）
⑥ 无 cost_limit 配置时 → 不限制（默认无限）

---

#### 验收标准

- [ ] LLM 调用后 Redis 中记录 token 消耗
- [ ] 累计消耗超过 cost_limit → 后续调用被拒绝，返回 budget_exceeded
- [ ] 新一天开始后 → 计数器重置（日级粒度）
- [ ] 无 cost_limit 配置 → 不限制，正常调用
- [ ] call_llm 返回值包含 token_usage 信息

---

#### 工作范围

**包含：** cost_tracker.py + llm_client.py 集成（~60 行）
**不包含：** 成本看板前端（v0.50）；月度/项目级预算

---

#### 预估工作量

- Phase 1 读 llm_client.py + model route 配置方式：1 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Redis 不可用导致无法记录成本 | 低 | 中 | 降级：仅记日志不阻断调用 |
| 费率表不准确 | 中 | 低 | 费率可配置，定期更新 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `llm_client.py` 调用流程和返回格式
> 2. 确认 model route 配置方式（DB / 环境变量）
> 3. 确认 Redis 连接方式

---

## 第六章 ~ 第十七章

（结构同 v0.47，简化如下）

### 第六章 实现约束
同 v0.47。Migration 路径：`infra/sql/alembic/versions/`。

### 第七章 任务领取规则
同 v0.47。

### 第八章 测试要求
| 层次 | 覆盖重点 |
|------|---------|
| 后端单元测试 | IR 字段写入、规则检查函数、cost_tracker |
| 后端集成测试 | pgvector 搜索、反思循环端到端（mock LLM）、幂等性 |
| 前端 | 无（v0.49 无前端变更） |

### 第九章 汇报格式
同 v0.47。

### 第十章 版本号管理
`v0.49.{Z}`，Z = 1-9。

### 第十一章 文档产出
每任务更新 VERSION / CHANGELOG / TODO_NEXT.md。版本完成后产出 phase-report + seal-audit。

### 第十二章 新增数据库表汇总

| 任务 | 表 | 变更类型 | 字段 | 类型 | 约束 | 说明 |
|------|---|---------|------|------|------|------|
| v0.49.1 | asset_chunk | 修改 | original_format | VARCHAR(20) | nullable | 解析来源格式 |
| v0.49.1 | asset_chunk | 修改 | structure_type | VARCHAR(20) | nullable | 内容结构类型 |
| v0.49.1 | asset_chunk | 修改 | extraction_confidence | FLOAT | nullable | 提取置信度 |
| v0.49.1 | asset_chunk | 修改 | semantic_boundaries | JSONB | nullable | 语义边界信息 |
| v0.49.1 | asset_chunk | 修改 | language | VARCHAR(10) | nullable | 语言标识 |
| v0.49.6 | doc_embedding | **已有列** | embedding_vec | vector(1536) | nullable | pgvector 原生列（已存在，本次仅建 HNSW 索引 + 回填数据） |
| v0.49.7 | pipeline_stage_log | 修改 | input_hash | VARCHAR(64) | nullable | 输入数据 hash |

合计：0 张新表，3 张表修改（7 个新字段），3 次 Alembic migration。

### 第十三章 开始前必须先输出
1. AssetChunk / DocEmbedding / quality_check 当前代码理解
2. 第一个任务的实施计划
3. 预计修改文件清单

### 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|----------|--------|------|
| v0.49.1 | IR schema 升级 | — | 0 | Planned |
| v0.49.2 | IR 解析器填充 | — | 0 | Planned |
| v0.49.3 | IR stage 适配 | — | 0 | Planned |
| v0.49.4 | 反思规则层 | — | 0 | Planned |
| v0.49.5 | 反思 AI 循环 | — | 0 | Planned |
| v0.49.6 | pgvector 迁移 | — | 0 | Planned |
| v0.49.7 | 幂等性保障 | — | 0 | Planned |
| v0.49.8 | Prometheus | — | 0 | Planned |
| v0.49.9 | 成本限制 | — | 0 | Planned |

### 第十五章 变更记录
| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-31 | V1.0 初始版本 | Claude Code |
| 2026-03-31 | V2.0 规范重写：拆分 IR 适配为 2 任务、反思循环为 2 任务，补齐必填字段 | Claude Code |
| 2026-04-01 | V2.1 交叉审查修复：§1.2 继承列表补充 v0.48 readability/video_parser/URL import 能力 | Claude Code |
| 2026-04-01 | V2.2 交叉审查v2修复：H-1 v0.49.6 pgvector embedding_vec 列已存在，migration 改为仅回填+建索引 | Claude Code |

### 第十六章 决策与假设
**关键决策：**
- IR 字段全部 nullable — 旧数据向后兼容
- pgvector 保留旧 JSONB 列 — 渐进迁移，降低风险
- 反思循环先规则后 AI — 减少 LLM 成本
- 成本追踪用 Redis 而非 DB — 高频写入场景更适合

**假设：**
- PostgreSQL 已安装或可安装 pgvector 扩展
- embedding 维度固定为 1536（使用 OpenAI text-embedding-ada-002 或兼容模型）
- Redis 已部署且可用

### 第十七章 版本级风险
| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| IR schema 迁移影响旧数据 | 低 | 低 | nullable 字段 |
| pgvector HNSW 索引构建耗时 | 中 | 中 | CONCURRENTLY |
| 反思循环增加 LLM 成本 | 确定 | 中 | 先规则后 AI，max_rounds=3 |
| Prometheus /metrics 暴露内部指标 | 低 | 中 | 内网限制 |
