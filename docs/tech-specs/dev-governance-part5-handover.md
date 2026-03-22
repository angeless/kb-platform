# 第五部分：多 Agent 接力协议（§5.1–§5.5）

> **导航**: [← 返回索引](dev-governance.md) | [← 第四部分：文件管理](dev-governance-part4-files.md) | [附录 →](dev-governance-appendix.md)
>
> 本文件是 `dev-governance.md` 拆分后的第五部分。
>
> **TL;DR（上下文受限时仅读此块）**:
> 多 Agent 接力的信息传递必须通过文件，禁止依赖对话历史。核心硬规则：① 新 Agent 接手必须依次读取 VERSION → CHANGELOG → git log → 开发计划 → 已完成任务 → 输出状态总结；② Agent 结束时必须确保 git clean + 更新 CHANGELOG + 更新开发计划 + 生成交接总结文件；③ 禁止假设前一个 Agent 已做过检查；④ 禁止跳过标准 Phase 1-7 流程；⑤ 高风险任务建议由不同 session 的 Agent 独立执行 Phase 4 审计（§5.5）。

---

# 第五部分：多 Agent 接力协议

> 本部分定义在多个开发者或 AI Agent 接力完成项目时的协作规范。

## 5.1 工作交接的信息来源

**禁止：** 通过对话内容、chat 历史传递信息

**必须：** 通过本地文件（git 仓库中的文件）交接信息

**规则：**
- 每个 Agent 开始工作前，必须从文件读取当前状态
- 每个 Agent 结束工作后，必须将所有重要信息写入文件
- 任何决策都必须有文档记录

## 5.2 Agent 开始工作的标准流程

当一个新 Agent 接手 KB Platform 项目时，必须依次执行：

**Step 1:** 读取 VERSION
**Step 2:** 阅读 CHANGELOG.md
**Step 3:** 查看 git log
**Step 4:** 读取开发计划
**Step 5:** 检查已完成的 `vX.Y.Z` 任务
**Step 6:** 输出当前状态总结

```markdown
# Agent 交接状态报告

**日期：** {{日期}}
**接手 Agent：** {{AI Agent}}

## 当前状态

- 版本：v{{x.y.z}}
- 最新 commit：{{commit hash}}
- 上一个完成的任务：v{{X.Y.Z}}
- 当前未完成的任务：v{{X.Y.Z+1}}

## 下一步

1. 读取 v{{X.Y.Z+1}} 的完整定义
2. 生成实施计划
3. 执行 Phase 2-7
```

## 5.3 Agent 结束工作的标准流程

当一个 Agent 完成一个 `vX.Y.Z` 任务后，必须：

1. **确保所有文件都已 commit**
   ```bash
   git status  # 结果应该是 clean
   ```

2. **更新 CHANGELOG.md**

3. **更新开发计划文档**

4. **生成交接总结**

   创建文件 `docs/dev-plans/{{日期}}-agent-handoff-summary.md`

## 5.4 禁止的跨 Agent 假设

- 禁止：假设前一个 Agent 已做过某个检查
- 禁止：依赖对话中的口头约定
- 禁止：跳过标准的 Phase 1-7 流程
- 禁止：自作主张改变任务定义

## 5.5 跨 Session 审计协作（高风险任务）

> 本节定义何时以及如何利用不同 session 的 Agent 提升审计可信度。

**背景**：当 Phase 2（编码实现）和 Phase 4（审计）由同一个 AI session 完成时，审计存在固有的确认偏误——AI 倾向于认为自己刚写的代码是正确的。Phase 4 ③ Part B 的"自审可信度标注"机制会将此类审计标注为"自审"。对于高风险任务，建议通过跨 session 审计消除这一偏误。

**适用场景**：
- 开发计划中标注 `risk: high` 的任务
- 涉及安全（认证、授权、加密）、支付、数据迁移、核心数据结构变更的任务
- 用户明确要求"独立审计"的任务

**跨 Session 审计流程**：

1. **编码 Agent**（Session A）完成 Phase 1-3 后，在 Phase 4 ② 生成审计报告时，额外创建一份审计请求文件：
   ```
   docs/dev-plans/audit-request-v{{X.Y.Z}}.md
   ```
   内容包含：任务编号、涉及文件清单、关键设计决策、已知风险点、需要重点审计的规范条目

2. **审计 Agent**（Session B）接手后：
   - 按 §5.2 标准流程读取项目状态
   - 读取 `audit-request-v{{X.Y.Z}}.md`
   - **独立执行 Phase 4 ③ Part B/C/D 门禁**（不读取 Session A 的审计报告，避免锚定效应）
   - 将审计结论写入 `docs/versions/audit-report-v{{X.Y.Z}}-independent.md`
   - 在任务汇报中标注 `审计模式: 独立审计（跨 session）`

3. **编码 Agent**（Session A 或新 Session C）根据独立审计结果继续 Phase 5-7

**非强制性**：跨 Session 审计是建议而非强制。如果团队资源有限或任务风险可控，可由用户决定跳过。跳过时在任务汇报中标注 `外部复核: 已跳过（用户确认）`。

---
