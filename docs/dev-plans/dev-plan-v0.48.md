# KB Platform v0.48 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v048
**版本**: V2.0（规范重写版）
**日期**: 2026-03-31
**基线**: v0.47 完成后
**依据**: PRD §7.2（多模态解析）+ WISHLIST W-07
**作者**: Claude Code（自动生成）

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.47 完成后的代码增量增强。禁止重构无关模块。

### 1.2 继承已有能力

- **Ingestion Worker**（`services/ingestion-worker/`）— text/pdf/ocr/asr 4 种解析器
- **Asset 模型**（`packages/shared-models/shared_models/asset.py`）— Asset + AssetChunk + 多模态标记
- **MinIO 存储**（`services/api/app/utils/storage.py`）— 文件上传/下载
- **URL import**（`services/api/app/services/asset_service.py`）— import_url 保存原始 HTML
- **SSRF 防护**（`url_fetcher.py` + `url_validator.py`）— DNS rebinding 防御
- **Pipeline 配置化**（v0.46.1-4）— stage enable/disable + params

### 1.3 最小改动原则

每个任务只改必须改的文件。

### 1.4 任务领取规则

每次只能领取一个任务。完成后汇报，确认再领下一个。

---

## 第二章 当前阶段事实

### 2.1 版本主题

**v0.48：多模态解析增强 — 视频解析 + 网页正文提取 + 文件安全扫描**

> 将平台输入能力从"文本/PDF/图片/音频"扩展到"视频+网页"，补齐 PRD §7.2 最后两个多模态缺口。同时集成文件安全扫描。

---

## 第三章 本轮目标与边界

### 3.1 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.48.1 | 网页正文提取 — Readability 算法集成 | P0 | 待开发 | PRD §7.2 |
| v0.48.2 | URL import 升级 — 使用正文提取替代原始 HTML | P1 | 待开发 | PRD §7.2 |
| v0.48.3 | 视频解析器 — FFmpeg 音频提取 + 字幕检测 | P0 | 待开发 | PRD §7.2 |
| v0.48.4 | 视频帧提取 — 关键帧截取 + OCR | P1 | 待开发 | PRD §7.2 |
| v0.48.5 | 文件恶意扫描集成（ClamAV） | P1 | 待开发 | W-07 |
| v0.48.6 | 前端上传页 — 视频预览 + 解析进度 | P2 | 待开发 | UX |

### 3.2 北极星三问校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ |
|-----|----------------|-------------|-------------|
| v0.48.1 | ✅ 输入端（网页→结构文本） | - | - |
| v0.48.2 | ✅ 输入端（提升 URL 导入质量） | - | - |
| v0.48.3 | ✅ 输入端（视频→文本） | - | - |
| v0.48.4 | ✅ 输入端（视频→图文） | - | - |
| v0.48.5 | - | - | ✅ 安全必要 |
| v0.48.6 | - | ✅ 输入接口体验 | - |

### 3.3 明确不做

- 实时视频流处理 — 仅支持文件上传
- YouTube/Bilibili 在线视频下载 — 版权风险
- 浏览器渲染型抓取（Playwright/Puppeteer）— 过重，仅 Readability 静态解析

---

## 第四章 执行顺序

```
网页链：v0.48.1 → v0.48.2
视频链：v0.48.3 → v0.48.4 → v0.48.6
安全：v0.48.5（独立，可并行）
```

建议：`v0.48.1 → v0.48.2 → v0.48.3 → v0.48.5 → v0.48.4 → v0.48.6`

---

## 第五章 各任务详细定义

---

### v0.48.1: 网页正文提取 — Readability 算法集成

**任务版本号：** v0.48.1
**优先级：** P0
**前置依赖：** 无

---

#### 背景与目标

**现状：** URL import 保存原始 HTML，包含导航栏、广告等噪音。

**目标（Goal）：** 新增 Readability 工具模块，使用 `trafilatura` 从 HTML 中提取正文、标题、作者、发布日期，去除噪音。

---

#### 后端变更

**新增文件：**
- `services/api/app/utils/readability.py` — 正文提取模块：
  ```
  def extract_article(html: str, url: str) -> dict:
      # 返回 {"title": str, "body": str, "author": str|None, "date": str|None}
  ```

**修改文件：**
- `requirements.in`（或对应 service 的依赖文件）— 新增 `trafilatura` 依赖

**业务规则：**
① 接收 HTML 字符串和原始 URL
② 调用 `trafilatura.extract()` 提取正文
③ 使用 `trafilatura.metadata` 提取标题、作者、日期
④ 去除导航、侧栏、广告、脚本标签
⑤ 提取失败时返回 `{"title": "", "body": html_stripped, "author": None, "date": None}`（降级为简单 HTML 去标签）
⑥ 正文返回纯文本（非 HTML）

---

#### 验收标准

- [ ] 传入新闻网页 HTML → 提取纯正文（无导航/广告/脚本）
- [ ] 提取结果包含 title / body / author / date 四个字段
- [ ] 传入空 HTML → 返回空 body，不报错
- [ ] 传入非 HTML 文本 → 原样返回 body
- [ ] trafilatura 提取失败 → 降级为简单 HTML 去标签

---

#### 工作范围

**包含：** readability.py 模块 + trafilatura 依赖（~40 行）
**不包含：** URL import 流程集成（v0.48.2）；浏览器渲染（Playwright）

---

#### 预估工作量

- Phase 1 读现有 URL import 流程 + trafilatura 文档：1 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| trafilatura 对中文网页效果差 | 中 | 中 | 备选 `newspaper3k`，需对比测试 |
| 依赖安装增加镜像大小 | 低 | 低 | trafilatura ~2MB，可接受 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/services/asset_service.py` 中 import_url 完整逻辑
> 2. 确认 trafilatura 安装和基本 API
> 3. 确认依赖文件路径（requirements.in / pyproject.toml）

---

### v0.48.2: URL import 升级 — 使用正文提取替代原始 HTML

**任务版本号：** v0.48.2
**优先级：** P1
**前置依赖：** v0.48.1（readability 模块可用）

---

#### 背景与目标

**目标（Goal）：** 修改 URL import 流程，使用 v0.48.1 的 readability 模块提取正文，AssetChunk 使用提取后的正文而非原始 HTML。原始 HTML 仍存 MinIO 保留溯源。

---

#### 后端变更

**修改文件：**
- `services/api/app/services/asset_service.py` — `import_url` 方法：
  - 获取 HTML 后调用 `extract_article(html, url)`
  - 原始 HTML 仍上传到 MinIO（保留溯源）
  - AssetChunk.content_text 使用提取后的正文
  - Asset.tags 中记录 `extracted_title`、`extracted_author`、`extracted_date`

**业务规则：**
① 下载 URL 内容（沿用现有 url_fetcher，含 SSRF 防护）
② 调用 `extract_article(html, url)` 提取正文
③ 原始 HTML 上传到 MinIO（文件名不变）
④ 创建 AssetChunk 时，`content_text` = 提取后的正文
⑤ 提取的元数据（title/author/date）存入 Asset.tags JSONB
⑥ 提取失败时降级为原始 HTML 去标签（与 v0.48.1 降级逻辑一致）

---

#### 验收标准

- [ ] 导入新闻 URL → AssetChunk.content_text 为纯正文（非 HTML）
- [ ] MinIO 中保存了原始 HTML（可下载验证）
- [ ] Asset.tags 包含 extracted_title / extracted_author / extracted_date
- [ ] 导入不可解析的 URL → 降级为去标签文本，不报错
- [ ] SSRF 防护不受影响（依然拦截内网 IP）

---

#### 工作范围

**包含：** asset_service.py import_url 修改（~15 行）
**不包含：** 批量 URL 导入；已有 URL 资产的正文重提取

---

#### 预估工作量

- Phase 1 读 import_url 完整流程：0.5 小时
- Phase 2 执行：1 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 提取后正文过短导致知识质量下降 | 低 | 中 | 降级机制保底 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `asset_service.py` 中 import_url 完整代码
> 2. 确认 AssetChunk 创建位置和 tags 使用方式

---

### v0.48.3: 视频解析器 — FFmpeg 音频提取 + 字幕检测

**任务版本号：** v0.48.3
**优先级：** P0
**前置依赖：** 无（但需系统安装 FFmpeg）

---

#### 背景与目标

**现状：** 视频上传仅通过 ASR 提取音频转文字，无字幕检测、无元数据。

**目标（Goal）：** 新增视频解析器模块，使用 FFmpeg 提取音轨交给 ASR、检测内嵌字幕、提取视频元数据。

---

#### 后端变更

**新增文件：**
- `services/ingestion-worker/worker/parsers/video_parser.py` — 视频解析器：
  ```
  def parse_video(file_path: str, asset_id: str, db: Session) -> list[AssetChunk]:
      # 1. 提取元数据（时长、分辨率、帧率）
      # 2. 提取音轨 → 传递给 asr_parser
      # 3. 检测内嵌字幕（SRT/ASS/VTT）→ 独立 chunk
      # 返回 chunk 列表
  ```

**修改文件：**
- `services/ingestion-worker/worker/parsers/__init__.py` — 注册 video_parser，MIME 类型映射 `video/*`
- 依赖文件 — 新增 `ffmpeg-python`

**业务规则：**
① 接收视频文件路径和 asset_id
② 使用 `ffmpeg.probe()` 提取元数据（duration / width / height / fps）
③ 使用 `ffmpeg.input().output()` 提取音轨为临时 WAV 文件
④ 将 WAV 传递给已有 `asr_parser` 获取文字 chunks
⑤ 检查视频流中是否有字幕流（`codec_type == 'subtitle'`）
⑥ 有字幕流时：使用 FFmpeg 提取字幕文本，创建独立 AssetChunk（tags 标记 `source: subtitle`）
⑦ 元数据存入 Asset.tags（`duration_s`, `resolution`, `fps`）
⑧ 清理临时文件

---

#### 验收标准

- [ ] 上传 MP4 视频 → 自动提取音频并通过 ASR 转为文字 chunks
- [ ] 含内嵌字幕的视频 → 字幕文本被独立提取为 chunk（tags 标记 source: subtitle）
- [ ] 无字幕的视频 → 仅音频转文字，不报错
- [ ] 视频元数据（时长/分辨率）记录在 Asset.tags
- [ ] 临时文件在解析完成后被清理
- [ ] 无 FFmpeg 时 → 友好错误信息（而非 crash）

---

#### 工作范围

**包含：** video_parser.py + 解析器注册 + ffmpeg-python 依赖（~80 行）
**不包含：** 帧提取/OCR（v0.48.4）；前端视频预览（v0.48.6）

---

#### 预估工作量

- Phase 1 读 ingestion-worker 解析器架构 + asr_parser 接口：1 小时
- Phase 2 执行：4 小时
- Phase 3 测试：2 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| FFmpeg Docker 镜像体积增大 ~200MB | 确定 | 低 | 使用 ffmpeg-slim 或多阶段构建 |
| 大视频文件 ASR 超时 | 中 | 中 | 设置 ASR 超时 + 分段处理 |
| FFmpeg 不在 PATH | 中 | 高 | Phase 1 确认 Docker 镜像是否包含 FFmpeg |

**外部依赖：** FFmpeg 系统级安装（Docker 镜像需包含 `apt-get install ffmpeg`）

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/ingestion-worker/worker/parsers/` 目录，确认解析器注册机制
> 2. 读 `asr_parser` 接口，确认音频输入格式要求
> 3. 确认 Docker 镜像是否已包含 FFmpeg

---

### v0.48.4: 视频帧提取 — 关键帧截取 + OCR

**任务版本号：** v0.48.4
**优先级：** P1
**前置依赖：** v0.48.3（video_parser 模块存在）

---

#### 背景与目标

**目标（Goal）：** 扩展视频解析器，支持定时截取关键帧，对帧图片执行 OCR 提取文字（适用于 PPT 录屏、白板等场景）。

---

#### 后端变更

**修改文件：**
- `services/ingestion-worker/worker/parsers/video_parser.py` — 新增帧提取逻辑：
  ```
  def _extract_keyframes(file_path: str, interval_s: int = 30) -> list[tuple[str, float]]:
      # 每 interval_s 秒提取一帧
      # 使用 ffmpeg scene filter 去重
      # 返回 [(frame_path, timestamp_s), ...]
  ```

**业务规则：**
① 视频解析时，每 N 秒提取一帧（N 从 pipeline config 读取，默认 30s）
② 使用 FFmpeg `select='gt(scene,0.4)'` 场景检测去除相似帧
③ 提取的帧图片传递给已有 `ocr_parser` 做文字识别
④ OCR 有文字的帧 → 创建 AssetChunk（tags: `source: video_frame`, `timestamp_s: N`）
⑤ 帧截图上传到 MinIO（路径: `{asset_id}/frames/frame_{timestamp}.jpg`）
⑥ 10 分钟视频预期提取 ~20 帧（去重后）
⑦ 清理本地临时帧文件

---

#### 验收标准

- [ ] 10 分钟视频 → 提取 ~20 帧（去重后）
- [ ] 含文字的帧（PPT 录屏）→ OCR 提取文字创建 chunk
- [ ] 帧截图存入 MinIO，路径正确
- [ ] AssetChunk.tags 包含 timestamp_s 时间戳
- [ ] 无文字帧 → 不创建 chunk（避免噪音）
- [ ] 帧提取间隔可通过 pipeline config 配置

---

#### 工作范围

**包含：** video_parser.py 帧提取扩展 + OCR 集成（~60 行）
**不包含：** 帧内容的语义分析；视频摘要生成

---

#### 预估工作量

- Phase 1 读 ocr_parser 接口 + MinIO 上传方式：0.5 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 场景检测阈值不适合所有视频 | 中 | 低 | 阈值可配置，默认 0.4 |
| 大量帧 OCR 耗时 | 中 | 中 | 限制最大帧数（默认 50） |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `ocr_parser` 接口确认图片输入格式
> 2. 确认 MinIO 上传 API

---

### v0.48.5: 文件恶意扫描集成（ClamAV）

**任务版本号：** v0.48.5
**优先级：** P1
**前置依赖：** 无

---

#### 背景与目标

**现状：** 文件上传无恶意扫描，存在安全风险。

**目标（Goal）：** 集成 ClamAV 守护进程，文件上传前扫描，恶意文件拒绝上传。

---

#### 后端变更

**新增文件：**
- `services/api/app/utils/malware_scanner.py` — ClamAV 扫描封装：
  ```
  def scan_file(file_path: str) -> tuple[bool, str | None]:
      # 通过 clamd socket 扫描文件
      # 返回 (is_clean, threat_name)
  ```

**修改文件：**
- `services/api/app/services/asset_service.py` — upload 前调用扫描
- `packages/shared-config/shared_config/settings.py` — 新增：
  - `clamav_socket: str = "/var/run/clamav/clamd.ctl"` — ClamAV socket 路径
  - `clamav_enabled: bool = False` — 是否启用扫描（默认关闭，需安装 ClamAV 后开启）

**业务规则：**
① 文件上传时，若 `clamav_enabled=True`，调用 `scan_file()` 扫描
② 连接 ClamAV 守护进程 socket
③ 发送 `INSTREAM` 命令 + 文件数据
④ 检测到恶意文件 → 返回 400 `{"error": "malware_detected", "detail": "File rejected: {threat_name}"}`
⑤ ClamAV 不可用（socket 连接失败）→ 记录 WARNING 日志，允许上传（降级策略）
⑥ `clamav_enabled=False` 时完全跳过扫描

---

#### 验收标准

- [ ] `clamav_enabled=True` + ClamAV 运行 → 正常文件上传成功
- [ ] `clamav_enabled=True` + 恶意文件（EICAR test file）→ 400 拒绝上传
- [ ] `clamav_enabled=True` + ClamAV 不可用 → WARNING 日志 + 允许上传
- [ ] `clamav_enabled=False` → 完全跳过扫描，行为不变
- [ ] 扫描操作不显著增加上传延迟（< 1s for files < 10MB）

---

#### 工作范围

**包含：** malware_scanner.py + asset_service.py 集成 + 配置项（~40 行）
**不包含：** ClamAV 部署（运维任务）；扫描结果日志持久化

**外部依赖：** ClamAV daemon（Docker sidecar 或共享 socket）

---

#### 预估工作量

- Phase 1 读 asset_service upload 流程 + clamd 协议：1 小时
- Phase 2 执行：2 小时
- Phase 3 测试：1.5 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| ClamAV 数据库更新需要网络 | 中 | 低 | freshclam cron + 离线数据库备选 |
| ClamAV 不可用时的降级策略 | 低 | 中 | 默认 clamav_enabled=False，需主动开启 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 `services/api/app/services/asset_service.py` upload 方法完整逻辑
> 2. 确认 clamd Python 客户端库（pyclamd 或直接 socket）

---

### v0.48.6: 前端上传页 — 视频预览 + 解析进度

**任务版本号：** v0.48.6
**优先级：** P2
**前置依赖：** v0.48.3（视频解析器可用）

---

#### 背景与目标

**目标（Goal）：** 在资产管理页面为视频文件显示缩略图和时长，上传时展示解析进度状态。

---

#### 前端变更

**修改文件：**
- `apps/web/src/app/(dashboard)/projects/[id]/assets/page.tsx` — 修改：
  - 视频文件列表项显示缩略图 + 时长（从 Asset.tags 中读取 `duration_s`）
  - 上传进度条组件（已有上传进度 → 扩展为多阶段：上传中 / ASR 中 / 帧提取中 / 完成）
  - 解析状态标签（基于 Asset 的 processing_status 字段）

**业务规则：**
① 视频类型文件在列表中显示视频图标 + 时长标签（格式 `MM:SS`）
② 上传期间展示进度条
③ 上传完成后展示解析状态：ASR 进行中 / 帧提取中 / 完成
④ 解析状态通过轮询 Asset 详情获取（GET asset → 检查 processing_status）

---

#### 验收标准

- [ ] 视频类型文件显示视频图标（区别于文档/图片）
- [ ] 视频文件显示时长标签（如 "3:45"）
- [ ] 上传过程中显示进度条
- [ ] 解析完成后状态标签更新为"完成"
- [ ] 非视频文件不受影响

---

#### 工作范围

**包含：** assets/page.tsx 视频相关 UI 改动（~40 行前端）
**不包含：** 视频在线播放器；视频帧浏览功能

---

#### 预估工作量

- Phase 1 读 assets/page.tsx 结构：0.5 小时
- Phase 2 执行：3 小时
- Phase 3 测试：1 小时

---

#### 风险预判

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 轮询解析状态增加 API 负载 | 低 | 低 | 轮询间隔 5s，解析完成后停止 |

> ⚠️ **Phase 1 前置确认：**
> 1. 读 assets/page.tsx 当前列表渲染逻辑
> 2. 确认 Asset 上是否有 processing_status 字段（可能在 tags 中）

---

## 第六章 实现约束

- 新增解析器遵循 `services/ingestion-worker/worker/parsers/` 目录结构
- FFmpeg 依赖需在 Docker 镜像中安装
- ClamAV 为可选依赖，默认关闭
- Migration 路径：`infra/sql/alembic/versions/`

---

## 第七章 任务领取规则

每次只能领取一个任务。完成后汇报，确认后再领。

---

## 第八章 测试要求

> 引用 `docs/tech-specs/testing-strategy.md`

| 层次 | 覆盖重点 |
|------|---------|
| 后端单元测试 | readability 提取、video_parser 各子功能、malware_scanner |
| 后端集成测试 | URL import 端到端（mock HTTP）、文件上传 + 扫描 |
| 前端组件测试 | 视频文件列表渲染、进度状态展示 |

---

## 第九章 任务汇报格式

同 v0.47 第九章（9 项结构报告）。

---

## 第十章 版本号管理

版本号格式：`v0.48.{Z}`。每完成一个任务更新 VERSION / CHANGELOG / TODO_NEXT.md。

---

## 第十一章 文档产出要求

同 v0.47 第十一章。版本完成后产出 phase-report-v0.48.md + seal-audit-v0.48.md。

---

## 第十二章 新增数据库表汇总

v0.48 **不新增数据库表**。变更仅限代码层。

---

## 第十三章 开始前必须先输出

1. 当前 ingestion-worker 解析器架构理解
2. 第一个任务的实施计划
3. 预计修改文件清单

---

## 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|----------|--------|------|
| v0.48.1 | 网页正文提取 | — | 0 | Planned |
| v0.48.2 | URL import 升级 | — | 0 | Planned |
| v0.48.3 | 视频解析器 | — | 0 | Planned |
| v0.48.4 | 视频帧提取 | — | 0 | Planned |
| v0.48.5 | 文件恶意扫描 | — | 0 | Planned |
| v0.48.6 | 前端视频预览 | — | 0 | Planned |

---

## 第十五章 变更记录

| 日期 | 变更内容 | 责任人 |
|-----|--------|------|
| 2026-03-31 | V1.0 初始版本 | Claude Code |
| 2026-03-31 | V2.0 按规范重写，补齐必填字段 | Claude Code |

---

## 第十六章 决策与假设

**关键决策：**
- 使用 trafilatura 而非 newspaper3k — 原因：活跃维护、多语言支持更好
- ClamAV 默认关闭 — 原因：需额外部署，不强制依赖
- 视频帧提取独立任务（v0.48.4）而非合并到 v0.48.3 — 原因：帧提取依赖 OCR 集成，复杂度独立

**重要假设：**
- FFmpeg 可在 Docker 镜像中安装
- ClamAV daemon 可作为 sidecar 部署
- trafilatura 对主流中英文网站效果可接受

---

## 第十七章 版本级风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| FFmpeg Docker 镜像体积增大 ~200MB | 确定 | 低 | ffmpeg-slim 或多阶段构建 |
| ClamAV 数据库更新需要网络 | 中 | 低 | freshclam cron + 离线备选 |
| trafilatura 中文效果未验证 | 中 | 中 | 备选 newspaper3k，Phase 1 对比测试 |
