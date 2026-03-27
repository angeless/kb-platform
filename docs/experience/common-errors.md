# KB Platform 常见错误清单

> 本文件记录开发过程中发现的跨任务通用错误模式。
> 每个 vX.Y.Z 任务完成后，如果发现了具有复用价值的错误模式，应追加到本文件。
> Phase 2 ③ 门禁要求对照本文件逐条扫描当前变更。

## 错误模式列表

### CE-001: N+1 查询未被批量化
- **错误表现**: 在循环中逐个查询数据库（如 for result in results: db.get(Model, id)）
- **根因**: 习惯性逐条处理，未考虑批量加载
- **正确做法**: 收集所有 ID 后一次性 `select(...).where(Model.id.in_(ids))`，再在内存中映射
- **首次发现**: v0.43.5 - agent_search N+1 审计
- **适用范围**: 所有涉及循环 + 数据库查询的场景

### CE-002: 前后端 API 字段名不一致
- **错误表现**: 后端返回 `label` 但前端接口定义为 `node_name`，导致渲染 undefined
- **根因**: 前端接口定义时未对照后端 schema，凭记忆写字段名
- **正确做法**: 前端类型定义必须从后端 Pydantic schema 或 OpenAPI 文档导出，不手写
- **首次发现**: v0.43.4 - knowledge-graph 前后端字段不匹配
- **适用范围**: 所有新增 API 端点的前端消费方

### CE-003: 缺少租户隔离检查
- **错误表现**: 端点仅按 project_id 过滤，未验证 project.tenant_id == user.tenant_id
- **根因**: 新建路由时复制模板但未添加租户校验
- **正确做法**: 每个涉及 project_id 的端点，首行必须 `db.get(Project, id)` + tenant 校验
- **首次发现**: v0.43.4 - graph + api_keys 端点缺少租户隔离
- **适用范围**: 所有以 `{project_id}` 为路径参数的端点
