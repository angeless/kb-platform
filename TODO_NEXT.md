# TODO_NEXT

## 上次停在
- 版本：v0.48.6 | 分支：test-v-0-48-a | 最后完成：v0.48.6 前端视频预览
- v0.45-v0.47 全部完成 ✅
- v0.48 全部完成 ✅（v0.48.1-6 共 6 个任务）

## 下一步

### 版本边界：v0.48 版本封板
- 执行 §0.11 无任务空闲循环（PRD Gap 扫描 + 全量测试）
- 执行 §1.10 封板检查清单
- 执行 Phase 8 版本交叉审计
- 版本收尾 → CI 闭环

### 进入 v0.49 开发
- 读取 `docs/dev-plans/dev-plan-v0.49.md`
- Pipeline 智能化 + IR

## 注意事项
- FFmpeg 需在 Docker 镜像中安装
- trafilatura 2.0.0 + lxml_html_clean + ffmpeg-python 需加入部署依赖
- ClamAV 默认关闭，需要 ClamAV daemon 才能启用
- URL import parse_status 现在设为 "completed"
- Asset 解析状态字段名为 `parse_status`
- Node.js 未安装在当前环境，前端代码未经 tsc 验证
