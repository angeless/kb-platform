# KB Platform v0.49 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v049
**版本**: V1.0（初始版）
**日期**: 2026-03-31
**基线**: v0.48 完成后
**依据**: PRD §2.3（IR）+ §5（成本）+ WISHLIST W-01/W-04/W-11/W-13
**作者**: Claude Code（自动生成）

---

## 第一章 版本主题

**v0.49：Pipeline 智能化 — IR 中间表示 + 反思循环 v2 + 语义搜索升级**

> 三大核心升级：① 统一中间表示（IR）让 Pipeline 各 stage 共享结构化数据而非 raw text；② 多轮反思循环将知识生成准确率从 ~85% 提升至 95%+；③ pgvector 原生迁移将语义搜索从 O(n) 降至 O(log n)。

---

## 第二章 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.49.1 | IR 中间表示 — AssetChunk schema 升级 | P0 | 待开发 | PRD §2.3 |
| v0.49.2 | IR 适配 — classify/doc_generate stage 适配新 schema | P0 | 待开发 | PRD §2.3 |
| v0.49.3 | 反思循环 v2 — 规则校验层 + 二次 AI 自检 | P0 | 待开发 | W-13 |
| v0.49.4 | pgvector 原生迁移 — JSONB → vector 列 + HNSW 索引 | P1 | 待开发 | W-04 |
| v0.49.5 | Per-stage 幂等性保障 | P1 | 待开发 | W-11 |
| v0.49.6 | Prometheus 指标导出 | P1 | 待开发 | W-01 |
| v0.49.7 | 模型成本限制执行 — 按 route 追踪 + 预算切断 | P1 | 待开发 | PRD §5 |

---

## 第三章 目标与边界

### 3.1 北极星校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ |
|-----|----------------|-------------|-------------|
| v0.49.1 | ✅ 整合端（结构化数据流） | - | - |
| v0.49.2 | ✅ 整合端（stage 间数据质量） | - | - |
| v0.49.3 | ✅ 整合端（生成质量 85%→95%） | - | - |
| v0.49.4 | - | ✅ 输出端（搜索性能） | - |
| v0.49.5 | - | - | ✅ 重跑安全性 |
| v0.49.6 | - | - | ✅ 生产可观测 |
| v0.49.7 | - | - | ✅ 成本控制 |

### 3.2 明确不做

- OpenTelemetry 分布式追踪 — v0.49 仅做 Prometheus 指标，全链路追踪留给 v0.51+
- SKILL 驱动 Pipeline — 留给 v0.51
- 知识本体建模 — 留给 v0.51
- 前端新页面 — v0.49 无新页面（成本看板可在 v0.50 做）

---

## 第四章 执行顺序

```
IR 链：v0.49.1 → v0.49.2
反思链：v0.49.3（依赖 v0.49.2 IR 数据）
搜索链：v0.49.4（独立）
基础设施：v0.49.5 → v0.49.6 → v0.49.7（可并行）
```

建议：`v0.49.1 → v0.49.2 → v0.49.4 → v0.49.3 → v0.49.5 → v0.49.6 → v0.49.7`

---

## 第五章 各任务详细定义

---

### v0.49.1: IR 中间表示 — AssetChunk schema 升级

**前置依赖：** 无

**背景：** PRD §2.3 要求"统一为可供后续 AI 使用的结构化片段"。当前 AssetChunk 仅有 `content_text` (raw text) + `tags` (JSONB)。

**变更：**
- `packages/shared-models/shared_models/asset.py` — AssetChunk 新增字段：
  ```
  original_format: String(20)        # "text" | "pdf" | "ocr" | "asr" | "video_frame" | "url"
  structure_type: String(20)         # "paragraph" | "heading" | "table" | "list" | "code" | "caption"
  extraction_confidence: Float       # 解析器对提取质量的置信度
  semantic_boundaries: JSONB         # {"start_page": 1, "end_page": 2, "timestamp_ms": 30000}
  language: String(10)               # "zh" | "en" | "mixed"
  ```
- `infra/sql/alembic/versions/` — migration
- 约 30 行模型 + 25 行 migration

**验收标准：**
- 新上传的文件，chunk 包含 IR 字段
- 旧 chunk 的 IR 字段为 NULL（向后兼容）

---

### v0.49.2: IR 适配 — classify/doc_generate 适配新 schema

**前置依赖：** v0.49.1

**变更：**
- `services/ingestion-worker/worker/parsers/*.py` — 各解析器在创建 chunk 时填充 IR 字段
- `services/pipeline-worker/worker/stages/classify.py` — 利用 structure_type 优化分类（heading chunk 权重更高）
- `services/pipeline-worker/worker/stages/doc_generate.py` — 利用 IR 字段生成更结构化的文档
- 约 60 行改动

---

### v0.49.3: 反思循环 v2

**前置依赖：** v0.49.2

**背景：** 当前仅有单次 confidence < 0.7 重试。Shiji-KB 证明 5 轮反思可将准确率从 90% 提升至 99.1%。

**变更：**
- `services/pipeline-worker/worker/stages/quality_check.py` — 新增规则校验层：
  - 格式一致性检查（标题层级、列表格式）
  - 来源引用完整性（每个结论是否有 SourceRef）
  - 术语一致性（同一概念是否用同一名称）
- `services/ai-orchestrator/orchestrator/tasks.py` — 新增 `reflect_and_revise` Celery task：
  - 接收 quality_check 的 issues 列表
  - 调用 LLM 自检："为什么这些 issue 存在？如何修正？"
  - 自动修正后重新提交 quality_check
  - 最多 3 轮（可配置）
- `services/pipeline-worker/worker/tasks.py` — quality_check 后接入反思循环
- 约 120 行

**验收标准：**
- 格式/来源/术语 3 类规则自动检查
- 低质量文档自动修正，最多 3 轮
- 可通过 pipeline config 设置 `max_reflection_rounds`

---

### v0.49.4: pgvector 原生迁移

**前置依赖：** 无

**变更：**
- `infra/sql/alembic/versions/` — migration：将 DocEmbedding.embedding (JSONB) 数据复制到 embedding_vec (vector) 列
- `services/api/app/services/search_service.py` — 语义搜索改用 pgvector `<=>` 运算符
- `infra/sql/alembic/versions/` — 创建 HNSW 索引
- 约 40 行

**验收标准：**
- 语义搜索使用 pgvector 原生向量比较
- 1000 篇文档搜索延迟 < 100ms（之前可能 > 500ms）

---

### v0.49.5: Per-stage 幂等性保障

**前置依赖：** v0.47.6（stage log 表）

**变更：**
- `packages/shared-models/shared_models/pipeline_stage_log.py` — 新增 `input_hash` 字段
- `services/pipeline-worker/worker/tasks.py` — 每个 stage 执行前检查 (job_id, stage_name, input_hash)，若已存在则跳过
- 约 30 行

---

### v0.49.6: Prometheus 指标导出

**前置依赖：** 无

**变更：**
- `services/api/app/middleware/metrics.py` — 用 `prometheus_client` 替代内存指标
- `/metrics` 端点输出 Prometheus 格式
- 关键指标：request_duration, request_count, active_connections, llm_calls_total, llm_tokens_total
- `requirements.in` — 新增 `prometheus-client`
- 约 40 行

---

### v0.49.7: 模型成本限制执行

**前置依赖：** v0.47.6（stage log 含 token_usage）

**变更：**
- `services/ai-orchestrator/orchestrator/llm_client.py` — call_llm 返回 token 用量（不仅日志，还返回给调用方）
- `services/ai-orchestrator/orchestrator/cost_tracker.py` — 新增：
  - 按 model_route 累计 token 消耗
  - 与 cost_limit_usd 比较
  - 超限时拒绝调用 + 告警
- 约 60 行

---

## 第六章 风险

| 风险 | 缓解 |
|------|------|
| IR schema 迁移影响旧数据 | 旧 chunk 新字段为 NULL，不影响已有流程 |
| pgvector HNSW 索引构建耗时 | 使用 CREATE INDEX CONCURRENTLY |
| 反思循环增加 LLM 调用成本 | 默认 max_rounds=3，首先尝试规则修正（不调 LLM） |
| Prometheus 暴露内部指标 | /metrics 端点限制为内网访问 |
