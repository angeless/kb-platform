# TODO_NEXT

## 上次停在
- 版本：v0.48.3 | 分支：test-v-0-48-a | 最后完成：v0.48.3 视频解析器
- v0.45-v0.47 全部完成 ✅
- v0.48.1 完成 ✅（readability 模块）
- v0.48.2 完成 ✅（URL import 集成）
- v0.48.3 完成 ✅（视频解析器）

## 下一步

### v0.48.5 — 文件恶意扫描集成（ClamAV）
- 按计划执行顺序：v0.48.3 → v0.48.5 → v0.48.4 → v0.48.6
- 新增 `malware_scanner.py`
- 集成到 asset upload 流程
- ClamAV 默认关闭

## 注意事项
- FFmpeg 需在 Docker 镜像中安装（本地未安装，测试通过 mock）
- trafilatura 2.0.0 + lxml_html_clean + ffmpeg-python 已安装到 .venv
- URL import 的 parse_status 设为 "completed"
- Asset 解析状态字段名为 `parse_status`
