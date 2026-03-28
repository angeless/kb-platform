# KB Platform v0.43 版本开发任务计划

**文档编号**: PLAN-2026-03-24-v043
**版本**: V3.0（规范完整版，符合 §2.5 全部要求）
**日期**: 2026-03-24
**基线 commit**: main HEAD (v0.42.10，含 0.42.11 / 0.42.12 补丁)
**基线分支**: main
**依据**: 产品北极星（docs/tech-specs/product-north-star.md）+ 代码审计结论（2026-03-24）
**作者**: 产品 Owner

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.42.12 现有代码增量修复和增强。禁止重构无关模块、禁止重写已有业务逻辑、禁止变更已有 API 契约（除非本计划明确要求）。

### 1.2 继承已有能力

以下 v0.42 完成的能力全部继承不变：

- **`services/api/`** — FastAPI 主服务：认证（JWT + refresh token）、CSRF 中间件、SSRF 防护、搜索（全文+语义）、QA（流式 SSE）、审核工作流、跨库索引、多库路由
- **`services/ingestion-worker/`** — 解析工作器：text / pdf parser 已稳定；asr / ocr parser 代码存在但有静默失败缺陷（本版本修复）
- **`services/pipeline-worker/`** — 9 阶段知识整合流水线（含 MECE 门禁、增量五分类）
- **`services/ai-orchestrator/`** — LLM 编排服务
- **`packages/shared-models/`** — 所有 SQLAlchemy 模型（project / architecture / knowledge_doc / asset / cross_reference 等）
- **`packages/shared-schemas/`** — Pydantic 请求/响应模型
- **`apps/web/`** — Next.js 15 前端：三栏 Wiki 视图、认证流程、搜索、QA、审核中心、跨库引用页

### 1.3 最小改动原则

每个任务只改必须改的文件。如果发现无关问题，记录到衍生建议但不执行。

### 1.4 任务领取规则

每次只能领取一个任务。完成后按第十一章格式汇报，确认后再领下一个。

---

## 第二章 当前阶段事实

### 2.1 项目目标

将多模态原始资料自动整理为可追溯、可维护、可被 AI 使用的结构化知识系统。平台本质是带知识拆解和结构化层的数据库，对外提供输入接口（接收多模态内容）和输出接口（Agent 可检索）。

### 2.2 当前基线

- **版本**: v0.42.10（含 v0.42.11 / v0.42.12 补丁，共 12 个任务已完成）
- **分支**: main

### 2.3 代码审计发现的问题（v0.43 修复目标）

| 问题 | 严重程度 | 现象 |
|------|---------|------|
| `.docx` 文件走 PDF 解析器，实际失败 | P0 Bug | 上传 Word 文件，任务显示 completed，但 asset_chunks 为空 |
| OCR/ASR 依赖缺失时静默返回空 | P0 Bug | 上传图片/音频，任务显示 completed，但无内容，用户无感知 |

### 2.4 v0.43 新增能力

| 能力 | 说明 |
|------|------|
| Agent 输出接口 | API Key 认证 + `/v1/agent/search` + `/v1/agent/ask`，外部系统可无 session 调用 |
| 知识图谱可视化 | `GET /v1/projects/{id}/graph` + 前端交互图谱，核心产物的直接呈现 |

---

## 第三章 本轮目标与边界

### 3.1 版本主题

**v0.43：输入管线修复 + 输出接口标准化**

### 3.2 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 |
|----------|--------|------|------|
| v0.43.1 | Word 解析器修复（.docx 当前走错解析器导致数据丢失） | P0 | Planned |
| v0.43.2 | OCR/ASR 静默失败修复（依赖缺失时应明确报错） | P0 | Planned |
| v0.43.3 | Agent 输出接口（API Key + /agent/search + /agent/ask） | P1 | Planned |
| v0.43.4 | 知识图谱 API + 前端可视化 | P1 | Planned |
| v0.43.5 | 全量回归验收 | P0 | Planned |

### 3.3 明确不做什么

1. **不做**多轮对话/聊天界面（是"用"知识库，不是"建"知识库）
2. **不做**文件在线预览（UI 体验优化，与核心链路无关）
3. **不做**知识质量评分（没有真实用户数据前属于过早优化）
4. **不做**通知系统完善（不影响核心链路）
5. **不做**视频解析（工作量大，当前无明确需求）
6. **不做** `.doc` 旧格式转换（标记 unsupported，避免引入 LibreOffice 依赖）

---

## 第四章 优先级与顺序

| 序号 | 任务版本号 | 任务名称 | 优先级 | 依赖 | 预估工时 |
|:---:|:---:|---|:---:|:---:|:---:|
| 1 | v0.43.1 | Word 解析器修复 | P0 | 无 | 6h |
| 2 | v0.43.2 | OCR/ASR 静默失败修复 | P0 | 无 | 5h |
| 3 | v0.43.3 | Agent 输出接口 | P1 | 无 | 12h |
| 4 | v0.43.4 | 知识图谱 API + 可视化 | P1 | 无 | 14h |
| 5 | v0.43.5 | 全量回归验收 | P0 | v0.43.1–v0.43.4 | 6h |

**总预估**：~43h（约 5–6 个工作日）

---

## 第五章 各任务详细定义

---

### v0.43.1：Word 解析器修复

**任务版本号**：v0.43.1
**所属功能项**：v0.43.0 — 输入管线修复
**优先级**：P0

---

#### 需求定义

**目标**：修复 `.docx` 文件上传后数据完全丢失的 bug，新增独立的 Word 解析器，`.doc` 旧格式标记为 unsupported。

**问题根因**：`services/ingestion-worker/worker/parsers/__init__.py` 中 `"doc": pdf_parser` 将所有 Word 文件路由到 PDF 解析器。pymupdf 无法读取 .docx（zip 格式），会报错或返回空，任务状态依然显示 completed，但 `asset_chunk` 表中无任何记录。

**输入**：
- 上传 `.docx` 文件到任意项目
- 文件存储在 MinIO，路径在 `asset.object_path`，`asset.asset_type = "doc"`

**输出**：
- `asset_chunk` 表中有对应文档的文本块记录
- `asset.parse_status = "parsed"`
- `job.status = "completed"`

---

#### 改动范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `services/ingestion-worker/worker/parsers/word_parser.py` | 新增 | Word 解析器主体 |
| `services/ingestion-worker/worker/parsers/__init__.py` | 修改 | 注册 word_parser，区分 docx / doc |
| `services/ingestion-worker/requirements.in` | 修改 | 添加 python-docx 依赖 |
| `services/ingestion-worker/tests/test_word_parser.py` | 新增 | 单元测试 |
| VERSION / CHANGELOG / TODO_NEXT | 修改 | 收尾 |

---

#### 新增 / 变更数据库表

无。本任务不涉及数据库表结构变更，仅影响 `asset_chunk` 表的数据填充（由解析器写入，表结构已存在）。

---

#### API 定义

无新增 API。本任务修改解析器代码，不涉及新增 HTTP 端点。

---

#### 业务规则

**word_parser.parse(content: bytes, filename: str) → list[dict]**

第 1 步：用 `python-docx` 打开 `io.BytesIO(content)`。若打开失败（非 .docx 格式），抛出 `ValueError("不是有效的 .docx 文件: {filename}")`。

第 2 步：遍历文档的所有段落（`doc.paragraphs`）：
- 跳过空段落（`para.text.strip() == ""`）
- 取 `para.style.name` 判断标题层级：`Heading 1` → `heading_level=1`；`Heading 2` → `heading_level=2`；`Heading 3` → `heading_level=3`；其余 → `heading_level=0`（正文）
- 每个非空段落构造一个 chunk dict

第 3 步：按 `heading_level` 分组合并：同一标题下的正文段落合并为一个 chunk，直到遇到下一个同级或更高级标题。chunk 的 `page_or_timestamp` 记为 `"para-{起始段落序号}"`。

第 4 步：如果合并后总字数 > 3000，按双换行拆分为子 chunk，`page_or_timestamp` 记为 `"para-{起始}-part-{子序号}"`。

第 5 步：返回 chunk list，每个 chunk 结构：
```python
{
    "content_text": str,           # 合并后的文本
    "page_or_timestamp": str,      # "para-N" 或 "para-N-part-M"
    "tags": {
        "source_type": "docx",
        "filename": str,
        "heading_level": int,      # 0=正文, 1/2/3=对应标题级别
        "heading_text": str | None # 所属标题文本，正文段落为 None
    }
}
```

**`__init__.py` 路由变更规则**：
- `asset_type == "docx"` → `word_parser`
- `asset_type == "doc"` → `None`（返回 None，tasks.py 中会标记为 `unsupported`）
- 原有 `"doc": pdf_parser` 删除

---

#### 验收标准

- [ ] 上传包含标题（H1/H2）+ 正文的 .docx，`asset_chunk` 表中有 ≥1 条记录，tags 含 `source_type: "docx"`
- [ ] 上传带多个 H2 节的 .docx，每个 H2 节内容在独立 chunk 中，`heading_text` 字段有值
- [ ] 上传空 .docx（无任何段落），返回 0 chunks，`asset.parse_status = "parsed"`（不报错）
- [ ] 上传 .doc 旧格式文件，`asset.parse_status = "unsupported"`，任务 `job.status = "completed"`（不是 failed）
- [ ] 上传损坏的 .docx（非法 zip），`asset.parse_status = "failed"`，error_message 含 "不是有效的 .docx 文件"
- [ ] `pytest services/ingestion-worker/tests/test_word_parser.py` 全部通过（≥5 个测试用例）

---

#### 依赖关系

- 无前置任务
- 可与 v0.43.2 并行执行

---

#### 工作范围

**包含**：.docx 解析（python-docx）、heading 层级提取、分组合并、.doc 标记 unsupported

**不包含**：.docx 转 PDF 再解析、LibreOffice 依赖、图片/表格提取（只处理文本段落）

---

#### 原子级拆解

**T-43-01-A：新增 `word_parser.py`**
- 改动文件：`services/ingestion-worker/worker/parsers/word_parser.py`（新增）
- 改动内容：实现 `parse(content, filename)` 函数，python-docx 按段落解析，heading 分组合并，超长拆分
- 改动量：~80 行
- 验收：手动调用 `parse(docx_bytes, "test.docx")` 返回正确 chunks

**T-43-01-B：更新解析器路由表**
- 改动文件：`services/ingestion-worker/worker/parsers/__init__.py`（修改）
- 改动内容：删除 `"doc": pdf_parser`，新增 `"docx": word_parser`，`.doc` 不注册（get_parser 返回 None）
- 改动量：~5 行修改
- 验收：`get_parser("docx")` 返回 `word_parser`；`get_parser("doc")` 返回 `None`

**T-43-01-C：添加 python-docx 依赖**
- 改动文件：`services/ingestion-worker/requirements.in`（修改）
- 改动内容：新增一行 `python-docx>=1.1.0`
- 改动量：1 行
- 验收：`pip install -r requirements.lock` 后 `import docx` 不报错

**T-43-01-D：单元测试**
- 改动文件：`services/ingestion-worker/tests/test_word_parser.py`（新增）
- 改动内容：测试用例：①正常 .docx 有 chunks；②含 H1/H2 的 chunks 有 heading_text；③空文档返回 []；④.doc 走 get_parser 返回 None；⑤损坏文件抛 ValueError
- 改动量：~70 行
- 验收：`pytest tests/test_word_parser.py -v` 全部通过

**T-43-01-E：收尾**
- 改动文件：VERSION（→ 0.43.1）、CHANGELOG.md（新增条目）、TODO_NEXT.md（更新状态）
- 改动量：~15 行
- 验收：VERSION = "0.43.1"；CHANGELOG 最新条目描述本次修复

---

### v0.43.2：OCR/ASR 静默失败修复

**任务版本号**：v0.43.2
**所属功能项**：v0.43.0 — 输入管线修复
**优先级**：P0

---

#### 需求定义

**目标**：将 OCR（图片）和 ASR（音频）解析器的"依赖缺失时静默返回空"行为改为"明确报错"，并在 Docker 镜像中补全系统依赖，确保生产环境 OCR/ASR 可用。

**问题根因**：`ocr_parser.py` 和 `asr_parser.py` 在 `pytesseract`、`Pillow`、`whisper` 未安装时执行 `return []`。`tasks.py` 收到空 chunks 后将 `asset.parse_status` 置为 `"parsed"`，`job.status` 置为 `"completed"`。用户看到任务成功，但知识库中没有这份文件的任何内容。

**输入**：
- 上传图片（PNG/JPG 等）或音频（MP3/WAV 等）到项目
- `asset.asset_type` 分别为 `"image"` 或 `"audio"`

**输出（修复后期望行为）**：
- Tesseract/ffmpeg/whisper 未安装 → `asset.parse_status = "failed"`，`job.status = "failed"`，`job.error_message` 含明确说明
- 依赖已安装 → 正常解析，chunks 写入 DB

---

#### 改动范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `services/ingestion-worker/worker/parsers/ocr_parser.py` | 修改 | 依赖缺失时 raise RuntimeError |
| `services/ingestion-worker/worker/parsers/asr_parser.py` | 修改 | 依赖缺失时 raise RuntimeError |
| `services/ingestion-worker/Dockerfile`（或 docker-compose 中 ingestion-worker 的构建配置） | 修改 | apt 安装 tesseract-ocr tesseract-ocr-chi-sim ffmpeg |
| `services/ingestion-worker/tests/test_parsers.py` | 修改 | 更新 mock 测试，验证 RuntimeError 被抛出 |
| VERSION / CHANGELOG / TODO_NEXT | 修改 | 收尾 |

---

#### 新增 / 变更数据库表

无。不涉及表结构变更。

---

#### API 定义

无新增 API。

---

#### 业务规则

**ocr_parser.py 修改规则**：

将以下三处 `return []` 改为 `raise RuntimeError(...)`:

1. `except ImportError` (Pillow 缺失)：`raise RuntimeError("OCR 依赖缺失：Pillow 未安装，请在 ingestion-worker 容器中运行 pip install Pillow")`
2. `except ImportError` (pytesseract 缺失)：`raise RuntimeError("OCR 依赖缺失：pytesseract 未安装，请在 ingestion-worker 容器中运行 pip install pytesseract")`
3. `TesseractNotFoundError`：`raise RuntimeError("OCR 依赖缺失：系统未安装 Tesseract，请在容器中运行 apt-get install tesseract-ocr")`

`tasks.py` 已有完整的 try/except，会捕获 RuntimeError 并将 `asset.parse_status = "failed"`，`job.error_message = str(e)`，无需修改 tasks.py。

**asr_parser.py 修改规则**：

1. `except ImportError` (whisper 缺失)：`raise RuntimeError("ASR 依赖缺失：openai-whisper 未安装，请在 ingestion-worker 容器中运行 pip install openai-whisper")`
2. ffmpeg 不可用时（model.transcribe 抛出 ffmpeg 相关异常）：已在 `except Exception as e` 中被捕获，改为 re-raise：`raise RuntimeError(f"ASR 转录失败（可能缺少 ffmpeg）：{e}")`

**Dockerfile 修改内容**（在 apt-get install 阶段追加）：
```
tesseract-ocr \
tesseract-ocr-chi-sim \
ffmpeg \
```

---

#### 验收标准

- [ ] 在未安装 Tesseract 的环境下上传 PNG，`asset.parse_status = "failed"`，`job.error_message` 含 "Tesseract"
- [ ] 在未安装 ffmpeg 的环境下上传 MP3，`asset.parse_status = "failed"`，`job.error_message` 含 "ffmpeg" 或 "ASR"
- [ ] docker-compose up 启动 ingestion-worker 后，容器内 `tesseract --version` 和 `ffmpeg -version` 均有输出
- [ ] 上传真实 PNG 图片（含文字），chunks 被写入 DB，`tags.source_type = "image"`
- [ ] `pytest services/ingestion-worker/tests/test_parsers.py` 全部通过

---

#### 依赖关系

- 无前置任务
- 可与 v0.43.1 并行执行

---

#### 工作范围

**包含**：ocr_parser / asr_parser 错误处理改造、Docker 镜像系统依赖补全

**不包含**：更换 OCR 引擎（仍用 Tesseract）、更换 ASR 模型（仍用 Whisper）、修改 tasks.py 错误处理逻辑（已有）

---

#### 原子级拆解

**T-43-02-A：修改 `ocr_parser.py`**
- 改动文件：`services/ingestion-worker/worker/parsers/ocr_parser.py`（修改）
- 改动内容：3 处 `return []` 改为 `raise RuntimeError("...")`，附带具体安装指引
- 改动量：~10 行修改
- 验收：mock `pytesseract` 缺失，parse 调用抛出 RuntimeError

**T-43-02-B：修改 `asr_parser.py`**
- 改动文件：`services/ingestion-worker/worker/parsers/asr_parser.py`（修改）
- 改动内容：`ImportError` 处改为 raise；transcribe 异常改为 re-raise RuntimeError
- 改动量：~10 行修改
- 验收：mock `whisper` 缺失，parse 调用抛出 RuntimeError

**T-43-02-C：补全 Dockerfile 系统依赖**
- 改动文件：`services/ingestion-worker/Dockerfile`（修改，或 docker-compose.yml 中对应 build 配置）
- 改动内容：apt-get install 阶段添加 `tesseract-ocr tesseract-ocr-chi-sim ffmpeg`
- 改动量：~3 行
- 验收：`docker build` 后容器内 `tesseract --version` 有输出

**T-43-02-D：更新测试**
- 改动文件：`services/ingestion-worker/tests/test_parsers.py`（修改）
- 改动内容：添加测试：mock pytesseract 缺失 → 期望 RuntimeError；mock whisper 缺失 → 期望 RuntimeError
- 改动量：~25 行新增
- 验收：`pytest tests/test_parsers.py -v` 全部通过

**T-43-02-E：收尾**
- 改动文件：VERSION（→ 0.43.2）、CHANGELOG.md、TODO_NEXT.md
- 改动量：~15 行
- 验收：VERSION = "0.43.2"

---

### v0.43.3：Agent 输出接口标准化

**任务版本号**：v0.43.3
**所属功能项**：v0.43.0 — 输出接口标准化
**优先级**：P1

---

#### 需求定义

**目标**：提供一套专为外部 Agent 设计的知识检索接口，使用 API Key 认证（不依赖 session cookie），包含知识检索和知识问答两个端点，并提供前端 API Key 管理页。

**输入**：
- HTTP 请求携带 `Authorization: Bearer <api_key>` 头
- 请求体包含 `project_id`、`query`（或 `question`）、`top_k`

**输出**：
- 检索端点：返回 top-k 相关知识文档及其 node_path 和来源素材
- 问答端点：返回同步 JSON 格式的 AI 回答及来源文档（非流式）

---

#### 改动范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `packages/shared-models/shared_models/api_key.py` | 新增 | ApiKey SQLAlchemy 模型 |
| `packages/shared-models/shared_models/__init__.py` | 修改 | 导出 ApiKey |
| `packages/shared-schemas/shared_schemas/api_key.py` | 新增 | ApiKey Pydantic schema |
| `infra/sql/alembic/versions/xxxx_add_api_key_table.py` | 新增 | Alembic migration |
| `services/api/app/routers/api_keys.py` | 新增 | API Key CRUD 路由 |
| `services/api/app/routers/agent.py` | 新增 | /v1/agent/* 路由 |
| `services/api/app/deps.py` | 修改 | 新增 `get_api_key_project` 依赖函数 |
| `services/api/app/main.py` | 修改 | 注册 api_keys router 和 agent router |
| `apps/web/src/app/(dashboard)/projects/[id]/settings/page.tsx` | 新增或修改 | API Key 管理 UI |
| `apps/web/src/lib/api.ts` | 修改 | 新增 API Key CRUD 的前端调用函数 |
| `docs/api/agent-api.md` | 新增 | Agent 调用接口文档 |
| VERSION / CHANGELOG / TODO_NEXT | 修改 | 收尾 |

---

#### 新增数据库表

**表名**：`api_key`

| 字段名 | 类型（PostgreSQL） | 约束 | 说明 |
|-------|-----------------|------|------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | 主键 |
| project_id | UUID | NOT NULL, FK → project.id ON DELETE CASCADE | 所属项目，Project 级别隔离 |
| tenant_id | UUID | NOT NULL, FK → tenant.id | 所属租户，用于安全校验 |
| name | VARCHAR(100) | NOT NULL | Key 的友好名称，用户自定义 |
| key_hash | VARCHAR(64) | NOT NULL, UNIQUE | SHA-256(raw_key)，不存储原始 key |
| key_prefix | VARCHAR(8) | NOT NULL | raw_key 前 8 位，用于列表页识别（如 "kb_abc123"） |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否有效，撤销时设为 FALSE |
| created_by | UUID | NOT NULL, FK → user.id | 创建者 |
| last_used_at | TIMESTAMPTZ | NULL | 最后一次使用时间，每次调用更新 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间（继承 Base） |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 更新时间（继承 Base） |

**索引**：
- `ix_api_key_project`：(project_id)
- `ix_api_key_hash`：(key_hash)，用于认证查找

**说明**：raw_key 格式为 `kb_{random_32_chars}`，仅在创建响应中返回一次，之后不可再查询。

---

#### 已有表变更

无。本任务不修改现有表字段。

---

#### API 定义

**API Key 管理（用户登录态，session cookie 认证）：**

| 方法 | 路径 | 权限 | 入参 | 说明 |
|------|------|------|------|------|
| POST | `/v1/projects/{project_id}/api-keys` | 已登录用户 + 项目成员 | body: `{ name: str }` | 创建 API Key，响应包含 raw_key（仅此一次） |
| GET | `/v1/projects/{project_id}/api-keys` | 已登录用户 + 项目成员 | — | 列出当前项目所有 API Key（不返回 raw_key，只返回 key_prefix） |
| DELETE | `/v1/projects/{project_id}/api-keys/{key_id}` | 已登录用户 + 项目成员 | — | 撤销指定 API Key（`is_active = FALSE`） |

**Agent 检索接口（API Key 认证）：**

| 方法 | 路径 | 权限 | 入参 | 说明 |
|------|------|------|------|------|
| POST | `/v1/agent/search` | 有效 API Key | body: `{ project_id: UUID, query: str, top_k: int = 5 }` | 语义检索知识文档 |
| POST | `/v1/agent/ask` | 有效 API Key | body: `{ project_id: UUID, question: str, top_k: int = 5 }` | RAG 问答，返回同步 JSON（非流式） |

**API Key 认证规则（`get_api_key_project` 依赖）**：
1. 从 `Authorization: Bearer <token>` 头提取 token
2. 计算 `SHA-256(token)` → `key_hash`
3. 查 `api_key` 表：`key_hash = ?` AND `is_active = TRUE`
4. 若未找到 → 401，`{"error": "INVALID_API_KEY", "message": "API Key 无效或已撤销"}`
5. 若找到 → 异步更新 `last_used_at = now()`
6. 验证 `api_key.project_id == body.project_id`，不匹配 → 403
7. 返回 `(api_key, project_id, tenant_id)` 供路由使用

---

#### 业务规则

**POST /v1/projects/{project_id}/api-keys（创建 Key）**：

第 1 步：验证当前用户是该项目的成员（现有 project 权限逻辑）。若不是 → 403。

第 2 步：生成 `raw_key = "kb_" + secrets.token_urlsafe(24)`（总长约 35 字符）。

第 3 步：计算 `key_hash = hashlib.sha256(raw_key.encode()).hexdigest()`。

第 4 步：取 `key_prefix = raw_key[:8]`。

第 5 步：写入 `api_key` 表。

第 6 步：响应 201，body 包含 `{ id, name, key_prefix, raw_key, created_at }`。**raw_key 仅此响应中出现一次**。

---

**POST /v1/agent/search（Agent 检索）**：

第 1 步：通过 `get_api_key_project` 依赖验证 API Key，获取 `project_id` 和 `tenant_id`。

第 2 步：调用现有 `SearchService.search(project_id, query, top_k, tenant_id)`（复用已有搜索逻辑）。

第 3 步：对每条搜索结果，查询 `knowledge_doc` 的 `node_id`，再从 `architecture_node` 向上递归获取 `node_path`（`[根节点名, ..., 叶节点名]`）。

第 4 步：查询每条 `knowledge_doc` 关联的 `source_ref → asset_chunk → asset`，取 `asset.filename` 列表。

第 5 步：响应 200：
```json
{
  "results": [
    {
      "doc_id": "uuid",
      "title": "文档标题",
      "content_snippet": "相关片段（前 500 字）",
      "relevance_score": 0.92,
      "node_path": ["根节点", "子节点", "文档所在节点"],
      "source_assets": ["原始素材文件名1", "文件名2"]
    }
  ],
  "query": "原始 query",
  "total": 5
}
```

---

**POST /v1/agent/ask（Agent 问答）**：

第 1 步：通过 `get_api_key_project` 依赖验证 API Key。

第 2 步：调用现有 `QAService.ask(project_id, question, top_k)`（非流式版本，已有）。

第 3 步：响应 200：
```json
{
  "answer": "AI 回答文本",
  "source_docs": [
    { "doc_id": "uuid", "title": "文档标题", "node_path": ["根", "子"] }
  ],
  "question": "原始问题"
}
```

---

#### 前端变更

**新增 / 修改页面**：`apps/web/src/app/(dashboard)/projects/[id]/settings/page.tsx`

新增"API 访问"区块，包含：
- API Key 列表：展示 `name`、`key_prefix`、`created_at`、`last_used_at`（若有）、撤销按钮
- 创建 API Key 按钮：弹窗输入 name → 调用创建 API → 弹窗展示 raw_key，提示"请立即复制，关闭后不可再查看"
- 撤销确认弹窗：确认后调用 DELETE

---

#### 验收标准

- [ ] `POST /v1/projects/{id}/api-keys` 返回 raw_key，再次 GET 列表只能看到 key_prefix，不能看到 raw_key
- [ ] 使用有效 API Key 调用 `POST /v1/agent/search`，返回含 node_path 和 source_assets 的结果
- [ ] 使用无效 API Key 调用，返回 401，error = "INVALID_API_KEY"
- [ ] API Key 属于 project_a，用 project_b 的 project_id 请求，返回 403
- [ ] `DELETE /v1/projects/{id}/api-keys/{key_id}` 后，该 Key 调用返回 401
- [ ] `POST /v1/agent/ask` 返回同步 JSON（不是 SSE 流），包含 answer 和 source_docs
- [ ] 前端项目设置页可创建 Key，raw_key 弹窗一次性展示
- [ ] `api_key.last_used_at` 在每次调用后更新

---

#### 依赖关系

- 无前置任务

---

#### 工作范围

**包含**：api_key 表、3 个管理端点、2 个 agent 端点、前端管理 UI、接口文档

**不包含**：API Key 速率限制（v0.44 考虑）、API Key 过期机制（v0.44 考虑）、Tenant 级别 Key

---

#### 原子级拆解

**T-43-03-A：ApiKey 数据模型 + Alembic migration**
- 改动文件：`packages/shared-models/shared_models/api_key.py`（新增）；`shared_models/__init__.py`（修改，添加 ApiKey 导出）；`infra/sql/alembic/versions/xxxx_add_api_key.py`（新增）
- 改动内容：ApiKey model（9 个字段，见上方表格）；migration up：CREATE TABLE api_key + 两个索引；migration down：DROP TABLE api_key
- 改动量：~60 行（model 30 行 + migration 30 行）
- 验收：`alembic upgrade head` 成功；`alembic downgrade -1` 成功

**T-43-03-B：ApiKey Pydantic schema**
- 改动文件：`packages/shared-schemas/shared_schemas/api_key.py`（新增）
- 改动内容：`ApiKeyCreateRequest(name: str)`；`ApiKeyCreateResponse(id, name, key_prefix, raw_key, created_at)`；`ApiKeyListItem(id, name, key_prefix, is_active, created_at, last_used_at)`
- 改动量：~30 行
- 验收：schema 可 import，字段类型正确

**T-43-03-C：API Key CRUD 路由**
- 改动文件：`services/api/app/routers/api_keys.py`（新增）；`services/api/app/main.py`（修改，注册 router）
- 改动内容：POST 创建（生成 raw_key + hash + 写 DB）；GET 列表；DELETE 撤销（`is_active = FALSE`）
- 改动量：~90 行
- 验收：三个端点通过 curl 测试，符合业务规则

**T-43-03-D：`get_api_key_project` 认证依赖**
- 改动文件：`services/api/app/deps.py`（修改）
- 改动内容：新增 `get_api_key_project(authorization: str = Header(...), db: AsyncSession = Depends(get_db))` 依赖，实现 SHA-256 hash 查表、is_active 校验、last_used_at 更新
- 改动量：~40 行
- 验收：有效 Key → 返回 api_key 对象；无效 Key → raise 401；已撤销 Key → raise 401

**T-43-03-E：Agent 路由（search + ask）**
- 改动文件：`services/api/app/routers/agent.py`（新增）；`services/api/app/main.py`（修改，注册 router）
- 改动内容：`POST /v1/agent/search`（调用 SearchService + 构建 node_path + source_assets）；`POST /v1/agent/ask`（调用 QAService.ask 非流式版）
- 改动量：~100 行
- 验收：用有效 API Key curl 两个端点均返回预期格式

**T-43-03-F：前端 API Key 管理 UI**
- 改动文件：`apps/web/src/app/(dashboard)/projects/[id]/settings/page.tsx`（新增或修改）；`apps/web/src/lib/api.ts`（修改，新增 3 个 API 调用函数）
- 改动内容：API Key 列表、创建弹窗（含 raw_key 一次性展示）、撤销确认弹窗
- 改动量：~120 行
- 验收：前端页面可创建 Key 并展示 raw_key；撤销后列表刷新

**T-43-03-G：接口文档**
- 改动文件：`docs/api/agent-api.md`（新增）
- 改动内容：认证方式说明、两个端点的完整 request/response 示例、curl 调用示例、错误码说明
- 改动量：~80 行 Markdown
- 验收：文档可读，示例可直接复制执行

**T-43-03-H：收尾**
- 改动文件：VERSION（→ 0.43.3）、CHANGELOG.md、TODO_NEXT.md
- 改动量：~15 行
- 验收：VERSION = "0.43.3"

---

### v0.43.4：知识图谱 API + 前端可视化

**任务版本号**：v0.43.4
**所属功能项**：v0.43.0 — 核心产物呈现
**优先级**：P1

---

#### 需求定义

**目标**：以可交互图形呈现项目的知识结构（架构节点关系 + 文档跨库引用关系），并提供 API 供外部系统了解知识库组织结构。

**输入**：`GET /v1/projects/{project_id}/graph`（session cookie 或 API Key 认证）

**输出**：
- 后端：nodes（知识文档列表）+ edges（父子关系 + 跨库引用关系）的 JSON
- 前端：react-flow 交互图谱，点击节点跳转到 Wiki 文档页

---

#### 改动范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `packages/shared-schemas/shared_schemas/graph.py` | 新增 | GraphNode / GraphEdge / GraphResponse schema |
| `services/api/app/routers/graph.py` | 新增 | GET /v1/projects/{id}/graph 路由 |
| `services/api/app/main.py` | 修改 | 注册 graph router |
| `apps/web/src/app/(dashboard)/projects/[id]/graph/page.tsx` | 新增 | 图谱页面 |
| `apps/web/src/components/wiki/knowledge-graph.tsx` | 新增 | react-flow 图谱渲染组件 |
| `apps/web/src/app/(dashboard)/projects/[id]/page.tsx` | 修改 | 项目详情页新增图谱入口 |
| `apps/web/package.json` | 修改 | 添加 reactflow 依赖 |
| VERSION / CHANGELOG / TODO_NEXT | 修改 | 收尾 |

---

#### 新增 / 变更数据库表

无。数据来源于已有的 `knowledge_doc`、`architecture_node`、`cross_reference` 表，不新增表。

---

#### API 定义

| 方法 | 路径 | 权限 | 入参 | 说明 |
|------|------|------|------|------|
| GET | `/v1/projects/{project_id}/graph` | 已登录用户（session cookie）或有效 API Key | 路径参数 project_id | 返回知识图谱节点和边数据 |

**Response 200**：
```json
{
  "nodes": [
    {
      "id": "doc_uuid",
      "label": "文档标题",
      "node_type": "doc",
      "node_path": ["根节点", "子节点", "叶节点"],
      "status": "approved"
    }
  ],
  "edges": [
    {
      "id": "edge_uuid",
      "source": "doc_uuid_a",
      "target": "doc_uuid_b",
      "edge_type": "parent_child"
    },
    {
      "id": "edge_uuid_2",
      "source": "doc_uuid_c",
      "target": "doc_uuid_d",
      "edge_type": "cross_ref",
      "relation_type": "related"
    }
  ],
  "node_count": 42,
  "edge_count": 18
}
```

---

#### 业务规则

**GET /v1/projects/{project_id}/graph**：

第 1 步：验证用户有访问该 project 的权限（已有 tenant_id 隔离）。

第 2 步：查询 `knowledge_doc` 表，`project_id = ?`，`status IN ('approved', 'draft')`，取 `id, title, node_id, status`。若文档数 > 500，只取 `status = 'approved'` 的文档（防止图谱过大导致前端卡顿）。

第 3 步：对每个文档，通过 `node_id` 递归查询 `architecture_node` 的父节点链，构建 `node_path = [根节点名, ..., 当前节点名]`。

第 4 步：同项目内，同一 `architecture_node` 下的文档视为"兄弟节点"，**不构建父子 edge**（父子关系由 node_path 隐含）。跨文档的直接引用（`cross_reference` 表，`source_doc_id` 和 `target_doc_id` 均在本项目内）构建 `edge_type = "cross_ref"`。

第 5 步：返回 `{ nodes, edges, node_count, edge_count }`。

---

#### 前端变更

**新增页面**：`/projects/{id}/graph`

- 页面顶部：项目名称 + "返回项目" 面包屑
- 主区域：react-flow 画布，充满可用高度
- 节点颜色：按 `node_path` 层级深度着色（level 0 深色，越深越浅）
- 边样式：`cross_ref` 边用蓝色虚线；若将来有父子边则用灰色实线
- 交互：缩放（鼠标滚轮）、拖拽、MiniMap（右下角缩略图）、点击节点跳转 `/projects/{id}/wiki/{doc_id}`
- 节点悬浮 Tooltip：展示 `title` + `node_path.join(" › ")`
- Loading 状态：骨架屏；Error 状态：错误提示 + 重试按钮

**修改页面**：`/projects/{id}`（项目详情页）

在 Quick Stats 卡片区新增"知识图谱"入口卡片，点击跳转 `/projects/{id}/graph`。

---

#### 验收标准

- [ ] `GET /v1/projects/{id}/graph` 返回正确的 nodes 和 edges，nodes 数量等于该项目 knowledge_doc 数量
- [ ] 每个 node 的 node_path 从根节点到当前节点完整
- [ ] cross_reference 表中的引用在 edges 中体现，edge_type = "cross_ref"
- [ ] 文档数 ≤ 100 时，图谱在 3s 内完成渲染
- [ ] 点击节点成功跳转到 Wiki 文档页
- [ ] 项目详情页有图谱入口卡片
- [ ] `npm run build` 无编译错误

---

#### 依赖关系

- 无前置任务
- 需在 v0.43.3 的 `main.py` 修改之前或之后独立完成（无文件冲突，均只新增 router 注册）

---

#### 原子级拆解

**T-43-04-A：GraphSchema**
- 改动文件：`packages/shared-schemas/shared_schemas/graph.py`（新增）
- 改动内容：`GraphNode(id, label, node_type, node_path, status)`；`GraphEdge(id, source, target, edge_type, relation_type?)`；`GraphResponse(nodes, edges, node_count, edge_count)`
- 改动量：~35 行
- 验收：schema 可 import，字段类型正确

**T-43-04-B：Graph API 后端**
- 改动文件：`services/api/app/routers/graph.py`（新增）；`services/api/app/main.py`（修改，注册 router）
- 改动内容：GET /v1/projects/{id}/graph，查询 knowledge_doc + architecture_node 递归 + cross_reference，构建 nodes 和 edges
- 改动量：~100 行
- 验收：curl 调用返回正确 JSON；node_path 正确；cross_ref edges 存在

**T-43-04-C：前端 graph/page.tsx**
- 改动文件：`apps/web/src/app/(dashboard)/projects/[id]/graph/page.tsx`（新增）；`apps/web/package.json`（修改，添加 reactflow）
- 改动内容：页面容器，调用 `/v1/projects/{id}/graph`，传入 KnowledgeGraph 组件，Loading/Error 状态处理
- 改动量：~55 行
- 验收：访问 `/projects/{id}/graph` 页面不报错，Loading 骨架屏可见

**T-43-04-D：KnowledgeGraph 组件（渲染）**
- 改动文件：`apps/web/src/components/wiki/knowledge-graph.tsx`（新增）
- 改动内容：react-flow ReactFlow 组件，将 nodes/edges 映射为 react-flow 的 node/edge 格式，按层级着色，MiniMap
- 改动量：~90 行
- 验收：传入 mock nodes/edges 数据，图谱正确渲染，节点颜色有层级差异

**T-43-04-E：节点交互（点击跳转 + 悬浮 Tooltip）**
- 改动文件：`apps/web/src/components/wiki/knowledge-graph.tsx`（修改，在 D 基础上）
- 改动内容：`onNodeClick` 调用 `router.push`；`nodeTypes` 中自定义节点包含悬浮 Tooltip（展示 node_path）
- 改动量：~35 行
- 验收：点击节点跳转到对应 Wiki 文档；鼠标悬浮展示节点路径

**T-43-04-F：项目详情页图谱入口**
- 改动文件：`apps/web/src/app/(dashboard)/projects/[id]/page.tsx`（修改）
- 改动内容：在 Quick Stats 区新增一个"知识图谱"卡片，点击跳转 `/projects/{id}/graph`
- 改动量：~15 行
- 验收：项目详情页可见图谱入口，点击跳转正确

**T-43-04-G：收尾**
- 改动文件：VERSION（→ 0.43.4）、CHANGELOG.md、TODO_NEXT.md
- 改动量：~15 行
- 验收：VERSION = "0.43.4"

---

### v0.43.5：全量回归验收

**任务版本号**：v0.43.5
**所属功能项**：v0.43.0 — 验收
**优先级**：P0

---

#### 验收范围

**新功能验收（v0.43 全部 4 项）**：

| 功能 | 核心验收点 |
|------|-----------|
| Word 解析 | 上传 .docx → chunks 正确入库；.doc → unsupported；损坏文件 → failed |
| OCR/ASR 失败可见 | 缺依赖 → 任务 failed + 明确 error_message |
| Agent API | API Key 认证 + 检索 + 问答接口全部通过；撤销后不可用 |
| 知识图谱 | API 返回正确 nodes/edges；前端渲染；点击跳转 |

**核心链路回归（v0.42 能力不退化）**：

| 能力 | 验收方式 |
|------|---------|
| 完整 Pipeline | 上传 PDF → 解析 → 架构生成 → 知识文档生成 → 可搜索 |
| 认证流程 | 注册 → 登录 → 刷新 token → 重置密码 全流程手工测试 |
| Wiki 浏览 | 三栏视图 / TOC / 面包屑 / 相关推荐 正常 |
| 搜索 | 关键词搜索 + 语义搜索 + 分页 正常 |
| 安全特性 | SSRF 防护（尝试请求内网 IP → 400）；登录 5 次失败 → 锁定 |

**收尾**：
- `docs/versions/v0.43-acceptance-report.md`（新增，记录验收结果）
- VERSION → 0.43.5
- CHANGELOG 汇总
- TODO_NEXT.md 重置为"v0.43 全部完成，等待 v0.44 计划"

---

## 第六章 实现约束

### 6.1 目录结构

- 新增模型：`packages/shared-models/shared_models/{name}.py`，导出到 `shared_models/__init__.py`
- 新增 schema：`packages/shared-schemas/shared_schemas/{name}.py`
- 新增路由：`services/api/app/routers/{name}.py`，在 `main.py` 注册
- 新增 migration：`infra/sql/alembic/versions/`，命名格式 `{timestamp}_{description}.py`

### 6.2 Migration 命名规范

格式：`{4位年月日4位时分}_{简短描述}.py`，如 `202603241030_add_api_key_table.py`

### 6.3 新 API 安全要求

- 所有新增 `/v1/agent/*` 端点必须经过 `get_api_key_project` 依赖认证
- Agent 端点不得绕过 tenant_id 隔离
- API Key 原始值仅返回一次，不得在 DB 或日志中存储

### 6.4 前端要求

- 使用 Next.js 15 + React 19 + TypeScript，符合现有 `apps/web/` 代码风格
- 新增页面必须有 Loading 和 Error 状态处理
- 图谱页面引入 `reactflow` 库，确认与现有依赖无冲突后再安装

---

## 第七章 任务领取规则

- 每次只能领取一个任务（v0.43.1 ~ v0.43.5 按序）
- 完成后按第十一章格式汇报，等待确认再领下一个
- 发现衍生问题仅记录，不擅自执行
- 连续两次审计有"高风险"项，停止并向用户反馈

---

## 第八章 测试要求

参见 `docs/tech-specs/testing-strategy.md`。

**本版本重点**：
- 后端测试：pytest，每个新增端点 ≥ 3 个测试用例（happy path + 认证失败 + 权限不足）
- 解析器测试：pytest，每个解析器 ≥ 5 个测试用例（正常 + 边界 + 错误）
- 前端测试：vitest，新增组件的渲染测试
- 不允许 mock DB 替代真实端点测试

---

## 第九章 版本号管理

参见 `docs/tech-specs/dev-governance-part1-version.md` §1.1–§1.4。

- 格式：`0.43.N`（N 从 1 递增）
- 每个原子任务完成后更新 VERSION 文件
- Commit message 格式：`feat(v0.43.N): <简要描述>`

---

## 第十章 文档产出要求

| 触发条件 | 必须更新的文档 |
|---------|-------------|
| 每个任务完成 | VERSION、CHANGELOG.md、TODO_NEXT.md |
| v0.43.3 完成 | `docs/api/agent-api.md` |
| v0.43.5 完成 | `docs/versions/v0.43-acceptance-report.md` |

---

## 第十一章 汇报格式

参见 `docs/tech-specs/dev-governance.md` §0.7（CLAUDE.md 第二部分开发报告格式）。

每个任务完成后按以下 9 项结构汇报：

1. 计划 / 当前迭代目标
2. 文件变更清单
3. 用户可见能力
4. 真实场景验证（≥5 个场景）
5. 开放问题
6. 收尾说明
7. 版本状态更新
8. Commit 信息
9. 是否继续下一个任务

---

## 第十二章 新增数据库表汇总

| 任务 | 新增表 | 字段数 |
|------|------|------|
| v0.43.3 | `api_key` | 11 个字段 |
| v0.43.1 / v0.43.2 / v0.43.4 | — | 无 |

**v0.43 合计新增：1 张表（api_key）**

---

## 第十三章 开始前必须先输出

Claude Code 在开始 v0.43.1 编码前，必须先输出：

1. **当前代码现状理解**：确认 `parsers/__init__.py` 现有路由表内容；确认 `asset_chunk` 表字段；确认 `ingestion-worker/Dockerfile` 现有 apt 安装内容
2. **v0.43.1 实施计划**：T-43-01-A 到 T-43-01-E 的执行顺序和预期改动
3. **v0.43.1 预计修改文件清单**：具体文件路径

**在这三项输出之前，不得开始写代码。**

---

## 第十四章 完成定义（DoD）

- [ ] v0.43.1 ~ v0.43.5 全部 Planned → Completed
- [ ] `.docx` 上传可正确解析，asset_chunk 有数据
- [ ] 图片上传依赖缺失时 job.status = "failed"，有明确 error_message
- [ ] 外部 Agent 可通过 API Key 调用 `/v1/agent/search` 和 `/v1/agent/ask`
- [ ] 知识图谱页面 `/projects/{id}/graph` 可访问，图谱正确渲染
- [ ] `pytest` 全量通过
- [ ] `npm run build` 无编译错误
- [ ] VERSION = 0.43.5，CHANGELOG 完整，验收报告已输出

---

## 第十五章 完成状态追踪

| 任务版本号 | 任务名称 | 状态 | 实际完成日期 |
|----------|--------|------|------------|
| v0.43.1 | Word 解析器修复 | Planned | — |
| v0.43.2 | OCR/ASR 静默失败修复 | Planned | — |
| v0.43.3 | Agent 输出接口标准化 | Planned | — |
| v0.43.4 | 知识图谱 API + 可视化 | Planned | — |
| v0.43.5 | 全量回归验收 | Planned | — |

---

## 第十六章 风险识别

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|---------|
| react-flow 与现有 React 19 版本兼容性 | 中 | 中 | T-43-04-C 开始前先安装并确认 `npm run build` 通过，有问题立即停止报告 |
| architecture_node 递归查询性能（深层架构） | 低 | 中 | 限制最大递归深度为 6 层；超出则截断并在 node_path 末位标注 "..." |
| API Key SHA-256 哈希碰撞 | 极低 | 高 | 业界接受的安全做法，无需额外缓解 |

---

## 第十七章 变更记录

| 日期 | 变更内容 | 责任人 |
|------|---------|------|
| 2026-03-24 | V1.0 初稿 | 产品 Owner |
| 2026-03-24 | V2.0 按产品北极星砍掉跑偏功能，聚焦核心链路 | 产品 Owner |
| 2026-03-24 | V3.0 按 §2.5 补全字段级定义、API 表格、业务规则、原子拆解、章节 6–17 | 产品 Owner |

---

*文档状态：已完成，Claude Code 可按章节 13 要求开始执行。*
