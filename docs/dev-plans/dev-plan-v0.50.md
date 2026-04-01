# KB Platform v0.50 版本开发任务计划

**文档编号**: PLAN-2026-03-31-v050
**版本**: V1.0（初始版）
**日期**: 2026-03-31
**基线**: v0.49 完成后
**依据**: PRD §7（审批工作流）+ §4.6（高危操作）+ §8（核心产出）
**作者**: Claude Code（自动生成）

---

## 第一章 版本主题

**v0.50：工作流 & 治理 — 审批引擎 + 高危操作确认 + 文档模板扩展**

> 从"工具平台"升级为"治理平台"：引入正式的审批工作流、高危操作二次确认机制、以及术语表/维护指南等专业文档模板。v0.50 完成后，平台满足企业级知识治理要求。

---

## 第二章 任务列表

| 任务版本号 | 任务名称 | 优先级 | 状态 | 来源 |
|----------|--------|------|------|------|
| v0.50.1 | 审批工作流 DB 模型 — ReviewTask 表 + 状态机 | P0 | 待开发 | PRD §7 |
| v0.50.2 | 审批工作流 API — 分配/批准/驳回/重新提交 | P0 | 待开发 | PRD §7 |
| v0.50.3 | 审批工作流前端 — 审批中心页重构 | P0 | 待开发 | PRD §7 |
| v0.50.4 | 高危操作二次确认 — 确认码机制 | P1 | 待开发 | PRD §4.6 |
| v0.50.5 | 术语表文档模板 — 新增 doc_type="glossary" | P1 | 待开发 | PRD §8 |
| v0.50.6 | 维护指南文档模板 — 新增 doc_type="maintenance_guide" | P2 | 待开发 | PRD §8 |
| v0.50.7 | 模型成本看板前端页 | P2 | 待开发 | PRD §5 UX |

---

## 第三章 目标与边界

### 3.1 北极星校验

| 任务 | Q1 强化核心链路？ | Q2 强化接口？ | Q3 必要支撑？ |
|-----|----------------|-------------|-------------|
| v0.50.1 | ✅ 图谱质量（审批保障发布质量） | - | - |
| v0.50.2 | ✅ 图谱质量 | ✅ 输出接口 | - |
| v0.50.3 | - | ✅ 输出接口 | - |
| v0.50.4 | - | - | ✅ 安全治理 |
| v0.50.5 | ✅ 图谱端（术语统一） | ✅ 输出接口 | - |
| v0.50.6 | - | ✅ 输出接口 | - |
| v0.50.7 | - | ✅ 输出接口 | - |

### 3.2 明确不做

- 多级审批（总监→VP→CEO）— v0.50 仅支持单级审批（一个审批人）
- 审批 SLA（超时自动升级）— 留给未来版本
- 审批规则引擎（根据内容类型自动选择审批人）— 留给未来版本

---

## 第四章 执行顺序

```
审批链：v0.50.1 → v0.50.2 → v0.50.3
安全链：v0.50.4（依赖 v0.50.2 的确认模式可复用）
文档链：v0.50.5 → v0.50.6（独立）
看板：v0.50.7（依赖 v0.49.7 成本数据）
```

建议：`v0.50.1 → v0.50.2 → v0.50.3 → v0.50.4 → v0.50.5 → v0.50.6 → v0.50.7`

---

## 第五章 各任务详细定义

---

### v0.50.1: 审批工作流 DB 模型

**前置依赖：** 无

**变更：**
- `packages/shared-models/shared_models/review_task.py` — 新模型：
  ```
  ReviewTask:
    id, project_id, doc_id, reviewer_id(nullable),
    status: "pending" | "assigned" | "approved" | "rejected" | "resubmitted",
    assigned_at, reviewed_at, review_note,
    created_by, created_at, updated_at
  ```
- `infra/sql/alembic/versions/` — migration
- 约 40 行

**状态机：**
```
pending → assigned（分配审批人）
assigned → approved | rejected（审批人操作）
rejected → resubmitted（作者修改后重新提交）
resubmitted → assigned（自动重新分配）
approved → (doc.status = "published")
```

---

### v0.50.2: 审批工作流 API

**前置依赖：** v0.50.1

**变更：**
- `services/api/app/routers/review.py` — 新路由：
  - `POST /v1/reviews` — 创建审批任务
  - `POST /v1/reviews/{id}/assign` — 分配审批人（project_admin）
  - `POST /v1/reviews/{id}/approve` — 批准（reviewer+）
  - `POST /v1/reviews/{id}/reject` — 驳回 + 原因
  - `POST /v1/reviews/{id}/resubmit` — 修改后重新提交
  - `GET /v1/reviews` — 审批任务列表（按状态/项目筛选）
- `services/api/app/services/review_service.py` — 业务逻辑 + 状态转换
- 审批通过时自动 publish doc
- 约 150 行

---

### v0.50.3: 审批工作流前端

**前置依赖：** v0.50.2

**变更：**
- `apps/web/src/app/(dashboard)/projects/[id]/review/page.tsx` — 重构：
  - 审批任务看板（待分配 / 待审批 / 已完成）
  - 分配审批人弹窗
  - 审批/驳回表单 + 备注
  - 审批历史时间线
- 约 200 行前端

---

### v0.50.4: 高危操作二次确认

**前置依赖：** v0.50.2

**背景：** PRD §4.6 要求发布架构主版本、回滚文档、删除项目、修改默认模型路由等操作需二次确认。

**变更：**
- `services/api/app/utils/confirmation.py` — 确认码生成/验证：
  - 生成 6 位随机码存入 Redis（TTL 5 分钟）
  - 第一次请求返回 `{"requires_confirmation": true, "confirmation_id": "xxx"}`
  - 第二次请求携带 confirmation_id + code 才执行
- 高危端点加 `@require_confirmation` 装饰器：
  - `POST /architectures/{id}/publish`
  - `POST /docs/{id}/versions/{v}/rollback`
  - `DELETE /projects/{id}`
  - `PATCH /model-routes/{id}`（修改默认路由时）
- 约 60 行后端 + 前端确认弹窗组件

---

### v0.50.5: 术语表文档模板

**前置依赖：** 无

**变更：**
- `services/pipeline-worker/worker/stages/doc_generate.py` — 新增 `generate_glossary()` 函数
  - 从所有 chunk 中提取专业术语
  - 按字母/拼音排序
  - 生成 Markdown 术语表（术语 | 定义 | 首次出现文档）
- `services/ai-orchestrator/orchestrator/prompts.py` — 新增术语提取 prompt
- 约 60 行

---

### v0.50.6: 维护指南文档模板

**前置依赖：** v0.50.5

**变更：**
- `services/pipeline-worker/worker/stages/doc_generate.py` — 新增 `generate_maintenance_guide()` 函数
  - 分析架构节点的 update_policy、review_policy
  - 生成维护指南（更新频率建议、审批流程、质量标准）
- 约 40 行

---

### v0.50.7: 模型成本看板前端页

**前置依赖：** v0.49.7

**变更：**
- `apps/web/src/app/(dashboard)/settings/costs/page.tsx` — 新页面：
  - 按模型 / 按 task_type / 按日期的 token 消耗图表
  - 预算使用百分比进度条
  - 超限告警历史
- `services/api/app/routers/model_providers.py` — 新增 `GET /v1/model-usage/summary` 聚合端点
- 约 100 行前端 + 30 行后端

---

## 第六章 风险

| 风险 | 缓解 |
|------|------|
| 审批工作流增加文档发布延迟 | 默认关闭，项目级配置开启 |
| 确认码存 Redis 依赖 | 降级方案：内存 dict（单实例限制） |
| 术语提取 LLM 成本 | 复用已有 chunk 分类结果，减少重复调用 |
