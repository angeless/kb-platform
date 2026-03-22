# 附录：修改边界铁律 + 四文档关系说明

> **导航**: [← 返回索引](dev-governance-index.md) | [← 第五部分：接力协议](dev-governance-part5-handover.md)
>
> 本文件是 `dev-governance.md` 拆分后的附录部分。
>
> **TL;DR（上下文受限时仅读此块）**:
> 修改边界铁律共 20 条（分 5 类：流程纪律 1-6、范围纪律 7-10、代码保护纪律 11-14、文件保护纪律 15-16、质量纪律 17-20），权威定义在 §0.5，本处仅为提醒入口。四文档关系：architecture.md（系统长什么样）、coding-standards.md（代码怎么写）、dev-governance.md（开发怎么走）、testing-strategy.md（怎么做测试），均位于 `docs/tech-specs/`。

---

## 修改边界铁律

> **⚠️ 本节不重复定义铁律条目。唯一权威定义见 §0.5（全局禁止事项与修改边界铁律）。**
>
> 放在文档末尾便于快速定位。所有 Agent 在执行任何任务前，必须已读取 §0.5 的完整内容。本处仅作为提醒入口：
>
> - 共 20 条铁律，分 5 类：流程纪律（1-6）、范围纪律（7-10）、代码保护纪律（11-14）、文件保护纪律（15-16）、质量纪律（17-20）
> - 任何一条被违反 → 立即停止当前操作并报告
> - 如需查阅具体条目，请读取 `docs/tech-specs/dev-governance.md` §0.5

---

# 附录：四文档关系说明

本项目的技术规范分为四个核心文档：

| 文档 | 位置 | 职责 | 内容 |
|-----|------|------|------|
| **architecture.md** | `docs/tech-specs/` | 系统长什么样 | 模块划分、依赖关系、数据流 |
| **coding-standards.md** | `docs/tech-specs/` | 代码怎么写 | 命名、注释、异常处理 |
| **dev-governance.md** | `docs/tech-specs/` | 开发怎么走 | 版本管理、计划、迭代流程 |
| **testing-strategy.md** | `docs/tech-specs/` | 怎么做测试 | 类型分类、频次、流程、用例规范、路径管理、报告命名、数据管理 |

**使用场景：**
- 需要理解系统架构？→ 读 architecture.md
- 需要知道代码应该怎么写？→ 读 coding-standards.md
- 需要了解开发流程？→ 读 dev-governance.md
- 需要了解测试策略？→ 读 testing-strategy.md
- 需要执行一个迭代周期？→ 按照 dev-governance.md 第 3 部分的 7 个 Phase 执行

---

*文档结束*
