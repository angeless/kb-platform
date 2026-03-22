# 第四部分：过程文件管理（§4.1–§4.6）

> **导航**: [← 返回索引](dev-governance.md) | [← 第三部分：操作指南](dev-governance-part3-guides.md) | [第五部分：接力协议 →](dev-governance-part5-handover.md)
>
> 本文件是 `dev-governance.md` 拆分后的第四部分。
>
> **TL;DR（上下文受限时仅读此块）**:
> 过程文件统一存放规则：审计报告 `docs/versions/audit-report-vX.Y.Z.md`、测试报告 `docs/versions/test-report-vX.Y.Z.md`、开发计划 `docs/dev-plans/dev-plan-vX.Y.md`、实施计划 `docs/dev-plans/impl-plan-vX.Y.Z.md`、审计请求 `docs/dev-plans/audit-request-vX.Y.Z.md`（跨 Session 审计时，详见 §5.5）、决策记录 `docs/decisions/ADR-{序号}-{主题}.md`。所有过程文件永久保留，命名必须包含版本号以支持追溯。

---

# 第四部分：过程文件管理

> 本部分定义如何规范存储和管理开发过程中产生的各类文件。

所有过程文件必须规范存放、命名清晰、可追溯：

## 4.1 审计记录

**位置：** `docs/versions/`

**命名规则：** `audit-report-v{{X.Y.Z}}.md`

**保留期：** 永久保留

## 4.2 测试报告

**位置：** `docs/versions/`

**命名规则：** `test-report-v{{X.Y.Z}}.md`

**保留期：** 永久保留

## 4.3 开发计划

**位置：** `docs/dev-plans/`

**命名规则：** `dev-plan-v{{X.Y}}.md`

**保留期：** 永久保留

## 4.4 实施计划

**位置：** `docs/dev-plans/`

**命名规则：** `impl-plan-v{{X.Y.Z}}.md`

**保留期：** 永久保留

## 4.5 审计请求（跨 Session 审计）

**位置：** `docs/dev-plans/`

**命名规则：** `audit-request-v{{X.Y.Z}}.md`

**保留期：** 永久保留

**说明：** 当高风险任务需要跨 Session 独立审计时（详见 §5.5），由编码 Agent（Session A）在 Phase 4 ② 创建。内容包含：任务编号、涉及文件清单、关键设计决策、已知风险点、需要重点审计的规范条目。审计 Agent（Session B）读取此文件后独立执行 Phase 4 ③ Part B/C/D 门禁。

## 4.6 决策记录（ADR）

**位置：** `docs/decisions/`

**命名规则：** `ADR-{{序号}}-{{主题}}.md`

**内容结构：**
```markdown
# ADR-{{序号}} - {{决策标题}}

## 状态
Accepted / Proposed / Superseded

## 背景
为什么要做这个决策？

## 决策
我们决定：...

## 后果
正面结果：...
负面结果：...

## 替代方案
- 方案 A：...
- 方案 B：...
```

**保留期：** 永久保留

---
