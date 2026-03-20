# 第一部分：文件保护与 TODO_NEXT（§1.7–§1.8）

> **导航**: [← 返回索引](dev-governance-index.md) | [← 分支策略](dev-governance-part1-branch.md) | [并行开发 →](dev-governance-part1-parallel.md)
>
> 本文件是 `dev-governance-template.md` 拆分后的第一部分（§1.7–§1.8）。
>
> **TL;DR（上下文受限时仅读此块）**:
> 三级文件保护：Tier 1（绝对禁止）= 技术规范四件套 + UI 规范，任何任务都不可修改；Tier 2（封板后禁止）= 已完成的开发计划/报告/审计文件；Tier 3（条件保护）= CI 配置/Docker/部署文件，仅当任务定义明确列出时才允许修改。违反任何一条 → 门禁立即失败。TODO_NEXT.md 是开发计划的状态快照，每次 Phase 6 收尾时整体覆写更新。

---

## 1.7 禁止修改文件清单

> 本节定义哪些文件在开发过程中受到保护，AI 开发者不得擅自修改。
> Phase 1 ① 规范输入要求阅读本节；Phase 1 ③ 门禁和 Phase 4 ③ Part D 门禁要求核对本节。

### 保护层级说明

本清单分为三个保护层级，保护力度依次递减：

| 层级 | 含义 | 违反后果 |
|------|------|---------|
| **Tier 1：绝对禁止** | 任何任务中都不允许修改，无论理由多么充分 | 门禁立即失败，停止等待用户介入 |
| **Tier 2：封板后禁止** | 对应版本/任务封板（状态变为 `Sealed` 或 `Released`）后禁止修改 | 门禁立即失败，停止等待用户介入 |
| **Tier 3：条件保护** | 仅当当前任务定义中**明确列出**该文件为改动范围时才允许修改 | 未授权修改 → 门禁失败；已授权 → 正常通过 |

### Tier 1：绝对禁止

以下文件在任何情况下都**不允许 AI 开发者修改**。如需变更，必须由人类开发者或项目负责人手动修改。

| 文件/路径 | 说明 |
|-----------|------|
| `docs/tech-specs/dev-governance.md` | 开发治理流程（本文件的项目实例） |
| `docs/tech-specs/coding-standards.md` | 编码标准规范 |
| `docs/tech-specs/architecture.md` | 系统架构规范 |
| `docs/tech-specs/testing-strategy.md` | 测试策略规范 |
| `docs/ui-design-spec.html` | UI 设计规范 |

**理由：** 这些文件是"规则本身"。如果执行者可以修改规则，则所有规则都将失去约束力。

**升级流程豁免条款：**
> 在执行 dev-workflow-upgrade 升级流程（阶段 1-7）期间，Tier 1 文件保护暂不生效。
> 这是因为升级流程本身的目的就是创建或更新这些规范文件。
> 升级阶段 7 验证通过并完成最终 commit 后，Tier 1 保护正式启用，此后任何修改必须由人类开发者或项目负责人手动执行。

### Tier 2：封板后禁止

以下文件在**对应版本/任务封板后**不允许修改。封板前按正常流程操作。

| 文件/路径模式 | 封板条件 | 说明 |
|--------------|---------|------|
| `docs/dev-plans/dev-plan-vX.Y.md` | 对应功能项（vX.Y）所有任务状态变为 `Sealed` | 已封板的开发计划 |
| `docs/dev-plans/impl-plan-vX.Y.Z.md` | 对应任务（vX.Y.Z）状态变为 `Completed` | 已完成任务的实施计划 |
| `docs/versions/task-report-vX.Y.Z.md` | 文件创建即封板 | 已归档的任务报告 |
| `docs/versions/audit-report-vX.Y.Z.md` | 文件创建即封板 | 已归档的审计报告 |
| `docs/versions/test-report-vX.Y.Z.md` | 文件创建即封板 | 已归档的测试报告 |
| `docs/versions/phase-report-vX.Y.md` | 文件创建即封板 | 已归档的阶段报告 |
| `docs/versions/RELEASE_NOTES_vX.md` | 文件创建即封板 | 已归档的版本发布说明 |
| `docs/versions/seal-audit-vX.Y.md` | 文件创建即封板 | 已归档的大版本封板审计报告 |
| 已打 tag 的 `VERSION` 快照 | `git tag` 创建后 | tag 对应的版本号不可回退 |

**理由：** 这些文件是历史记录，保证过程可追溯。封板前开发计划可按 §2.4 变更记录流程正常修改。

**封板判定规则：**
- **任务级封板：** 当任务状态流转到 `Completed` 时，该任务的 impl-plan、task-report、audit-report、test-report 自动封板
- **功能项级封板：** 当功能项下所有任务状态流转到 `Sealed` 时，该功能项的 dev-plan、phase-report 自动封板
- **版本级封板：** 当版本所有功能项封板并打 tag 后，RELEASE_NOTES 自动封板

### Tier 3：条件保护

以下文件默认受保护，但如果**当前任务定义中明确将其列为改动范围**，则允许修改。

| 文件/路径模式 | 说明 |
|--------------|------|
| `.env.example` / `.env.template` | 环境变量模板 |
| `docker-compose*.yml` | 容器编排配置 |
| `infra/docker/Dockerfile*` | 容器构建配置（4 个 Dockerfile） |
| `.github/workflows/*.yml` / `.gitlab-ci.yml` | CI/CD 流水线配置（尚未配置） |
| `scripts/ci_verify.sh` | 整合检查脚本 |
| `nginx*.conf` / 部署配置文件 | 部署相关配置 |
| `Makefile` / `justfile` | 构建入口脚本 |
| `packages/shared-config/` | 共享配置包（影响所有服务） |
| `alembic.ini` / `alembic/env.py` | 数据库迁移配置 |

**理由：** 这些文件影响范围大（环境、构建、部署），但在实际开发中经常需要随功能调整。通过复用「任务定义中明确列出才能修改」的现有规则，不增加额外审批成本，同时防止 AI 在任务范围外擅自修改。

### 违规处理

1. **Phase 1 门禁检查**（预防）：在实施计划阶段，将预计修改文件清单与本节逐一比对
   - 命中 Tier 1 → 立即停止，报告冲突，等待用户介入
   - 命中 Tier 2 且已封板 → 立即停止，报告冲突，等待用户介入
   - 命中 Tier 3 且未在任务定义中授权 → 立即停止，报告冲突，等待用户介入
2. **Phase 4 Part D 门禁检查**（事后验证）：审计阶段对照实际修改文件，再次验证是否有未授权的禁止文件被修改
   - 发现违规 → 门禁失败，必须回退对应修改后才能继续

## 1.8 TODO_NEXT.md 文件管理

> 本文件是开发计划的**状态快照/视图**，用于快速判断"下一个该做什么"。
> 它不是独立的任务管理系统——所有任务定义、验收标准等权威信息仍以 `docs/dev-plans/dev-plan-vX.Y.md` 为准。

**位置：** `/项目根目录/TODO_NEXT.md`

**定位：** 开发计划的轻量状态视图。Agent 启动时（§0.8 快速启动命令）首先读取此文件，即可快速定位当前进度，无需遍历全部计划文档。

**生成与更新规则：**
- **首次创建**：在第一个 `vX.Y.Z` 任务的 Phase 6 收尾时自动创建
- **每次更新**：每完成一个任务的 Phase 6 收尾时，必须同步更新此文件
- **数据来源**：从 `docs/dev-plans/dev-plan-vX.Y.md` 中提取任务状态，生成快照
- **更新方式**：整体覆写（不是追加），每次都重新生成完整状态

**文件格式：**

```markdown
# TODO_NEXT — 开发进度快照

> 自动生成于 {{YYYY-MM-DD HH:MM}}，数据来源：docs/dev-plans/dev-plan-v{{X.Y}}.md
> 本文件是开发计划的状态快照，不是权威任务定义。任务详情请查阅对应的开发计划文档。

## 当前版本：v{{X.Y}}

## 下一个待执行任务

- **任务版本号：** v{{X.Y.Z}}
- **任务名称：** {{任务名称}}
- **所属功能项：** v{{X.Y.0}} — {{功能项名称}}
- **开发计划位置：** `docs/dev-plans/dev-plan-v{{X.Y}}.md` → 任务 v{{X.Y.Z}}

## 任务状态总览

| 任务版本号 | 任务名称 | 状态 | 完成日期 |
|----------|--------|------|---------|
| v{{X.Y.1}} | {{任务1}} | ✅ Completed | {{日期}} |
| v{{X.Y.2}} | {{任务2}} | ✅ Completed | {{日期}} |
| v{{X.Y.3}} | {{任务3}} | 🔲 Planned | — |
| v{{X.Y.4}} | {{任务4}} | 🔲 Planned | — |

## 版本进度

- 已完成：{{N}} / {{总数}} 任务
- 当前功能项：v{{X.Y.0}} — {{功能项名称}}（{{M}} / {{功能项总数}} 任务完成）
- VERSION 文件当前值：0.39.0
```

**与开发计划的关系：**
- TODO_NEXT.md 中的任务状态必须与 `dev-plan-vX.Y.md` 中的状态完全一致
- 如果发现不一致，以 `dev-plan-vX.Y.md` 为准，并在当前 Phase 6 中修正 TODO_NEXT.md
- TODO_NEXT.md 不记录任务的详细定义（目标、验收标准等），只记录状态

---
