# KB Platform v0.48 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v048
**版本**: V1.0（初始版）
**日期**: 2026-03-31
**基线**: v0.47 完成后
**依据**: PRD §7.2（多模态解析）+ WISHLIST W-07
**作者**: Claude Code（自动生成）

---

## 第一章 版本主题

**v0.48：多模态解析增强 — 视频解析 + 网页正文提取 + 文件安全扫描**

> 将平台的输入能力从"文本/PDF/图片/音频"扩展到"视频 + 网页"，补齐 PRD §7.2 最后两个多模态缺口。同时集成文件安全扫描，消除上传渠道风险。

---

## 第二章 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.48.1 | 视频解析器 — FFmpeg 音频提取 + 字幕检测 | P0 | 待开发 | PRD §7.2 |
| v0.48.2 | 视频帧提取 — 关键帧截取 + OCR | P1 | 待开发 | PRD §7.2 |
| v0.48.3 | 网页正文提取 — Readability 算法集成 | P0 | 待开发 | PRD §7.2 |
| v0.48.4 | URL import 升级 — 使用正文提取替代原始 HTML | P1 | 待开发 | PRD §7.2 |
| v0.48.5 | 文件恶意扫描集成（ClamAV） | P1 | 待开发 | W-07 |
| v0.48.6 | 前端上传页 — 视频预览 + 解析进度 | P2 | 待开发 | UX |

---

## 第三章 目标与边界

### 3.1 北极星校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ | 结论 |
|-----|----------------|-------------|-------------|------|
| v0.48.1 | ✅ 输入端（视频→文本） | - | - | ✅ |
| v0.48.2 | ✅ 输入端（视频→图文） | - | - | ✅ |
| v0.48.3 | ✅ 输入端（网页→结构文本） | - | - | ✅ |
| v0.48.4 | ✅ 输入端（提升 URL 导入质量） | - | - | ✅ |
| v0.48.5 | - | - | ✅ 安全必要 | ✅ |
| v0.48.6 | - | ✅ 输入接口体验 | - | ✅ |

### 3.2 明确不做

- 实时视频流处理 — 仅支持文件上传
- YouTube/Bilibili 在线视频下载 — 版权风险，仅支持用户自有视频文件
- 浏览器渲染型抓取（Playwright/Puppeteer）— 过重，仅 Readability 静态解析

---

## 第四章 执行顺序

```
视频链：v0.48.1 → v0.48.2 → v0.48.6
网页链：v0.48.3 → v0.48.4
安全：v0.48.5（独立，可并行）
```

建议：`v0.48.3 → v0.48.4 → v0.48.1 → v0.48.5 → v0.48.2 → v0.48.6`

---

## 第五章 各任务详细定义

---

### v0.48.1: 视频解析器 — FFmpeg 音频提取 + 字幕检测

**前置依赖：** 无（但需系统安装 FFmpeg）

**背景：** 当前视频上传仅通过 ASR 提取音频转文字。PRD 要求完整的视频解析：音频、字幕、关键帧。

**变更：**
- `services/ingestion-worker/worker/parsers/video_parser.py` — 新增：
  - FFmpeg 调用提取音轨 → 传递给 asr_parser
  - 字幕流检测（SRT/ASS/VTT 内嵌字幕提取）
  - 元数据提取（时长、分辨率、帧率）
- `services/ingestion-worker/worker/parsers/__init__.py` — 注册 video_parser
- `requirements.in` — 新增 `ffmpeg-python` 依赖
- 约 80 行

**验收标准：**
- 上传 MP4 视频，自动提取音频并转为文字
- 含内嵌字幕的视频，字幕文本被独立提取
- 视频元数据记录在 Asset 或 AssetChunk tags 中

**外部依赖：**
- FFmpeg 系统级安装（Docker 镜像需包含 `apt-get install ffmpeg`）

---

### v0.48.2: 视频帧提取 — 关键帧截取 + OCR

**前置依赖：** v0.48.1

**变更：**
- `services/ingestion-worker/worker/parsers/video_parser.py` — 扩展：
  - 每 N 秒提取一帧（N 可配置，默认 30s）
  - 关键帧通过场景检测（ffmpeg scene filter）去重
  - 提取的帧图片传递给 ocr_parser 做文字识别
- 约 60 行

**验收标准：**
- 10 分钟视频提取 ~20 帧
- 含文字的帧（PPT 录屏、白板）OCR 提取文字
- 帧截图存入 MinIO，AssetChunk.tags 记录时间戳

---

### v0.48.3: 网页正文提取 — Readability 算法集成

**前置依赖：** 无

**背景：** 当前 URL import 保存原始 HTML，包含导航栏、广告等噪音。

**变更：**
- `services/api/app/utils/readability.py` — 新增：
  - 基于 `readability-lxml` 或 `trafilatura` 提取正文
  - 提取：标题、正文、发布日期、作者
  - 去除导航、侧栏、广告、脚本
- `requirements.in` — 新增 `trafilatura` 依赖
- 约 40 行

**验收标准：**
- 给定新闻 URL，提取纯正文（无导航/广告）
- 提取准确率 > 90%（主流新闻/博客站点）

---

### v0.48.4: URL import 升级

**前置依赖：** v0.48.3

**变更：**
- `services/api/app/services/asset_service.py` — import_url 调用 readability 提取正文
- 原始 HTML 仍存 MinIO（保留溯源），AssetChunk 使用提取后的正文
- 约 15 行改动

---

### v0.48.5: 文件恶意扫描集成

**前置依赖：** 无

**变更：**
- `services/api/app/utils/malware_scanner.py` — ClamAV 扫描封装（clamd socket）
- `services/api/app/services/asset_service.py` — upload 前扫描，恶意文件拒绝上传
- `packages/shared-config/shared_config/settings.py` — 新增 clamav_socket 配置
- 约 40 行

**外部依赖：**
- ClamAV daemon（Docker sidecar 或共享 socket）

---

### v0.48.6: 前端上传页 — 视频预览 + 解析进度

**前置依赖：** v0.48.1

**变更：**
- `apps/web/src/app/(dashboard)/projects/[id]/assets/page.tsx` — 视频文件显示缩略图 + 时长
- 上传进度条 + 解析状态显示（ASR 进行中 / 帧提取中 / 完成）
- 约 40 行前端改动

---

## 第六章 风险

| 风险 | 缓解 |
|------|------|
| FFmpeg Docker 镜像体积增大 ~200MB | 使用 ffmpeg-slim 或多阶段构建 |
| ClamAV 数据库更新需要网络 | 使用 freshclam cron + 离线数据库备选 |
| trafilatura 对中文网页效果未验证 | 备选 newspaper3k，需对比测试 |
