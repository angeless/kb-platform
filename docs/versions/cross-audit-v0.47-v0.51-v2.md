# 交叉审查报告 v2：v0.47-v0.51 开发计划 vs 实际代码

**审查日期**: 2026-04-01
**审查范围**: 5 个开发计划文件 vs 代码库实际状态
**审查重点**: 版本衔接 / 代码一致性 / 版本完整度

---

## 审查方法

1. Round 1（之前完成）：计划对计划交叉比对 — 依赖链、继承、DB schema、"不做"声明、治理合规
2. Round 2（本次）：计划对代码逐项验证 — 读取实际模型文件、配置文件、前端路由、migrations

---

## 发现汇总

| ID | 严重级 | 涉及版本 | 问题 | 状态 |
|----|--------|---------|------|------|
| C-1 | 🔴 CRITICAL | v0.47.6 | FK 引用 `pipeline_job.id`，实际表名为 `job` | ✅ 已修复 |
| C-2 | 🔴 CRITICAL | v0.47.1, v0.50.1/2/6 | 使用不存在的 `published`/`reviewing` 状态值 | ✅ 已修复 |
| H-1 | 🟠 HIGH | v0.49.6 | `embedding_vec` 列已存在，migration 会重复创建 | ✅ 已修复 |
| H-2 | 🟠 HIGH | v0.51.1 | S3 配置字段 (`s3_endpoint` 等) 已存在于 settings.py | ✅ 已修复 |
| M-1 | 🟡 MEDIUM | v0.50.3 | `review/page.tsx` 已存在，标记为"新增"错误 | ✅ 已修复 |
| M-2 | 🟡 MEDIUM | v0.50.6 | `KnowledgeDoc.doc_type` 字段已存在 | ✅ 已修复 |

---

## 详细发现

### C-1: v0.47.6 pipeline_job FK 引用错误

**代码事实**: `packages/shared-models/shared_models/job.py` → `__tablename__ = "job"`
**计划错误**: `FK→pipeline_job.id`（4 处引用）
**影响**: Alembic migration 将失败，`pipeline_job` 表不存在
**修复**: 所有 `pipeline_job.id` → `job.id`，风险预判中的不确定项标记为"已确认"

### C-2: KnowledgeDoc 状态值错误

**代码事实**: `knowledge.py:39` → `status: default="draft"`，合法值: `draft / pending / approved / rejected / archived`
**计划错误**: v0.47.1 使用 `published`/`reviewing`；v0.50 状态机写 `approved → doc.status = "published"`
**影响**: 编码时会写入无效状态值，查询条件永远匹配不到
**修复**: v0.47.1 全部替换为正确枚举值（3 处）；v0.50 全部 `published` → `approved`（7 处）；§1.2 继承列表修正

### H-1: v0.49.6 pgvector embedding_vec 列已存在

**代码事实**: `embedding.py:33` → `embedding_vec = mapped_column(Vector(1536), nullable=True)`，由迁移 `a1b2c3d4e5f6` / `b2c3d4e5f6a7` 创建
**计划错误**: migration 包含 `CREATE EXTENSION` + `ADD COLUMN` 步骤
**影响**: Alembic migration 报列已存在错误
**修复**: 移除 `CREATE EXTENSION` 和 `ADD COLUMN` 步骤，保留数据回填和 HNSW 索引创建

### H-2: v0.51.1 S3 配置字段已存在

**代码事实**: `settings.py:67-71` → `s3_endpoint, s3_access_key, s3_secret_key, s3_bucket, s3_region` 全部已有
**计划错误**: "新增 s3_bucket / s3_region / s3_endpoint"
**影响**: 重复声明会被 Pydantic 忽略但造成混淆
**修复**: 明确标注已有字段，仅需新增 `storage_backend` 切换开关

### M-1: v0.50.3 review/page.tsx 已存在

**代码事实**: `apps/web/src/app/(dashboard)/projects/[id]/review/page.tsx` 已存在
**计划写法**: 暗示"新增"页面
**修复**: 改为"重构已有页面"

### M-2: v0.50.6 doc_type 字段已存在

**代码事实**: `knowledge.py:36` → `doc_type: Mapped[str] = mapped_column(String(30))`
**计划写法**: Phase 1 前置确认"确认 doc_type 是否存在"
**修复**: 标记为"已确认存在"

---

## 版本衔接验证（Round 1 结论维持）

| 检查项 | 结果 |
|-------|------|
| v0.47→v0.48 依赖链 | ✅ 正确，v0.48 依赖 v0.47 连接池 |
| v0.48→v0.49 依赖链 | ✅ 正确，v0.49 IR 依赖 v0.48 readability |
| v0.49→v0.50 依赖链 | ✅ 正确，v0.50 审批依赖 v0.49 反思循环 |
| v0.50→v0.51 依赖链 | ✅ 正确，v0.51 水平扩展可独立部署 |
| §1.2 继承列表完整性 | ✅ 已修复（v0.49 补充 v0.48 能力；v0.50 修正状态值列表） |

## 版本完整度验证

| 检查项 | 结果 |
|-------|------|
| PRD 覆盖率 | ~92-95%，覆盖 PRD §1-§17 核心需求 |
| WISHLIST 16 项 | 全部分配到 v0.47-v0.51（W-01~W-16） |
| 43 个原子任务 | 顺序 ID、有效 DAG、无循环依赖 |
| 治理规范合规 | 所有任务含 10 必填字段（Goal/改动范围/DB/API/业务规则/验收标准/工作范围/预估/风险/Phase 1） |

---

## 修复文件清单

| 文件 | 修改数 | 涉及 ID |
|------|--------|---------|
| `docs/dev-plans/dev-plan-v0.47.md` | 7 处 | C-1, C-2 |
| `docs/dev-plans/dev-plan-v0.49.md` | 3 处 | H-1 |
| `docs/dev-plans/dev-plan-v0.50.md` | 8 处 | C-2, M-1, M-2 |
| `docs/dev-plans/dev-plan-v0.51.md` | 1 处 | H-2 |

---

**结论**: 6 项代码-计划不一致已全部修复。v0.47-v0.51 开发计划现与代码库实际状态一致，可进入 v0.47.1 开发。
