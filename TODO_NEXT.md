# TODO_NEXT

## 上次停在
- 版本：v0.52.11 | 分支：main | 最后完成：v0.52 版本封板（tag v0.52.11 + push origin）
- Phase 8 审计：健康度 A（16 发现，13 已修复，3 延后 v0.53）
- v0.52 全部完成 ✅，已 push 到 origin/main

## 下一步

### 无规划版本
- 目前无 v0.53 开发计划文件（`docs/dev-plans/dev-plan-v0.53.md` 不存在）
- 等待产品负责人创建 v0.53 开发计划后继续

### v0.53 候选任务（Phase 8 审计延后项）
- I-001：租户搜索结果 UI 限额指示（前端 quota 展示）
- I-002：Pipeline 编辑器 UI（stage 拖拽排序页面）
- I-003：Ontology 图谱可视化 UI 页面

### 可选技术改进
- 将 `get_redis_client()` 替换现有 `redis.from_url()` 调用点（统一 Sentinel 支持）
- 在更多高危路由（doc rollback, architecture rollback）添加确认码
- 前端 Review Kanban "分配审批人" 交互
- GitHub Dependabot 警告处理（2 high, 6 moderate）

## 注意事项
- migrations 待执行：y4z5a6b7c8d9 + z5a6b7c8d9e0
- v0.52 约束已解除（封板完成）
- v0.53 可引入新 migration / 新模型（如需要）
