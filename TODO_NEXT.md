# TODO_NEXT

## 上次停在
- 版本：v0.50.1 | 分支：test-v-0-48-a | 最后完成：v0.50.1 ReviewTask 审批模型 + 状态机
- v0.45-v0.49 全部完成 ✅
- v0.50.1 完成 ✅（审批工作流 DB 模型）

## 下一步

### v0.50.2 — 审批工作流 API（分配/批准/驳回/重新提交）
- 新增 review_service.py + review router
- CRUD + 状态转换端点
- 审批通过时同步更新 doc.status = approved
- 角色控制：project_admin 分配，reviewer 审批

### 随后
- v0.50.3-4: 审批前端（看板 + 操作组件）
- v0.50.5: 高危操作二次确认
- v0.50.6-7: 术语表 + 维护指南文档模板
- v0.50.8: 模型成本看板

## 注意事项
- migrations 待执行：u0i1j2k3l4m5(IR), v1w2x3y4z5a6(HNSW), w2x3y4z5a6b7(idempotency), x3y4z5a6b7c8(review_task)
- 分支 test-v-0-48-a 包含 v0.48+v0.49+v0.50.1（16 个任务）
- KnowledgeDoc.status 合法值：draft/pending/approved/rejected/archived
- ReviewTask 状态机：pending→assigned→approved/rejected→resubmitted
