# 实施计划 v0.48.3 — 视频解析器（FFmpeg 音频提取 + 字幕检测）

**任务版本号**: v0.48.3
**基线**: v0.48.2
**分支**: test-v-0-48-a

---

## 1. 目标

新增视频解析器模块，使用 FFmpeg 提取音轨交给 ASR、检测内嵌字幕、提取视频元数据。

## 2. 变更文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `services/ingestion-worker/worker/parsers/video_parser.py` | 新增 | 视频解析器 |
| `services/ingestion-worker/worker/parsers/__init__.py` | 修改 | 注册 video_parser |
| `services/ingestion-worker/requirements.in` | 修改 | 新增 ffmpeg-python |
| `services/ingestion-worker/tests/test_video_parser.py` | 新增 | 单元测试 |

## 3. 设计

### 接口
```python
def parse(content: bytes, filename: str) -> list[dict]:
    # 1. 写入临时文件
    # 2. ffmpeg.probe() 提取元数据
    # 3. 提取音轨 → 临时 WAV → asr_parser.parse()
    # 4. 检测字幕流 → 提取字幕文本
    # 5. 清理临时文件
    # 返回 chunk 列表
```

### 业务规则
- FFmpeg 不在 PATH → 友好 RuntimeError（不 crash）
- 无音轨视频 → 返回空 chunks，不报错
- 有字幕流 → 提取为独立 chunk，tags 标记 source: subtitle
- 元数据（时长/分辨率）记录在第一个 chunk 的 tags 中

## 4. 验收标准

- [ ] AC-1: MP4 视频 → 提取音频并通过 ASR 转文字 chunks
- [ ] AC-2: 含字幕视频 → 字幕独立 chunk（tags.source=subtitle）
- [ ] AC-3: 无字幕视频 → 仅音频转文字，不报错
- [ ] AC-4: 元数据记录在 tags
- [ ] AC-5: 临时文件解析后清理
- [ ] AC-6: 无 FFmpeg → 友好错误信息
