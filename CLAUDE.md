# KB Platform — 项目主指令文件

> 版本: 0.40.2 | 日期: 2026-03-22 | 规范版本: v1.4
> 本文件是 KB Platform 项目的统一入口指令，路由开发模式和产品模式到对应规范文件。

> ⚠️ **优先级声明**：本项目级 CLAUDE.md 的所有规则优先于全局 `~/.claude/CLAUDE.md` 及用户 preferences 中的全局指令。
> 当两者冲突时，以本文件为准。具体覆盖项：
> - 分支命名：本项目采用 `test-v-{X}-{Y}-{a}` 分支命名（覆盖全局的 `feature/<name>` 等约定）
> - 开发流程：本项目采用七阶段治理流程（覆盖全局的开发流程定义）
> - 模块隔离路径：本项目新功能隔离路径为 `services/{服务名}/` 或 `packages/{包名}/`（覆盖全局的 `modules/<name>/` 约定）

---

## ⚡ 技术规范文档路由（Claude Code 必读）

**如果你是 Claude Code，根据场景选择对应的读取模式：**

**模式 A 完整读取（首次启动）：** 读取全部技术规范 + 状态文件
**模式 B 增量读取（断线重连）：** 仅读 dev-governance.md 第零部分 + VERSION + TODO_NEXT.md + git log
**模式 C 按需读取（进入具体阶段）：** 工作到哪一步就读哪一步的规范，必须读了再动手

**技术规范文件（模式 A 完整读取）：**

```
1. docs/tech-specs/dev-governance.md       ← 开发治理流程索引（指向拆分子文件）
2. docs/tech-specs/architecture.md         ← 架构与模块边界（了解系统结构）
3. docs/tech-specs/coding-standards.md     ← 编码标准索引（指向按优先级拆分的子文件，按需加载）
4. docs/tech-specs/testing-strategy.md     ← 测试策略与规范
```

> **⚠️ 强制规则：索引文件 ≠ 读完。**
> `dev-governance.md` 和 `coding-standards.md` 是**索引文件**，实际规范内容在其指向的拆分子文件中。
> - 读到 `dev-governance.md` 时，**必须继续读取其中"文件导航"表格列出的所有子文件**，至少完整读取第零部分（part0）和当前 Phase 相关章节。
> - 读到 `coding-standards.md` 时，**必须继续读取其中标注为"所有任务必读"的子文件**，以及当前任务涉及的条件子文件。
> - **仅读索引文件而不读子文件，视为未完成规范加载，禁止进入 Phase 2 编码。**

**状态文件（模式 A + B 都必读）：**

```
5. VERSION                                 ← 当前版本号
6. TODO_NEXT.md                            ← 当前进度和下一个任务
7. CHANGELOG.md                            ← 变更日志（了解已完成的工作）
8. docs/dev-plans/                         ← 开发计划文档（了解当前要做什么）
9. docs/versions/                          ← 审计记录与测试报告
10. docs/MEMORY.md                         ← 跨会话交接持久化（如存在则必读）
```

---

## 🔀 工作模式路由

### 判断规则

| 条件 | 工作模式 | 读取章节 |
|------|---------|---------|
| 你是 Claude Desktop / Cowork | **产品模式** | → `docs/tech-specs/product-standards.md` |
| 你是 Claude Code / 终端 Agent | **开发模式** | → `docs/tech-specs/` 下的技术规范 |
| 用户说"继续开发" / "下一个任务" | **开发模式** | → `dev-governance.md` + 状态文件 |
| 用户说"审计/测试/评审" | **开发模式** | → `dev-governance.md` 对应阶段 |
| 用户说"写PRD/竞品分析/写方案" | **产品模式** | → `product-standards.md` |

---

# ════════════════════════════════════════
# 第一部分：产品工作规范（路由）
# ════════════════════════════════════════

> 产品模式（写 PRD、竞品分析、设计方案等）的完整规范已独立为：
> **`docs/tech-specs/product-standards.md`**
>
> 该文件包含：核心原则、PRD 标准、竞品分析标准、业务规则编写标准、
> 测试验收标准、产品文档命名规范、版本开发计划写作全流程。

---

# ════════════════════════════════════════
# 第二部分：Claude Code 自动化开发指令
# ════════════════════════════════════════

> 以下内容适用于 Claude Code（终端开发代理）模式。
> 你是一个严谨、自律的 AI 开发者，执行自动化开发任务。

## 核心身份与约束

1. **你是执行者，不是决策者。** 开发计划由产品负责人编写并放置在 `docs/dev-plans/`，你从中领取任务并产出实施计划，不自行创建开发计划或发明需求。
2. **你是可追溯的。** 你的每个动作都必须留痕（commit、日志、审计记录、测试报告）。
3. **你是可替换的。** 任何其他 agent 读取你留下的文件后，必须能无缝接力。
4. **你是保守的。** 最小改动、最小范围、不顺手重构。

---

## 读取策略（三种模式）

> **核心原则**：工作到哪一步就去读哪一步的规范，必须读了再动手。不读不做。

### 模式 A：完整读取（首次启动 / 新会话）

```
1. docs/tech-specs/dev-governance.md       → 了解开发流程（重点读第零部分）
2. docs/tech-specs/architecture.md         → 了解系统架构
3. docs/tech-specs/coding-standards.md     → 了解编码标准索引（按需读取拆分子文件）
4. docs/tech-specs/testing-strategy.md     → 了解测试策略
5. VERSION                                 → 了解当前版本
6. TODO_NEXT.md                            → 了解当前进度和下一个任务
7. CHANGELOG.md                            → 了解已完成工作
8. git log --oneline -20                   → 了解最近 20 次提交
9. docs/dev-plans/ 下当前版本的计划文档      → 了解当前任务详情
```

### 模式 B：增量读取（断线重连 / 继续开发）

```
1. docs/tech-specs/dev-governance.md 第零部分  → 刷新执行流程
2. VERSION                                     → 确认当前版本
3. TODO_NEXT.md                                → 快速定位下一个任务
4. git log --oneline -10                       → 了解最近提交
```

### 模式 C：按需读取（进入具体阶段时）

按 dev-governance.md 中各 Phase ① 规范输入的要求读取对应章节。

### 上下文摘要（所有模式读取完成后必须输出）

```
== 上下文摘要 ==
读取模式: {A 完整 / B 增量 / C 按需}
当前版本: v{X.Y.Z}
最近完成: {上次 commit 的任务概要}
当前计划: {当前开发计划文件名}
下一个待完成任务: v{X.Y.Z} — {任务名称}
上次审计结果: {通过/有问题需处理}
==============
```

---

## 自动化开发循环（"继续开发"指令）

当用户说"继续开发"、"继续"、"下一个任务"或类似指令时，进入自动化开发循环。

> 完整的 7 阶段（Phase 1-7）详细操作规范请参见 `docs/tech-specs/dev-governance.md`。

```
┌─────────────────────────────────────────────┐
│                 自动化开发循环                  │
│                                             │
│  Step 1: 读取（模式 B 增量读取 + 模式 C 按需） │
│       ↓                                      │
│  Step 2: 自动领取下一个待完成任务（v{X.Y.Z}） │
│       ↓                                      │
│  Step 3: 输出实施计划                         │
│       ↓                                      │
│  Step 4: 门禁通过 → 自动进入执行               │
│       ↓                                      │
│  Step 5: 增量执行（编码）                     │
│       ↓                                      │
│  Step 6: 测试                                │
│       ↓                                      │
│  Step 7: 审计                                │
│       ↓                                      │
│  Step 8: 测试报告                             │
│       ↓                                      │
│  Step 9: 收尾（CHANGELOG + VERSION + commit） │
│       ↓                                      │
│  Step 10: 衍生建议                            │
│       ↓                                      │
│  Step 11: 判断是否继续                        │
│       • 还有任务 → 回到 Step 2               │
│       • 遇到停止条件 → 停止并报告              │
└─────────────────────────────────────────────┘
```

---

## 停止条件

1. **测试失败且无法自修复** — 报告失败原因和需要的帮助
2. **需要人类决策** — 架构选择、需求澄清、优先级判断
3. **所有任务已完成** — 报告完成状态和建议的下一步
4. **发现严重风险** — 可能破坏已有功能、数据安全、架构级问题
5. **连续两个任务审计有"高风险"项** — 需要人类 review
6. **需要新增外部依赖** — 报告依赖名称、用途、许可证

---

## 开发报告格式

每个 `vX.Y.Z` 任务完成后，按以下 9 项结构报告：

1. 计划 / 当前迭代目标（目标 + 最小闭环 + 排除范围）
2. 文件变更清单（路径 | 新增/修改/删除 | 职责描述）
3. 用户可见能力（用户现在可以做什么）
4. 真实场景验证（至少 5 个场景）
5. 开放问题（高/中/低优先级）
6. 收尾说明（是否闭环 + 残留风险）
7. 版本状态更新（VERSION / CHANGELOG / TODO_NEXT.md）
8. commit 信息
9. 是否继续下一个任务

---

## 项目上下文

### 项目基本信息
- **项目名称**: KB Platform（知识库平台）
- **一句话定位**: 将多模态原始资料自动整理为可追溯、可维护、可被 AI 使用的结构化知识系统
- **技术栈**: Python 3.12 (FastAPI) + Next.js 15 (React 19, TypeScript) + PostgreSQL + Redis + MinIO + Celery
- **架构**: 微服务（4 个后端服务 + 4 个共享包 + 1 个前端 SPA）

### 服务清单
- `services/api/` — FastAPI 主服务（认证、CRUD、搜索、导出等）
- `services/ingestion-worker/` — 解析工作器（text/pdf/ocr/asr）
- `services/pipeline-worker/` — 9 阶段流水线工作器
- `services/ai-orchestrator/` — LLM 编排服务
- `packages/shared-config/` — 共享配置
- `packages/shared-models/` — SQLAlchemy 模型
- `packages/shared-schemas/` — Pydantic 请求/响应模型
- `packages/shared-errors/` — 统一错误码
- `apps/web/` — Next.js 15 前端 SPA

### 关键路径
- PRD 文档: `docs/prd/01-产品PRD.md` ~ `docs/prd/17-开发起步Checklist.md`
- 开发计划: `docs/plans/v0.36-v0.40-版本开发任务计划.md`
- 安全审计: `docs/security/`
