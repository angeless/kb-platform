# 第一部分：分支策略与 Git Tag（§1.5–§1.6, §1.5A）

> **导航**: [← 返回索引](dev-governance-index.md) | [← 版本管理](dev-governance-part1-version.md) | [文件保护 →](dev-governance-part1-protection.md)
>
> 本文件是 `dev-governance-template.md` 拆分后的第一部分（§1.5–§1.6, §1.5A）。
>
> **阅读条件**：Phase 1 ① 规范输入时必读。
> - §1.5：所有项目必读（五层分支体系）
> - §1.5A：仅 S 型项目需读（三层分支简化体系）
> - §1.6：涉及版本发布打 tag 时需读
>
> **TL;DR（上下文受限时仅读此块）**:
> 五层分支：main → test-final → test-v-x-y → build-merge/v-x-y → test-v-x-y-a。核心硬规则：① 开发代码只能提交到自己的 `test-v-x-y-a` 分支，禁止直接提交到上层分支；② 进入 Phase 1 前必须确认在正确分支上，否则立即停止；③ 合并前必须产出合并就绪报告；④ S 型小项目可用三层简化体系 main → test → dev-{a}（§1.5A）。

---

## 1.5 分支策略（五层分支体系）

> 本项目采用五层分支模型，覆盖从开发测试到线上发布的完整生命周期。
> 所有开发者（人工和 AI Agent）必须严格在指定分支上操作，禁止跨层直接提交。

### 1.5.1 分支总览

```
main                          ← 线上正式版本（受白名单开关保护）
  └── test-final              ← 灰度发布版本（从 test-v-x-y 合入，灰度验证通过后合入 main）
        └── test-v-x-y        ← 发布前测试版本（已合入各支线的所有 commit）
              └── build-merge/v-x-y  ← 合并专用分支（每次只合入一个 test-v-x-y-a 的 commit）
                    └── test-v-x-y-a ← 开发测试分支（a = 开发者/Agent 标识）
```

### 1.5.2 各分支职责与规则

| 分支 | 命名规则 | 职责 | 谁可以写入 | 生命周期 | 合入目标 |
|------|---------|------|-----------|---------|---------|
| **main** | `main` | 线上正式版本。需要用白名单开关控制用户可以访问的版本号 | 仅从 `test-final` 合入，禁止直接提交 | 永久 | — |
| **test-final** | `test-final` | 灰度发布版本。在正式上线前进行灰度验证 | 仅从 `test-v-x-y` 合入，禁止直接提交 | 永久 | `main` |
| **test-v-x-y** | `test-v-{X}-{Y}`，如 `test-v-0-39` | 发布前测试版本。汇集当前版本所有开发分支的 commit，进行集成测试 | 仅从 `build-merge/v-x-y` 合入，禁止直接提交 | 版本开始时从 `test-final` 创建 → 版本发布后保留归档 | `test-final` |
| **build-merge/v-x-y** | `build-merge/v-{X}-{Y}`，如 `build-merge/v-0-39` | 合并专用分支。不负责开发，仅负责将开发分支的代码逐个合入 `test-v-x-y`。**每次只合入一个 `test-v-x-y-a` 分支的 commit**，管理合并风险 | 合并操作者（人工或指定 Agent） | 按版本临时创建，从 `test-v-x-y` 拉出 → 版本发布后删除 | `test-v-x-y` |
| **test-v-x-y-a** | `test-v-{X}-{Y}-{a}`，如 `test-v-0-39-alice`、`test-v-0-39-agent1` | 开发测试分支。`v-x-y` 填前两位版本号，`a` 填开发者名称或 Agent 标识。这是实际写代码、跑测试的分支 | 对应的开发者或 Agent（一人一分支，禁止共享） | 从 `test-v-x-y` 创建 → 代码合入 `test-v-x-y` 后保留归档 | `build-merge/v-x-y` |

### 1.5.3 分支操作流程

**版本开发启动时：**

```bash
# 1. 从 test-final 创建版本测试分支（如果不存在）
git checkout test-final
git pull origin test-final
git checkout -b test-v-{X}-{Y}
git push -u origin test-v-{X}-{Y}

# 2. 从 test-v-x-y 创建开发测试分支（每个开发者/Agent 各自创建）
git checkout test-v-{X}-{Y}
git checkout -b test-v-{X}-{Y}-{a}
git push -u origin test-v-{X}-{Y}-{a}
```

**开发完成后合入流程：**

> **合并前必须产出合并报告**。合并不是简单的 git 操作，而是一个需要分析、验证和记录的治理环节。

**步骤 A：合并前报告（merge-readiness report）**

在执行任何 git merge 操作之前，必须产出以下报告并向用户/合并操作者展示：

```markdown
### 合并就绪报告（Merge Readiness Report）

**1. 合并来源与目标**
- 来源分支: test-v-{X}-{Y}-{a}
- 目标分支: test-v-{X}-{Y}（经 build-merge）
- 来源分支最后 commit: {hash} - {message}

**2. 变更摘要**
- 涉及的文件数: N
- 新增/修改/删除: A/M/D
- 涉及的模块: {模块列表}

**3. 影响分析**
- 是否修改了公共接口: 是/否
- 是否修改了数据库 schema: 是/否
- 是否修改了配置文件: 是/否
- 可能影响的其他模块: {列表}

**4. 测试状态**
- 来源分支测试结果: ✅ 全部通过 / ❌ 有失败
- Phase 3-4 门禁结论: ✅ / ❌

**5. 冲突预检**
- 执行 `git merge --no-commit --no-ff` 干运行
- 预期冲突文件: {列表，或"无冲突"}

**6. 回滚策略**
- 合并失败时: `git merge --abort`
- 合并后发现问题: `git revert -m 1 {merge-commit-hash}`
```

**步骤 B：执行合并**

```bash
# 3. 创建 build-merge 分支（从 test-v-x-y 拉出）
git checkout test-v-{X}-{Y}
git pull origin test-v-{X}-{Y}
git checkout -b build-merge/v-{X}-{Y}

# 4. 每次只合入一个开发分支的 commit（管理风险）
git merge test-v-{X}-{Y}-{a} --no-ff
# 解决冲突（如有）→ 运行测试 → 确认通过

# 5. 合入 test-v-x-y
git checkout test-v-{X}-{Y}
git merge build-merge/v-{X}-{Y} --no-ff

# 6. 清理 build-merge 分支
git branch -d build-merge/v-{X}-{Y}
git push origin --delete build-merge/v-{X}-{Y}

# 7. 重复步骤 A-B 的 3-6，合入下一个开发分支
```

**步骤 C：合并后验证**

合入完成后，在 `test-v-{X}-{Y}` 上必须：
1. 运行完整测试套件（`ci_verify.sh` 或等效命令），确认无回归
2. 如有多个开发分支合入，确认它们之间的交互功能正常
3. 记录合并结果到版本文档中

**版本发布流程：**

```bash
# 8. 集成测试全部通过后，合入 test-final
git checkout test-final
git merge test-v-{X}-{Y} --no-ff

# 9. 灰度验证通过后，合入 main
git checkout main
git merge test-final --no-ff
git tag -a v{X}.{Y}.0 -m "Release v{X}.{Y}.0: 简要描述"
git push origin main --tags
```

### 1.5.4 硬性规则

1. **禁止跨层提交**：开发代码只能提交到 `test-v-x-y-a`，禁止直接提交到 `test-v-x-y`、`test-final`、`main`
2. **禁止在 main 上开发**：`main` 仅接受从 `test-final` 的合并
3. **一人一分支**：即使单人开发，也必须创建 `test-v-x-y-a` 分支（`a` 为开发者名称或 Agent 标识），不得直接在 `test-v-x-y` 上开发
4. **build-merge 逐个合入**：`build-merge/v-x-y` 每次只合入一个 `test-v-x-y-a` 的 commit，合入后必须运行测试确认通过，再合入下一个。禁止一次性合入多个开发分支
5. **build-merge 按版本临时创建**：每个版本创建 `build-merge/v-{X}-{Y}`，合并完成后删除。下个版本重新从新的 `test-v-x-y` 拉出
6. **分支不删除，仅归档**：`test-v-x-y` 和 `test-v-x-y-a` 在版本发布后保留不删除，作为历史追溯依据
7. **开发前必须确认分支**：进入 Phase 1 前，必须确认当前所在分支是否为自己的 `test-v-x-y-a` 分支，如果不是则**立即停止开发**（详见 §0.2 Phase 1 ①）
8. **禁止在开发线程内执行合并**：正在执行七阶段开发流程（Phase 1-7）的 Agent/开发者，不得在其开发分支 `test-v-x-y-a` 上执行向 `test-v-x-y` 或更上层分支的合并操作。合并必须由专门的合并操作者在 `build-merge` 分支上执行
9. **合并前必须产出报告**：任何合并操作（步骤 3-6 和步骤 8-9）之前，必须先产出合并就绪报告并经操作者/用户确认

### 1.5.5 白名单版本控制（main 分支）

`main` 分支上的每个版本 tag 对应一个可访问的产品版本。通过白名单开关控制用户可以访问的版本号：
- 新版本合入 `main` 后，默认不开放给所有用户
- 通过配置白名单（如功能开关、灰度百分比、用户分群）逐步放量
- 白名单开关的实现方式由项目自行定义（环境变量、配置中心、Feature Flag 服务等）

## 1.6 Git Tag 规则

**命名规范：** `vX.Y.Z`

示例：`v0.39.0`、`v1.0.0-beta1`

**创建时机：** 当一个完整版本的所有 `vX.Y.Z` 任务都完成、审计通过、测试通过时

**创建命令：**
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z: 简要描述改动"
git push origin vX.Y.Z
```

**Push 失败错误处理：**

如果 `git push origin vX.Y.Z` 失败，按以下流程处理：

| 错误类型 | 处理方式 |
|---------|---------|
| 权限被拒绝（403 / authentication failed） | ① 本地 tag 保留不删除 ② 在任务汇报和 CHANGELOG 中标注"⚠️ tag 已创建但未推送" ③ 提示用户：检查 SSH key / token 是否有 push 权限，修复后手动执行 `git push origin vX.Y.Z` |
| 远程仓库不可达（网络错误） | ① 本地 tag 保留不删除 ② 在任务汇报中标注"⚠️ tag 未推送（网络问题）" ③ 待网络恢复后手动执行 `git push origin vX.Y.Z` |
| tag 已存在于远程 | ① 不覆盖远程 tag（禁止 `--force`） ② 检查远程 tag 指向的 commit 是否一致 ③ 一致则跳过；不一致则报告冲突，等待用户决策 |

> tag push 失败**不阻塞 Phase 6 收尾流程的其他步骤**（CHANGELOG、VERSION、开发计划更新等可继续执行），但必须在任务汇报中明确标注未推送状态。

**保留期：** 永久保留

## 1.5A S 型项目简化分支体系（三层分支）

> 本节适用于满足以下**全部条件**的项目：
> 1. 项目规模为 S 型（参见 SKILL.md 中的项目规模判定标准）
> 2. 项目尚未对外发布（无线上用户、无公开版本）
> 3. 没有多 Agent / 多开发者并行开发的需求
>
> 如果上述任一条件不满足，必须使用 §1.5 的五层分支体系。

### 1.5A.1 三层分支总览

```
main                          ← 主干版本（受保护，禁止直接提交）
  └── test                    ← 测试/集成分支（从 main 创建）
        └── dev-{a}           ← 开发分支（a = 开发者/Agent 标识）
```

### 1.5A.2 各分支职责与规则

| 分支 | 命名规则 | 职责 | 谁可以写入 | 生命周期 | 合入目标 |
|------|---------|------|-----------|---------|---------|
| **main** | `main` | 主干稳定版本 | 仅从 `test` 合入，禁止直接提交 | 永久 | — |
| **test** | `test` | 测试与集成分支 | 仅从 `dev-{a}` 合入，禁止直接提交 | 永久 | `main` |
| **dev-{a}** | `dev-{a}`，如 `dev-alice`、`dev-agent1` | 实际开发分支 | 对应的开发者或 Agent | 长期保留 | `test` |

### 1.5A.3 操作流程

**初始化：**
```bash
# 1. 确保 main 分支存在
git checkout main

# 2. 创建 test 分支
git checkout -b test
git push -u origin test

# 3. 创建开发分支
git checkout test
git checkout -b dev-{a}
git push -u origin dev-{a}
```

**日常开发合入：**
```bash
# 开发完成后，合入 test
git checkout test
git pull origin test
git merge dev-{a} --no-ff
# 运行测试 → 确认通过

# 测试通过后，合入 main
git checkout main
git pull origin main
git merge test --no-ff
git tag -a v{X}.{Y}.{Z} -m "Release v{X}.{Y}.{Z}: {简要描述}"
git push origin main --tags
```

### 1.5A.4 硬性规则

1. **禁止在 main 上直接开发**：`main` 仅接受从 `test` 的合并
2. **禁止在 test 上直接开发**：`test` 仅接受从 `dev-{a}` 的合并
3. **合并前仍需产出合并报告**：简化版即可，但必须包含变更摘要和测试状态
4. **升级条件**：当项目满足以下任一条件时，必须升级到 §1.5 五层分支体系：
   - 项目对外发布（有线上用户）
   - 引入多 Agent / 多开发者并行开发
   - 项目规模从 S 型增长到 M/L 型

### 1.5A.5 检测与自动适配

在升级流程（SKILL.md 阶段 2）生成 `CLAUDE.md` 时，应根据以下逻辑判断使用哪套分支体系：

```
IF 项目规模 == S
   AND 无线上发布记录（无 Release tag、无部署配置、无生产环境配置）
   AND 无多开发者/多 Agent 并行需求（仅一个开发分支或无分支）
THEN → 采用 §1.5A 三层分支体系
ELSE → 采用 §1.5 五层分支体系
```

判断依据（供参考）：
- 检查是否存在 Release tag（`git tag -l 'v*'`）
- 检查是否存在部署配置文件（`Dockerfile`、`docker-compose.yml`、CI/CD 配置等）
- 检查是否存在多个活跃开发分支
- 项目规模参照 SKILL.md 中的 S/M/L 判定标准
