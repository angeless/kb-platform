# v0.53 开发计划 — Bridge Service (KB ↔ KBSQL)

> 版本: v0.53.0 | 日期: 2026-04-19 | 分支: `test-v-0-53-a`
> 上一版本: v0.52.11 (Phase 8 健康度 A, 16 发现/13 修复/3 延后)

---

## 一句话目标

为 KBSQL 增加一个**双向桥接服务（bridge）**，使其能与 Obsidian + GitHub 笔记系统（Hogwarts-KB）双向同步：KB 的 markdown 文件可被 KBSQL 自动摄取处理，KBSQL 的处理结果（摘要/分类/关系）也会回写到 KB。**通过 MCP + REST 双协议对接 Claude Code/Desktop 及任意脚本。**

---

## 范围与约束（READ FIRST）

### 包含范围
1. 新增 `services/bridge/` 服务（fs watcher + git sync + writer）
2. 新增 `services/mcp-server/` 服务（MCP 协议给 Claude agents）
3. 新增 `services/api/app/routers/bridge.py` REST 端点（给脚本/其他 agent）
4. 新增 `ingestion-worker` 解析器：`multi_format_parser.py`（markitdown + docling）
5. 新增 `pipeline-worker` stage：`bridge_ingest`（stage 0，KB 文件 → KBSQL）
6. 新增本地摘要 + 路径分类工具（`packages/bridge-utils/`）
7. 在 Hogwarts-KB 加 `.bridge-config.yml` 和 frontmatter 校验扩展
8. 自动 push 到 GitHub（两个仓库）
9. 前端**不动**（v0.53 不需要 UI 改动；v0.54 再加 bridge 监控页）

### 排除范围
- ❌ v0.52 遗留 I-001/002/003 UI 项（继续延后）
- ❌ 现有 6 个 parser 修改（仅新增，不改动）
- ❌ 现有 7 个 pipeline stage 修改（仅新增 bridge_ingest 在前，不改动）
- ❌ 现有 27 个 router 修改（仅新增 bridge router）
- ❌ JWT_SECRET / ENCRYPTION_KEY 安全修复（v0.52 遗留，bridge 不依赖这些）
- ❌ Aiven Postgres 连接池/SSL 配置改动
- ❌ Frontend 任何改动

### 硬约束
1. **不破坏现有功能**：所有新增代码隔离在新文件/新目录
2. **GLM_API_KEY 严格路由**：bridge 服务只能用 GLM；`BRIDGE_LLM_STRICT=true` 硬开关防止意外回退到 OpenAI/Anthropic
3. **Hogwarts-KB 写入限制**：bridge 只写 `wiki/analyses/` 和 `wiki/summaries/`，永远不写 `raw-sources/` 或 `lessons/`
4. **Git 安全**：写 KB 之前检查 `.git/index.lock`，加锁顺序：先 KB git lock → 后 KBSQL DB transaction
5. **冲突策略**：KB markdown 文件是 source of truth；KBSQL DB 是 cache。任何冲突以 KB 为准。
6. **遵循 dev-governance Phase 1-7 流程 + Phase 8 跨审计**

---

## 架构图

```
                  ┌─────────────────────────────────┐
                  │   Hogwarts-KB (笔记真相源)       │
                  │   ~/Hogwarts-Knowledge-Base      │
                  │   ┌────────┐  ┌──────────┐      │
                  │   │ wiki/  │  │raw-srcs/ │      │
                  │   └───┬────┘  └────┬─────┘      │
                  └───────┼────────────┼────────────┘
                          │ watch       │ read
                          ▼             ▼
       ┌────────────────────────────────────────────┐
       │   KBSQL bridge service (NEW v0.53)         │
       │  ┌─────────────┐  ┌────────────────────┐   │
       │  │ kb_watcher  │  │  multi_format       │   │
       │  │ (watchfiles)│  │  parser             │   │
       │  └──────┬──────┘  │  (markitdown+docling)│  │
       │         │         └──────────┬──────────┘   │
       │         ▼                    ▼              │
       │  ┌─────────────────────────────────────┐    │
       │  │  bridge_ingest stage (Celery, NEW)  │    │
       │  └────────────────┬────────────────────┘    │
       │                   ▼                         │
       │       (existing 7-stage pipeline runs)      │
       │                   │                         │
       │                   ▼                         │
       │  ┌──────────────────────────────────────┐   │
       │  │  kb_writer (writes back to KB)       │   │
       │  │  - summaries → wiki/summaries/       │   │
       │  │  - analyses  → wiki/analyses/        │   │
       │  │  - git commit + push                 │   │
       │  └──────────────────────────────────────┘   │
       └────────────────────────────────────────────┘
                   ▲                    ▲
                   │ MCP                │ REST
                   │ stdio/streamable   │ /v1/bridge/*
                   │                    │
       ┌───────────┴───────┐  ┌─────────┴─────────┐
       │  Claude Code      │  │  Scripts /        │
       │  Claude Desktop   │  │  Other agents     │
       └───────────────────┘  └───────────────────┘
```

---

## 任务分解（按 ROI + 依赖序）

### v0.53.0 — 基础设施 + 工具栈安装

**v0.53.0** — 工具栈安装 + bridge 服务骨架
- 创建 `services/bridge/` 目录结构
- 添加 `pyproject.toml` 依赖：markitdown, docling, watchfiles, mcp, sumy, keybert, spacy, yake, python-frontmatter, GitPython
- 创建 `services/bridge/bridge/__init__.py` + `main.py` + `config.py`
- 验收：`uv sync` 成功，`python -m bridge --version` 输出版本号

### v0.53.1 — Markdown 解析器（最小可用）
- `services/bridge/bridge/parsers/markdown_parser.py`：解析 KB 的 .md 文件，提取 frontmatter + content + wiki links
- 单元测试：covers Hogwarts-KB SCHEMA.md 中定义的 4 种 frontmatter（raw-sources/wiki/lessons/memory）
- 验收：能正确解析现有 KB 中 5 个不同类型的文件

### v0.53.2 — Multi-format parser（office + pdf + web）
- `services/ingestion-worker/worker/parsers/multi_format_parser.py`：调 markitdown 处理 docx/pptx/xlsx/csv/html，调 docling 处理 PDF/scanned PDF/image OCR
- 注册到 `parsers/__init__.py` 的 `PARSER_REGISTRY` 中（新 asset_type: `multi_format`）
- 单元测试：每种格式至少 1 个 fixture
- 验收：6 种新格式都能输出干净 markdown

### v0.53.3 — File watcher (kb_watcher)
- `services/bridge/bridge/watchers/kb_watcher.py`：用 watchfiles 监听 `HOGWARTS_KB_PATH/`
- 排除 `.git/`、`.obsidian/`、`.search-index.sqlite`、`.DS_Store`
- 检测到 .md 文件变化 → 计算 hash → 与 BridgeSyncRecord 对比 → 触发 `bridge_ingest` Celery task
- 单元测试：mock fs events，验证去重和 task dispatch
- 验收：手动改 KB 中一个文件，1 秒内被检测

### v0.53.4 — bridge_ingest Celery stage
- `services/pipeline-worker/worker/stages/bridge_ingest.py`：从 KB 文件创建/更新 Asset + AssetChunk → 触发 classify 等下游
- 新增 SQLAlchemy 模型：`BridgeSyncRecord`, `BridgeMapping`, `BridgeOperation`
- Alembic migration: `a6b7c8d9e0f1_add_bridge_tables.py`（revises z5a6b7c8d9e0）
- 单元测试：模拟 KB 文件变化，验证 DB 状态
- 验收：KB 中改一个文件，DB 中对应 Asset 被更新

### v0.53.5 — Local summarization + path classification
- `packages/bridge-utils/bridge_utils/summarize.py`：sumy LexRank 抽取式摘要（200 字以内）
- `packages/bridge-utils/bridge_utils/classify.py`：keybert + spacy NER → 路径建议（wiki/concepts/ vs wiki/howtos/ vs wiki/analyses/）
- LLM 兜底：当抽取式摘要相似度 < 0.5 时，调 GLM-4-flash 重写
- 单元测试：5 篇真实 wiki 页面，验证摘要质量 + 路径分类准确率
- 验收：≥80% 文件正确分类

### v0.53.6 — kb_writer (回写到 KB)
- `services/bridge/bridge/writers/kb_writer.py`：从 KBSQL DB 取处理结果 → 渲染 markdown（带 frontmatter） → 写入 `wiki/summaries/` 或 `wiki/analyses/`
- 用 GitPython 做 commit + push（commit prefix: `bridge:`，author: `kbsql-bridge[bot]`）
- 加锁：写之前检查 `.git/index.lock`，最多等待 30s
- 单元测试：mock git，验证文件写入 + commit 消息格式
- 验收：能成功 push 到 GitHub `feature/kbsql-bridge` 分支

### v0.53.7 — REST API endpoints
- `services/api/app/routers/bridge.py`：
  - `POST /v1/bridge/sync` — 手动触发全量同步
  - `POST /v1/bridge/ingest` — 上传单个文件 → bridge_ingest
  - `GET /v1/bridge/status` — 同步状态、最后操作日志
  - `GET /v1/bridge/mappings` — KB 路径 ↔ doc_id 映射列表
- 注册到 `main.py` (现有 27 router 列表 +1 = 28)
- OpenAPI 文档自动生成
- 单元测试：每个端点至少 1 个 happy-path + 1 个 error-path
- 验收：`curl http://localhost:8080/v1/bridge/status` 返回 JSON

### v0.53.8 — MCP server
- `services/mcp-server/mcp_server/server.py`：FastMCP server with tools:
  - `kb_search(query: str) -> list[KBPage]`
  - `kb_read(path: str) -> str`
  - `kb_write_summary(source_path: str, summary: str) -> str`
  - `kb_lineage(path: str) -> list[Session]`
- 双 transport：stdio（Claude Code/Desktop）+ streamable-http（远程 agent）
- 单元测试：用 mcp 官方 client 测试每个 tool
- 验收：在 Claude Code 中用 MCP 命令调通

### v0.53.9 — Hogwarts-KB 配套配置
- 在 Hogwarts-KB 加 `.bridge-config.yml`：定义 bridge 可写路径、ignore patterns、frontmatter 必填字段
- 加 `wiki/analyses/.bridge-managed`、`wiki/summaries/.bridge-managed` 标记文件（人类不直接编辑）
- 更新 SCHEMA.md：补充 bridge 写入约定章节
- 验收：人类阅读 SCHEMA.md 能理解 bridge 写入规则

### v0.53.10 — 端到端测试 + 文档
- E2E 测试：放一个 PDF 到 KB → 30s 内 KBSQL 处理完 → 摘要写回 KB → push 到 GitHub
- 用户文档：`docs/api/bridge-service.md`
- 运维文档：`docs/operations/bridge-deployment.md`
- 验收：所有 E2E 场景通过

### v0.53.11 — Phase 8 跨审计 + 修复
- 派发 3 个 Sub-agent（spec / quality / completeness）
- 整合报告 → `docs/audits/v0.53.11-bridge-audit.md`
- 修复所有 Critical/High 发现
- 重审直到收敛
- 验收：审计健康度 ≥ B+

### v0.53.12 — 封板 + push
- 更新 VERSION → `0.53.12`
- 更新 CHANGELOG.md
- 更新 TODO_NEXT.md → 指向 v0.54 候选
- 在 Hogwarts-KB 写交接文档
- git push 两个仓库
- 验收：GitHub PR 链接 + 两边 main branch 显示 bridge 已合入

---

## 验收清单（封板前必须全部 ✅）

- [ ] bridge 服务能启动 + 监听 KB 文件变化
- [ ] markitdown 能转换 docx/pptx/xlsx/csv/html
- [ ] docling 能转换 PDF/扫描 PDF/图片 OCR
- [ ] 本地摘要工具不调 LLM 也能产出 200 字摘要
- [ ] KBSQL 处理结果能写回 KB 并 push 到 GitHub
- [ ] MCP server 能被 Claude Code 调用
- [ ] REST API 能被 curl 调用
- [ ] GLM_API_KEY 严格模式生效（不会回退到 OpenAI）
- [ ] 现有 7 stage pipeline 没有破坏（回归测试通过）
- [ ] 现有 27 router 没有破坏（API 测试通过）
- [ ] 现有 6 parser 没有破坏（ingestion 测试通过）
- [ ] 没有引入 AGPL 依赖
- [ ] Phase 8 跨审计健康度 ≥ B+
- [ ] 两个仓库都 push 到 GitHub feature 分支

---

## 依赖与升级风险

### 新增 Python 依赖（pyproject.toml）
```
markitdown[all]
docling
trafilatura
playwright
yt-dlp
faster-whisper
scenedetect
whisperx
sumy
keybert
spacy
yake
python-frontmatter
watchfiles
mcp[cli]
GitPython
```

### 新增系统依赖
```
ffmpeg, tesseract, pandoc (optional), ocrmypdf (optional)
```

### 风险与回滚策略
- 若 markitdown / docling 安装失败：bridge 服务降级为 markdown-only 模式（仅处理 .md 文件）
- 若 watchfiles 在某些 macOS 版本不稳定：回退 watchdog（已加为 fallback）
- 若 MCP SDK API 与文档不符：先用 REST API 走通，MCP 留 v0.54 再加

---

## 决策记录链接

- 工具栈选型：[wiki/analyses/kbsql-bridge-toolkit-research.md](../../../Hogwarts-Knowledge-Base/wiki/analyses/kbsql-bridge-toolkit-research.md)
- 架构审计：[wiki/analyses/kbsql-v053-pre-impl-audit.md](../../../Hogwarts-Knowledge-Base/wiki/analyses/kbsql-v053-pre-impl-audit.md)
- 上一版交接：[v0.52 TODO_NEXT.md](../../TODO_NEXT.md)（封板时会被覆盖）

---

## 时间预算

- 研究 + 计划: 30 分钟（已完成）
- v0.53.0 ~ v0.53.6 实现：~3 小时（自动模式）
- v0.53.7 ~ v0.53.10 实现 + 测试：~2 小时
- v0.53.11 跨审计 + 修复：~1.5 小时（多轮）
- v0.53.12 封板 + push：~30 分钟
- **总计**: ~7-8 小时（睡眠时间内自动执行）

---

## 架构决策记录（ADR — 在 Phase 8 审计后追加）

### ADR-001: multi_format_parser 放在 services/bridge/ 而非 services/ingestion-worker/

**Phase 8 Stage 1 审计指出原计划 §v0.53.2 的位置（ingestion-worker）与实际位置（bridge）不符。
经评估后维持当前位置，原因如下：**

- **职责分离**：现有 `services/ingestion-worker/worker/parsers/` 服务于 KBSQL 的"任务式上传管线"
  （用户通过 REST POST /v1/ingestion 上传文件 → asset → chunk → 7 stage 处理）。bridge 服务的
  `multi_format_parser` 用于**文件系统监听场景**（用户在 Hogwarts-KB 目录直接放文件 → fs watcher
  → IR）。两个使用语境不同，参数化（如 LLM 提供方、并发模型）也不同。
- **避免破坏性修改**：将新 parser 注入现有 `PARSER_REGISTRY` 需要修改 `parsers/__init__.py` —
  这违反 "不破坏现有功能" 的硬约束。
- **测试隔离**：bridge 自带的 53 单元测试不需要启动 Celery；放在 ingestion-worker 中将引入
  Celery 启动开销。
- **代码复用路径**：v0.54 当 bridge_ingest Celery stage 落地时，可以从 `bridge.parsers` 导入
  `parse_file()`，再封装为 ingestion-worker 兼容的 parser 适配器。这种"共享底层，分别封装"的
  模式比强行共用注册表更清晰。

### ADR-002: bridge_ingest Celery stage 推迟到 v0.54

**Phase 8 Stage 1+3 审计均指出此 stage 在 v0.53 缺失。维持当前现状（推迟），理由：**

- **范围控制**：v0.53 的 ROI 重点是"双协议+本地 NLP+安全 git 写回" — 这三块能让 Claude Code/
  Desktop 立即开始用。Celery stage 是更深层次的"自动 DB 持久化"，依赖 alembic migration 已部署
  + Celery broker 已运行 + 解析结果到 Asset/AssetChunk 的 schema mapping。这三个前置条件中至少
  alembic migration 还没在用户的 Aiven Postgres 上 apply。
- **替代路径已足够**：v0.53 的 REST/MCP write 接口已经可以"显式触发 KB ↔ KBSQL 数据流"，
  Claude agent 可以代替 Celery 在 prompt 周期内完成同步。
- **风险隔离**：bridge_ingest 一旦运行错误（例如 KB schema 不兼容），会污染整个 pipeline 的
  Job/Asset 表。v0.53 跳过此 stage 让用户在试用阶段没有 DB-side blast radius。

**v0.54 任务**：
- `services/pipeline-worker/worker/stages/bridge_ingest.py`（stage 0）
- 在 `bridge.tasks` 添加 `bridge_ingest` Celery task
- 修改 `bridge.watchers.kb_watcher.run_watcher()` 默认注入 enqueue_fn
- 移除 `/v1/bridge/mappings` 的 stub 注释

### ADR-003: Auth on bridge write endpoints 推迟到 v0.54

`POST /v1/bridge/write/*` 暂无 admin-only 校验。原因：v0.53 的 `BridgeSettings.writer_allowed_paths`
已经把破坏面缩到只有两个目录；同时 CSRF 中间件（已生效）阻止了非 XHR 调用。完整 RBAC 要等
v0.54 的 `Depends(require_permission("bridge:write"))` 中间件落地。

---

*Drafted by Claude Code 2026-04-19 02:30 in autonomous mode following dev-governance v1.4*
*ADRs added after Phase 8 audit, 2026-04-19 06:00*
