# TODO_NEXT

## 上次停在
- 版本：v0.47.0 | 分支：test-v-0-44-a | 最后完成：v0.47-v0.51 交叉审查v3 + 3个完整度 gap 补齐
- v0.45 全部完成 ✅
- v0.46 全部完成 ✅（v0.46.1-7 共 7 个任务）
- PRD Gap 修复 ✅
- v0.47-v0.51 开发计划 ✅（44 个原子任务，规范合规）
- 交叉审查 v1-v3 ✅（所有代码-计划不一致已清零）

## 下一步

### 进入开发（v0.47.1 开始）
1. v0.47.1 矛盾检测排除 draft 文档（P0，审计 C-3）
2. v0.47.2 suggest_tags entity_types 从 pipeline config 读取（P0，审计 H-1）
3. v0.47.3 Pipeline params JSON Schema 校验（P1，审计 H-4）
4. v0.47.4 数据库连接池显式配置（P1，W-02）
5. v0.47.5 审计日志保留策略 + 归档（P1，W-08）
6. v0.47.6 Pipeline per-stage 执行日志表（P1，W-12）
7. v0.47.7 模型 API Key 加密方案文档化 + 轮换 API（P2，W-09）
8. v0.47.8 集成测试补全（P2，W-16）

## 注意事项
- weasyprint 需要系统级依赖（Cairo/Pango），Docker 部署时需确认
- migration s8g9h0i1j2k3 待执行：`ALTER TABLE knowledge_doc ADD COLUMN update_type varchar(20)`
- KnowledgeDoc.status 合法值：draft / pending / approved / rejected / archived
- Job 表名为 `job`（不是 pipeline_job），模型在 packages/shared-models/shared_models/job.py
- Asset 解析状态字段名为 `parse_status`（不是 processing_status）
