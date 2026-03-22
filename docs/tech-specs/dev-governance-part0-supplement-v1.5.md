# 第零部分补充：v1.5 新增规则

> **本文件是 dev-governance-part0-automation.md 的 v1.5 增量补充。**
> 包含 §0.1.5（全局任务连续性原则）和 Phase 8（版本交叉审计）引用。
> 当 part0 主文件更新后，本文件内容应合入主文件并删除。

---

## §0.1.5 全局任务连续性原则

> **⚠️ 本原则优先级最高，适用于所有任务执行场景。**

1. **分支操作自动执行**：所有分支上的操作（`git add`、`git commit`、`git push origin {branch}`）无需等待用户确认，直接执行。
2. **任务间禁止询问**：任务与任务之间、Phase 与 Phase 之间、功能项与功能项之间，**禁止输出"是否继续"、"继续？"、"继续执行？"等询问**。门禁通过后直接进入下一步。
3. **仅 main 合并需用户确认**：只有当需要合并到 `main` 分支（PR/merge）时，才停止并等待用户评审。
4. **封板流程为原子操作**：Phase 8 → 空闲循环 → 封板检查 → 版本收尾，全流程连续执行，禁止在步骤之间插入确认。
5. **门禁失败自动修复**：门禁失败后自动修复并立即重跑，不询问用户"是否重跑"。累计 10 次失败才停止。
6. **Hook 响应不中断任务流**：如果系统 hook 触发并需要回应，回应完毕后**必须立即继续当前任务**，不得停下等待用户。
7. **上下文窗口达到 50% 时主动交接**：当上下文使用量达到约 50%，**必须在当前任务完成后立即执行交接**。正确做法：① 完成当前任务的 Phase 6 收尾；② 执行 §5.3 Agent 结束工作标准流程；③ 输出交接摘要；④ 告知用户"上下文已达 50%，建议新开会话继续"。**禁止在任务中途停止。**

---

## Phase 8 引用

版本内所有任务的 Phase 1-7 循环完成后，进入 **Phase 8：版本交叉审计**。

详见：
- [dev-governance-part6-audit.md](dev-governance-part6-audit.md) — 审计流程总览（§6.1-§6.2）
- [dev-governance-part6-audit-prompts.md](dev-governance-part6-audit-prompts.md) — 子 Agent 审计标准（§6.3）
- [dev-governance-part6-audit-integrator.md](dev-governance-part6-audit-integrator.md) — 整合 Agent 规范（§6.4-§6.5）
