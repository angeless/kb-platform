# v0.54 开发计划 — Graph 层 + 读者感知视觉增强

> 版本: v0.54.0 | 日期: 2026-04-19 | 分支: `test-v-0-54-a`
> 上一版本: v0.53.0 (HEALTH B+，bridge 服务上线)

---

## 一句话目标

给 KB 加 **2 个互补能力**：
1. **图层**：Graphiti + Kuzu 嵌入式图 DB，把 markdown 中的实体/关系抽取成可查询的时序图
2. **读者感知视觉增强**：当一篇 KB 文章是"给人读的"或"系统型/展示型"时，自动追加 Mermaid 流程图 + 大纲视图

两个能力在 bridge 服务里挂同一个文件处理管线上 — 解析→图入库→（可选）视觉增强。

---

## 范围与约束

### 包含
1. **新包 `packages/bridge-graph/`**：Graphiti + Kuzu 集成
   - 从 markdown IR → entity/relation triples → Kuzu 图
   - 时序字段：每个事实带 `valid_at` / `recorded_at`
   - 把 KB 的 `session_id` 当 episode id（直接复用 p-chain）
   - 单文件 DB 存 `~/Hogwarts-Knowledge-Base/.bridge-state/.graph.kuzu`（`.bridge-state/` 已在 `.bridge-config.yml` ignore_globs）

2. **新包 `packages/bridge-visual/`**：读者感知 + 视觉增强
   - **reader profiler**：基于 frontmatter (`type`, `tags`) + 内容启发式（步骤标志/结构标志/技术术语密度）→ 输出 `audience_score`（0=纯 AI 用，1=纯人类阅读）
   - **mermaid generator**：当 `audience_score >= 0.6` AND 含 H2 步骤/状态/决策 → 生成 Mermaid `flowchart`/`stateDiagram` block
   - **outline builder**：从 H1/H2/H3 抽大纲，输出 `<details>` 折叠或 markdown TOC
   - **inserter**：把生成的 mermaid + outline 嵌入到原文章 frontmatter 之后、正文之前（用 HTML comment 标记，下次 sync 时可识别更新）

3. **bridge_ingest Celery stage** （v0.53 ADR-002 deferred 项 — 这次落地）
   - `services/pipeline-worker/worker/stages/bridge_ingest.py`
   - 把 IR 持久化为 BridgeSyncRecord + Asset/AssetChunk
   - 触发 graph + visual 后处理（如配置开启）

4. **REST + MCP 暴露**
   - `POST /v1/bridge/graph/query` — 图查询（cypher 子集）
   - `POST /v1/bridge/visual/augment` — 给定 markdown，返回带 mermaid+outline 的版本
   - MCP 工具：`kb_graph_search`、`kb_visual_augment`

5. **配置项**（.env + .bridge-config.yml）
   - `BRIDGE_GRAPH_ENABLED=true|false`
   - `BRIDGE_GRAPH_DB_PATH=...` (默认 `<HOGWARTS_KB_PATH>/.bridge-state/.graph.kuzu`)
   - `BRIDGE_VISUAL_ENABLED=true|false`
   - `BRIDGE_VISUAL_AUDIENCE_THRESHOLD=0.6`

### 排除
- ❌ 不实现自动写回 hook（pipeline → KB 的自动回流） — 留 v0.55
- ❌ 不实现 RBAC 中间件（仍是 admin-by-default）
- ❌ 不动 v0.52/v0.53 既有 27 router、7 stage、6 parser、25 model
- ❌ 不动 frontend
- ❌ 不实现 URL ingestion REST 端点（trafilatura 已实现，仅需薄包装，留 v0.55）

### 硬约束
1. **不破坏 v0.53**：bridge_graph + bridge_visual 是新包，新增 stage 在 `bridge_ingest` 内调
2. **图 DB 文件不入 git**：`.graph.kuzu` 加到 .gitignore（同 `.search-index.sqlite` 处理方式）
3. **视觉增强可逆**：嵌入用 HTML comment 标记，删除/重生成时不破坏原作者的内容
4. **GLM 严格模式**：reader profiler 用本地启发式 + 可选 GLM-4 兜底（不可意外退到 OpenAI）
5. **遵循 dev-governance Phase 1-7 + Phase 8 跨审计**

---

## 任务分解

### v0.54.0: 包骨架 + Kuzu 验证
- 新建 `packages/bridge-graph/` + `packages/bridge-visual/`
- pyproject.toml 加 `kuzu`、`graphiti-core`（lazy import）
- 装 + smoke test：能在临时目录创建 Kuzu DB、写一个节点、查回来
- 验收：`python -c "from bridge_graph import GraphStore; gs=GraphStore('/tmp/x.kuzu'); gs.ping()"`

### v0.54.1: markdown → 图（自带启发式 fallback）
- `bridge_graph.extract_triples(ir: dict) -> list[Triple]`
  - 优先策略：本地 spacy NER + 启发式（`[[wiki-link]]` = "references" 关系）
  - 兜底：GLM-4 抽取（开关，默认关闭）
- `GraphStore.upsert_episode(session_id, source_file, triples)` — episode = 一次写入操作
- 单元测试：用 KB 中真实文件（kbsql-bridge-toolkit-research.md）抽 entity/relation
- 验收：能正确把 wiki/concepts/foo.md 中的 `[[wiki/concepts/bar]]` 链接建成 (foo)-[references]->(bar) 边

### v0.54.2: reader profiler
- `bridge_visual.profile_reader(ir: dict) -> ReaderProfile`
  - 输入：IR (frontmatter + content_md)
  - 输出：`{audience_score: float, has_steps: bool, has_branches: bool, has_state_machine: bool, has_outline_value: bool}`
- 启发式信号：
  - `type=howto` → +0.3
  - 含 "Step N:" / "## 步骤" → +0.2 + has_steps=True
  - 含 "if ... then ..." 决策语 → +0.2 + has_branches=True
  - 含状态/状态机术语 → +0.15 + has_state_machine=True
  - 长文（>3000 字） → +0.15 has_outline_value=True
  - `type=concept` 或 `type=entity` → +0.1
  - 满 1.0 截止
- 单元测试：用 5 篇真实 KB 文件验证分数
- 验收：howtos/cross-platform-memory-spec.md 应该 ≥ 0.7（it has steps + outline value）

### v0.54.3: visual augmentor (mermaid + outline)
- `bridge_visual.generate_mermaid(ir, profile) -> str | None`
  - has_steps → flowchart
  - has_state_machine → stateDiagram
  - has_branches → flowchart with diamonds
- `bridge_visual.generate_outline(ir) -> str` — 从 H1/H2/H3 抽折叠 outline
- `bridge_visual.augment(ir) -> str` — 返回完整新内容（frontmatter + mermaid + outline + 原 body）
  - 用 HTML comment 标记 `<!-- bridge-visual:start ... bridge-visual:end -->` 便于二次更新时识别
- 验收：把 v0.54 dev-plan 自己跑一遍 augment，输出 mermaid 流程图

### v0.54.4: bridge_ingest Celery stage
- `services/pipeline-worker/worker/stages/bridge_ingest.py`
  - 接收 IR → 写 BridgeSyncRecord（hash/layer/状态）
  - 创建/更新 Asset + AssetChunk
  - 如 `BRIDGE_GRAPH_ENABLED` → 调 bridge_graph.extract_triples + upsert
  - 如 `BRIDGE_VISUAL_ENABLED` 且 `audience_score >= threshold` → 调 bridge_visual.augment + 触发 kb_writer 回写
- `bridge.tasks` 注册 Celery task
- 修改 `kb_watcher.run_watcher()` 默认注入 enqueue_fn
- 单元测试：mock Celery，验证 BridgeSyncRecord 行被创建

### v0.54.5: REST + MCP 暴露
- 新 REST 端点：
  - `POST /v1/bridge/graph/query` — 简单图查询（限定子集，避免 RCE）
  - `GET /v1/bridge/graph/stats` — 节点/关系数
  - `POST /v1/bridge/visual/augment` — 输入 markdown，返回增强版
  - `POST /v1/bridge/visual/profile` — 仅判断 reader profile
- 新 MCP 工具：
  - `kb_graph_search(query, top_k=10)` — 实体名 → 邻居
  - `kb_graph_neighbors(entity, depth=2)` — 实体扩展
  - `kb_visual_augment(markdown)` — 给一段 markdown，返回带 mermaid 的版本
  - `kb_visual_profile(markdown)` — reader 画像

### v0.54.6: 文档 + 配套配置
- `docs/api/bridge-graph.md` + `docs/api/bridge-visual.md`
- 更新 `bridge-deployment.md`：新增 graph DB / visual augmentor 启停说明
- Hogwarts-KB 加 `.gitignore` 条目：`.bridge-state/`
- 把"自动 mermaid 增强"功能加进 `.bridge-config.yml`

### v0.54.7: 测试 + Phase 8 跨审计
- 全跑测试套件，目标 ≥ 130 测试（v0.53 是 94，新增至少 36）
- 派 3 sub-agent 跨审计（spec / quality / completeness）
- 修所有 Critical+High 直到收敛

### v0.54.8: 封板 + push
- VERSION 0.53.0 → 0.54.0
- CHANGELOG / TODO_NEXT 两边都更新
- push 两个仓库
- 写 KB 交接文档

---

## 验收清单（封板前）

- [ ] Graphiti + Kuzu 可工作，KB 中所有 wiki/* 文件能成功 upsert
- [ ] reader profiler 在 5 篇真实文件上分数符合预期（howto > concept > raw-source）
- [ ] visual augmentor 能把 v0.54 dev plan 自己生成 mermaid 流程图
- [ ] bridge_ingest Celery stage 能把 IR 真正写入 BridgeSyncRecord
- [ ] REST + MCP 新端点都通
- [ ] v0.53 既有 94 测试仍全过（无回归）
- [ ] v0.54 新增 ≥ 36 测试全过
- [ ] Phase 8 健康度 ≥ B
- [ ] `.bridge-state/` 不入 git
- [ ] 两个仓 push 成功

---

## 依赖

新增 Python：
- `kuzu>=0.5` — embedded graph DB (MIT)
- `graphiti-core` — knowledge graph framework (Apache-2.0)
- 已有：spacy, yake, python-frontmatter, markdown-it-py

视觉增强不需要新依赖（mermaid 是纯 markdown text），但建议加：
- `pymdownx-toc` — outline 渲染辅助（可选）

---

## 时间预算（睡眠时间内执行）

- v0.54.0–1（包骨架 + 图层）：~2.5 小时
- v0.54.2–3（reader profiler + visual augmentor）：~2 小时
- v0.54.4（bridge_ingest stage）：~1 小时
- v0.54.5（REST + MCP）：~1.5 小时
- v0.54.6（文档）：~30 分钟
- v0.54.7（测试 + 审计）：~2 小时
- v0.54.8（封板）：~30 分钟
- **总计**：~10 小时

---

## ADR 占位（Phase 8 后追加）

待审计反馈。

---

*Drafted by Claude Code 2026-04-19 11:00 in autonomous mode following dev-governance v1.4*
