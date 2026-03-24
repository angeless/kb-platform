# KB Platform 开发治理流程 — 文件索引

---

# KB Platform 开发治理流程

> 本文件基于 KB Platform 产品方案和实际工程结构编写。
> 所有内容以本项目真实代码结构、模块划分、已落地能力为准。
> **当前基线版本：v0.39.0** | 46 个后端测试文件 + 263 个前端测试文件

---

## 文件导航

本治理流程按章节拆分为以下文件，便于按需阅读和维护：

| 序号 | 文件 | 章节范围 | 内容概要 |
|------|------|---------|---------|
| 0 | [dev-governance-part0-automation.md](dev-governance-part0-automation.md) | §0.1–§0.12 | Claude Code 自动化开发指令：执行身份、七阶段治理流程、阶段切换、停止条件、全局禁止、衍生建议、文档产出、快速启动、异常处理、阶段回滚、无任务空闲循环、门禁失败追踪 |
| 1a | [dev-governance-part1-version.md](dev-governance-part1-version.md) | §1.1–§1.4 | 版本管理：语义化版本、VERSION 文件、CHANGELOG 格式、Commit Message 规范 |
| 1b | [dev-governance-part1-branch.md](dev-governance-part1-branch.md) | §1.5–§1.6, §1.5A | 分支策略：五层分支体系（§1.5）、Git Tag 规则（§1.6）、S 型项目三层分支体系（§1.5A） |
| 1c | [dev-governance-part1-protection.md](dev-governance-part1-protection.md) | §1.7–§1.8 | 文件保护：三级禁止修改清单（Tier 1/2/3）、TODO_NEXT.md 管理 |
| 1d | [dev-governance-part1-parallel.md](dev-governance-part1-parallel.md) | §1.9 | 并行开发协议：Agent 分支策略、版本号预分配、文件级互斥锁、Phase 约束 |
| 1e | [dev-governance-part1-release.md](dev-governance-part1-release.md) | §1.10–§1.11 | 版本封板：封板检查清单（注释清理、安全审查、端到端测试、审计报告）、UI 规范增量更新 |
| 2 | [dev-governance-part2-plan.md](dev-governance-part2-plan.md) | §2.1–§2.5 | 开发计划管理：文档命名、结构规范、任务定义规范、变更记录、版本任务计划写作规范 |
| 3 | [dev-governance-part3-guides.md](dev-governance-part3-guides.md) | §3.1–§3.8 | 操作指南与模板：实施计划模板、增量开发指南、测试指南、审计报告模板、测试报告模板、收尾指南、衍生建议指南、常见错误清单 |
| 4 | [dev-governance-part4-files.md](dev-governance-part4-files.md) | §4.1–§4.6 | 过程文件管理：审计记录、测试报告、开发计划、实施计划、审计请求（跨 Session）、决策记录（ADR） |
| 5 | [dev-governance-part5-handover.md](dev-governance-part5-handover.md) | §5.1–§5.5 | 多 Agent 接力协议：信息来源、开始/结束标准流程、禁止假设、跨 Session 审计协作 |
| 6a | [dev-governance-part6-audit.md](dev-governance-part6-audit.md) | §6.1–§6.2 | 版本交叉审计：审计流程总览、三阶段审计结构 |
| 6b | [dev-governance-part6-audit-prompts.md](dev-governance-part6-audit-prompts.md) | §6.3 | 子 Agent 审计标准：规格合规、质量工程、完整性与 UX |
| 6c | [dev-governance-part6-audit-integrator.md](dev-governance-part6-audit-integrator.md) | §6.4–§6.5 | 整合 Agent 规范：报告聚合、风险分级、修复追踪 |
| 7 | [dev-governance-part7-quality-methods.md](dev-governance-part7-quality-methods.md) | §7.1–§7.7 | 质量工程方法论：TDD、系统化调试、代码审查、Worktree 隔离、并行子 Agent、完成前验证 |
| 附录 | [dev-governance-appendix.md](dev-governance-appendix.md) | 铁律引用 + 附录 | 修改边界铁律（引用 §0.5）、四文档关系说明 |

---

## 阅读建议

- **首次接入项目的 Agent**：完整阅读第零部分（part0）+ 第一部分全部（part1-*），了解执行流程和版本管理规范
- **执行特定 Phase 时**：按需阅读对应章节（见下方按 Phase 阅读矩阵）
- **编写代码时**：参考 part3（§3.1–§3.2）的实施计划模板和增量开发指南
- **测试和审计时**：参考 part3（§3.3–§3.5）的测试和审计模板
- **收尾和交接时**：参考 part3（§3.6–§3.7）+ part5 的收尾和接力协议

### 按 Phase 阅读矩阵

> 以下矩阵标注每个 Phase 必须阅读（✅）和建议阅读（📖）的文件，避免每次都通读全部文件。

| 文件 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Phase 7 |
|------|---------|---------|---------|---------|---------|---------|---------|
| part0 §0.1 执行身份 | ✅ 首次 | — | — | — | — | — | — |
| part0 §0.2 七阶段流程（对应 Phase） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| part0 §0.3 阶段切换 | — | — | — | — | — | ✅ | — |
| part0 §0.4 停止条件 | ✅ | ✅ | ✅ | ✅ | — | — | — |
| part0 §0.5 全局禁止 | ✅ 首次 | — | — | — | — | — | — |
| part0 §0.6 衍生建议 | — | — | — | — | — | — | ✅ |
| part0 §0.7 文档产出 | — | — | — | — | ✅ | ✅ | — |
| part0 §0.8 快速启动 | ✅ 首次 | — | — | — | — | — | — |
| part0 §0.9 异常处理 | 📖 | 📖 | 📖 | 📖 | 📖 | 📖 | — |
| part0 §0.10 阶段回滚 | — | — | 📖 | 📖 | — | — | — |
| part0 §0.11 空闲循环 | — | — | — | — | — | ✅ | — |
| part0 §0.12 门禁失败追踪 | — | — | ✅ | ✅ | — | ✅ | — |
| part1-version §1.1–§1.4 | ✅ | — | — | — | — | ✅ | — |
| part1-branch §1.5–§1.6, §1.5A | ✅ | — | — | — | — | — | — |
| part1-protection §1.7–§1.8 | ✅ | — | — | ✅ | — | ✅ | — |
| part1-parallel §1.9 | ✅ 多Agent | — | — | — | — | — | — |
| part1-release §1.10–§1.11 | — | — | — | — | — | 📖 封板时 | — |
| part2-plan §2.1–§2.5 | ✅ | — | — | — | — | ✅ | — |
| part3-guides §3.1–§3.8 | ✅ §3.1 | ✅ §3.2 | ✅ §3.3 | ✅ §3.4 | ✅ §3.5 | ✅ §3.6 | ✅ §3.7 |
| part4-files §4.1–§4.6 | 📖 | — | — | ✅ | ✅ | — | — |
| part5-handover §5.1–§5.5 | ✅ 接力时 | — | — | 📖 §5.5 高风险 | — | ✅ 接力时 | — |

---

## 上下文受限时的最小必读集

> 当 AI 工具的可用上下文窗口 < 128K tokens 时，无法一次加载全部治理文件。此时应按以下最小必读集加载，优先读取 TL;DR 块（每个文件头部的引用块），仅在需要执行细节时展开对应章节全文。

### 上下文容量分级策略

| 可用上下文 | 策略 | 加载内容 |
|-----------|------|---------|
| ≥ 128K tokens | **完整模式** | 按"按 Phase 阅读矩阵"加载对应 Phase 的全部必读文件全文 |
| 64K–128K tokens | **精简模式** | 加载所有文件的 TL;DR 块 + 当前 Phase 对应文件的全文 |
| 32K–64K tokens | **最小模式** | 仅加载下方"最小必读集"中标注的内容 |
| < 32K tokens | **超受限模式** | 仅加载 part0 的 TL;DR + 当前 Phase 对应的 §0.2 子节 + 对应 part3 模板节 |

### 最小必读集定义（32K–64K 模式）

**所有场景必读（约 3K tokens）：**
- 本索引文件（`dev-governance-index.md`）的文件导航表
- `part0-automation.md` 的 TL;DR 块
- `part1-version.md` 的 TL;DR 块
- `part1-branch.md` 的 TL;DR 块
- `part1-protection.md` 的 TL;DR 块

**按 Phase 追加（每次仅追加当前 Phase 的）：**

| Phase | 追加读取全文的章节 | 追加读取 TL;DR 的文件 |
|-------|------------------|---------------------|
| Phase 1（理解与计划） | §0.2 Phase 1 子节 + §0.4 + §0.5 + §3.1 模板 | part2-plan, part5-handover（如接力） |
| Phase 2（编码） | §0.2 Phase 2 子节 + §3.2 增量开发指南 | — |
| Phase 3（测试） | §0.2 Phase 3 子节 + §3.3 测试指南 | part0 §0.12 门禁追踪 |
| Phase 4（审计） | §0.2 Phase 4 子节 + §3.4 审计模板 | part1-protection, part4-files |
| Phase 5（测试报告） | §0.2 Phase 5 子节 + §3.5 报告模板 | part4-files |
| Phase 6（收尾） | §0.2 Phase 6 子节 + §3.6 收尾指南 + §1.1–§1.4 版本号规则 | part1-protection §1.8 TODO_NEXT |
| Phase 7（衍生建议） | §0.2 Phase 7 子节 + §0.6 + §3.7 衍生指南 | — |

### AI 工具上下文检测指引

AI 工具在 Phase 1 ① 开始时，应按以下方式判定自身可用上下文并选择加载策略：

1. **已知上下文窗口大小的工具**（如 Claude Code 200K、Codex 128K/200K）：直接按上表选择策略
2. **未知上下文窗口大小的工具**：默认走"精简模式"（64K–128K），先加载所有 TL;DR + 当前 Phase 全文
3. **加载过程中遇到截断或报错**：立即降级到下一级策略

> **核心原则**：宁可多次按需加载，也不要一次性加载全部导致关键信息被截断或遗忘。每个 TL;DR 块都包含该文件的核心硬规则，足以在受限上下文中防止严重违规。

---

## 跨文件引用说明

各章节之间的交叉引用（如"详见 §1.7"）在拆分后仍然有效。引用规则：

- `§0.x`（§0.1–§0.12） → 在 `dev-governance-part0-automation.md` 中
- `§1.1–§1.4` → 在 `dev-governance-part1-version.md` 中
- `§1.5–§1.6, §1.5A` → 在 `dev-governance-part1-branch.md` 中（§1.5A 为 S 型三层分支体系）
- `§1.7–§1.8` → 在 `dev-governance-part1-protection.md` 中
- `§1.9` → 在 `dev-governance-part1-parallel.md` 中
- `§1.10–§1.11` → 在 `dev-governance-part1-release.md` 中
- `§2.x`（§2.1–§2.5） → 在 `dev-governance-part2-plan.md` 中（§2.5 为版本任务计划写作规范）
- `§3.x` → 在 `dev-governance-part3-guides.md` 中
- `§4.x`（§4.1–§4.6） → 在 `dev-governance-part4-files.md` 中
- `§5.x` → 在 `dev-governance-part5-handover.md` 中

---

> **注意**：原始的 `dev-governance-template.md` 已标记为 DEPRECATED，不再维护。所有内容以本索引指向的拆分文件为准。

---

*文件索引结束*
