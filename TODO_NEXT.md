# TODO_NEXT

## 上次停在
- 版本：v0.48.1 | 分支：test-v-0-48-a | 最后完成：v0.48.1 网页正文提取模块
- v0.45 全部完成 ✅
- v0.46 全部完成 ✅
- v0.47 全部完成 ✅
- v0.48.1 完成 ✅

## 下一步

### v0.48.2 — URL import 升级（使用正文提取替代原始 HTML）
- 修改 `asset_service.py` 的 `import_url()` 方法
- 调用 `readability.py` 的 `extract_article()` 提取正文
- 原始 HTML 仍存 MinIO，AssetChunk 使用提取后正文
- 元数据存入 Asset.tags

## 注意事项
- weasyprint 需要系统级依赖（Cairo/Pango），Docker 部署时需确认
- migration s8g9h0i1j2k3 待执行：`ALTER TABLE knowledge_doc ADD COLUMN update_type varchar(20)`
- migration t9h0i1j2k3l4 待执行：`CREATE TABLE pipeline_stage_log`
- KnowledgeDoc.status 合法值：draft / pending / approved / rejected / archived
- Job 表名为 `job`（不是 pipeline_job），模型在 packages/shared-models/shared_models/job.py
- Asset 解析状态字段名为 `parse_status`（不是 processing_status）
- trafilatura 2.0.0 已安装到 .venv，需加入部署依赖
