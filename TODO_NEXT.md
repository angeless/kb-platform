# TODO_NEXT

## 上次停在
- 版本：v0.47.8 | 分支：test-v-0-44-a | 最后完成：v0.47.8 集成测试补全
- v0.45 全部完成 ✅
- v0.46 全部完成 ✅（v0.46.1-7 共 7 个任务）
- v0.47 全部完成 ✅（v0.47.1-8 共 8 个任务，其中 v0.47.2 已由 v0.46.3 实现）

## 下一步

### 进入 v0.48 开发
- 读取 `docs/dev-plans/dev-plan-v0.48.md` 了解任务列表
- 按执行顺序逐一领取任务

## 注意事项
- weasyprint 需要系统级依赖（Cairo/Pango），Docker 部署时需确认
- migration s8g9h0i1j2k3 待执行：`ALTER TABLE knowledge_doc ADD COLUMN update_type varchar(20)`
- migration t9h0i1j2k3l4 待执行：`CREATE TABLE pipeline_stage_log`
- KnowledgeDoc.status 合法值：draft / pending / approved / rejected / archived
- Job 表名为 `job`（不是 pipeline_job），模型在 packages/shared-models/shared_models/job.py
- Asset 解析状态字段名为 `parse_status`（不是 processing_status）
