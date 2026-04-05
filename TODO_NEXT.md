# TODO_NEXT

## 上次停在
- 版本：v0.52.11 | 分支：test-v-0-52-a | 最后完成：v0.52 集成缺口修复（11 个任务全部完成）
- v0.45-v0.51 全部完成 ✅（PR #7 已合并）
- v0.52 集成缺口修复全部完成 ✅（v0.52.1-11 共 11 个任务）

## 下一步

### 版本边界：v0.52 封板
- 需要交叉审计闭环 + PR 合并到 main

### 可选后续
- 将 `get_redis_client()` 替换现有 `redis.from_url()` 调用点（统一 Sentinel 支持）
- 在更多高危路由（doc rollback, architecture rollback）添加确认码
- 前端 Review Kanban "分配审批人" 交互（目前 pending 列无 assign 按钮，需选择 reviewer 的 UI）

## 注意事项
- migrations 待执行：y4z5a6b7c8d9 + z5a6b7c8d9e0
- v0.52 约束：无新 migration、无新模型、无新依赖 — 仅接线已有代码
