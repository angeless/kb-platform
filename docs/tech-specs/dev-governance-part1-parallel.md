# 第一部分：并行开发协议（§1.9）

> **导航**: [← 返回索引](dev-governance-index.md) | [← 文件保护](dev-governance-part1-protection.md) | [版本发布 →](dev-governance-part1-release.md)
>
> 本文件是 `dev-governance-template.md` 拆分后的第一部分（§1.9）。
>
> **TL;DR（上下文受限时仅读此块）**:
> 多 Agent 并行时的防冲突协议。核心硬规则：① 每个 Agent 一个 `test-v-x-y-a` 分支，禁止共享；② 修改文件前必须在 `.locks/` 下创建锁文件（含 agent_id 和 30 分钟超时）；③ 版本号由产品负责人预分配，禁止多 Agent 争抢同一 vX.Y.Z；④ Phase 6 收尾后释放所有锁文件。单人项目可跳过本节。

---

## 1.9 并行开发协议

> 当多个 AI Agent 同时在同一项目上工作时，必须遵守以下协议以避免冲突和数据损坏。

### 1.9.1 Git 分支策略

**原则：每个 Agent 一个 `test-v-x-y-a` 分支，禁止共享工作分支。分支体系遵循 §1.5 五层分支模型。**

| 分支类型 | 命名规则 | 用途 | 生命周期 |
|---------|---------|------|---------|
| Agent 开发测试分支 | `test-v-{X}-{Y}-{agent-id}`，如 `test-v-0-39-agent1` | 单个 Agent 执行任务的工作分支，实际写代码、跑测试的地方 | 从 `test-v-x-y` 创建 → 代码合入后保留归档 |
| 合并专用分支 | `build-merge/v-{X}-{Y}` | 将各 Agent 的开发分支逐个合入 `test-v-x-y`，管理合并风险 | 按版本临时创建 → 合并完成后删除 |
| 版本测试分支 | `test-v-{X}-{Y}` | 汇集所有 Agent 的 commit，进行集成测试 | 版本开始时创建 → 版本发布后保留归档 |

> 完整的五层分支模型（含 `test-final`、`main`）详见 §1.5。

**分支规则：**
1. 每个 Agent 在领取任务时（Phase 1）从 `test-v-{X}-{Y}` 创建自己的 `test-v-{X}-{Y}-{agent-id}` 分支
2. Agent 只能在自己的 `test-v-x-y-a` 分支上 commit，禁止直接推送到 `test-v-x-y`、`test-final`、`main` 或其他 Agent 的分支
3. 任务完成后，由合并操作者通过 `build-merge/v-{X}-{Y}` 将 Agent 分支逐个合入 `test-v-{X}-{Y}` 进行集成验证
4. 集成验证通过后，按 §1.5.3 的版本发布流程合入 `test-final` → `main`
5. 合并冲突必须在 `build-merge/v-x-y` 上解决，不得在 Agent 工作分支上强制覆盖

### 1.9.2 版本号预分配

**原则：在任务分配时预先分配版本号，避免多个 Agent 争抢同一版本号。**

**分配规则：**
1. 产品负责人在开发计划中为每个任务预分配唯一的 `vX.Y.Z` 版本号
2. Agent 领取任务时，该任务的 `vX.Y.Z` 即为其独占版本号
3. 同一时刻不允许两个 Agent 持有同一个 `vX.Y.Z`
4. VERSION 文件仅在合并到 `main` 时更新，Agent 的 `test-v-x-y-a` 分支上的 VERSION 保持领取时的值
5. 如果任务需要拆分，由产品负责人重新分配子版本号（如 `v0.39.3` → `v0.39.3.1`, `v0.39.3.2`）

**预分配表（在开发计划中维护）：**

```markdown
| vX.Y.Z | 任务名称 | 分配给 Agent | 分配时间 | 状态 |
|--------|---------|-------------|---------|------|
| v0.39.1 | 任务1 | agent1（分支: `test-v-0-39-agent1`） | 日期 | In Progress |
| v0.39.2 | 任务2 | agent2（分支: `test-v-0-39-agent2`） | 日期 | In Progress |
| v0.39.3 | 任务3 | — | — | Planned |
```

### 1.9.3 文件级互斥锁机制

**原则：通过声明式锁文件防止多个 Agent 同时修改同一文件。**

**锁文件位置：** `.locks/` 目录

**锁文件命名：** 将文件路径中的 `/` 替换为 `__`，后缀 `.lock`
- 例：`services/api/routes.py` → `.locks/services__api__routes.py.lock`

**锁文件内容：**

```json
{
  "file": "services/api/routes.py",
  "agent": "agent1",
  "agent_id": "agent1-session-20260320",
  "task": "v0.39.1",
  "branch": "test-v-0-39-agent1",
  "acquired": "2026-03-20T10:00:00Z",
  "timeout_minutes": 30,
  "reason": "添加知识库管理 API 路由"
}
```

**字段说明：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `file` | ✅ | 被锁文件的相对路径 |
| `agent` | ✅ | Agent 标识名称 |
| `agent_id` | ✅ | Agent 唯一 ID（建议格式：`{agent名}-session-{YYYYMMDD}` 或系统分配 ID），用于精确识别持锁者 |
| `task` | ✅ | 当前任务版本号 |
| `branch` | ✅ | 当前工作分支 |
| `acquired` | ✅ | 锁获取时间（ISO 8601 格式） |
| `timeout_minutes` | ✅ | 锁超时时间（分钟），默认 30 分钟。超时后其他 Agent 可强制获取锁 |
| `reason` | ✅ | 获取锁的原因 |

**锁超时与强制获取机制：**

1. **超时判定**：当 `当前时间 - acquired > timeout_minutes` 时，该锁视为超时
2. **超时后处理流程**：
   - 其他 Agent 检测到锁超时后，**不立即强制获取**
   - 先尝试与持锁 Agent 通信确认（如检查持锁 Agent 的分支是否有近期 commit）
   - 如果持锁 Agent 仍然活跃（近 `timeout_minutes` 内有 commit） → 视为 Agent 仍在工作，锁自动续期（更新 `acquired` 为最新 commit 时间）
   - 如果持锁 Agent 无活动迹象 → 可强制获取锁
3. **强制获取操作**：
   ```bash
   # 1. 备份原锁文件
   mv .locks/{原锁文件}.lock .locks/{原锁文件}.lock.expired
   # 2. 创建新锁文件（包含抢占记录）
   ```
   新锁文件中增加字段：
   ```json
   {
     "file": "services/api/routes.py",
     "agent": "agent2",
     "agent_id": "agent2-session-20260320",
     "task": "v0.39.2",
     "branch": "test-v-0-39-agent2",
     "acquired": "2026-03-20T11:00:00Z",
     "timeout_minutes": 30,
     "reason": "修改路由配置以支持报表端点",
     "force_acquired": true,
     "previous_holder": {
       "agent_id": "agent1-session-20260320",
       "original_acquired": "2026-03-20T10:00:00Z",
       "expired_at": "2026-03-20T10:30:00Z"
     }
   }
   ```
4. **强制获取后风险提示**：强制获取锁后，Agent 必须在 Phase 1 的实施计划中标注"该文件曾被其他 Agent 持锁，存在潜在合并冲突风险"

**互斥规则：**
1. Agent 在 Phase 1 输出预计修改文件清单后，必须为每个文件创建锁文件
2. 创建锁文件前必须检查该文件是否已被其他 Agent 锁定
3. 如果文件已锁定：
   - 若锁未超时且持锁 Agent 的任务与当前任务无依赖关系 → 等待或跳过该文件
   - 若锁未超时且持锁 Agent 的任务是当前任务的前置依赖 → 停止并报告依赖阻塞
   - 若锁已超时（超过 `timeout_minutes`，默认 30 分钟） → 按上述强制获取流程处理
4. Agent 在 Phase 6 收尾 commit 后释放所有锁文件（删除 `.locks/` 下自己的锁）
5. `.locks/` 目录应加入 `.gitignore`，锁文件仅在本地工作目录生效
6. 每次 Phase 2 开始编码前，Agent 应刷新自己持有锁的 `acquired` 时间，防止长任务意外超时

**冲突检测（Phase 4 增强）：**
- Phase 4 Part D 增加检查项：`git diff --name-only` 的结果是否包含未持锁的文件？如果包含，标记为 ❌ 违规

### 1.9.4 并行开发的 Phase 约束

| Phase | 并行约束 |
|-------|---------|
| Phase 1 | Agent 领取任务后立即声明锁文件；如有锁冲突，优先与协调者沟通调整任务分配 |
| Phase 2 | 只修改已持锁的文件；如发现需要修改未持锁的文件，先获取锁再修改 |
| Phase 3-5 | 测试和审计在自己的分支上独立进行，不影响其他 Agent |
| Phase 6 | 释放锁文件；通过 `build-merge/v-x-y` 合入 `test-v-x-y` 时需检查是否有合并冲突 |
| Phase 7 | 如果衍生建议涉及其他 Agent 持锁的文件，仅记录建议，不执行 |

---
