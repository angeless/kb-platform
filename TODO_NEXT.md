# TODO_NEXT

## 上次停在
- 版本：v0.48.2 | 分支：test-v-0-48-a | 最后完成：v0.48.2 URL import 升级
- v0.45-v0.47 全部完成 ✅
- v0.48.1 完成 ✅（readability 模块）
- v0.48.2 完成 ✅（URL import 集成）

## 下一步

### v0.48.3 — 视频解析器（FFmpeg 音频提取 + 字幕检测）
- 新增 `video_parser.py` in `services/ingestion-worker/worker/parsers/`
- FFmpeg 提取音轨 → ASR 转文字
- 检测内嵌字幕 → 独立 chunk
- 需要系统安装 FFmpeg

## 注意事项
- weasyprint 需要系统级依赖（Cairo/Pango），Docker 部署时需确认
- migration s8g9h0i1j2k3 待执行
- migration t9h0i1j2k3l4 待执行
- KnowledgeDoc.status 合法值：draft / pending / approved / rejected / archived
- Job 表名为 `job`，模型在 packages/shared-models/shared_models/job.py
- Asset 解析状态字段名为 `parse_status`（不是 processing_status）
- trafilatura 2.0.0 + lxml_html_clean 已安装到 .venv
- URL import 的 parse_status 现在设为 "completed"（已在 import 时完成文本提取）
