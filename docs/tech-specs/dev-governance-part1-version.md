# 第一部分：开发版本管理（版本号·VERSION·CHANGELOG·Commit）

> **导航**: [← 返回索引](dev-governance-index.md) | [← 第零部分](dev-governance-part0-automation.md) | [分支策略 →](dev-governance-part1-branch.md)
>
> 本文件是 `dev-governance-template.md` 拆分后的第一部分（§1.1–§1.4）。
>
> **TL;DR（上下文受限时仅读此块）**:
> 版本号格式 vX.Y.Z（MAJOR.MINOR.PATCH），每完成一个任务 PATCH +1。核心硬规则：① VERSION 文件、CHANGELOG、Git Tag、commit message、开发计划中的版本号必须完全一致；② commit message 格式 `type(vX.Y.Z): subject`；③ VERSION 更新必须与 CHANGELOG 更新在同一个 commit 中完成。

---

# 第一部分：开发版本管理

> 本部分定义版本号、文件管理、分支策略等版本管理规范。

## 1.1 语义化版本规则

版本号格式：**vX.Y.Z**（MAJOR.MINOR.PATCH）

**任务不再使用 R1/R2/R3 等字母+数字编号，统一用 `vX.Y.Z` 标识每个任务。**

- **X（MAJOR）— 大版本**：包含多个功能/优化项，代表一次重大产品迭代。架构变更、不兼容的 API 变更、产品形态重大调整均属此列
- **Y（MINOR）— 功能/优化项**：一个具体的功能模块或优化项，可能由多个任务组成。向后兼容的能力增强
- **Z（PATCH）— 单任务级**：一个最小可实现可验证的功能/优化，是开发执行的原子单位

层级关系：
```
v1.0.0（大版本）
├── v1.1.0（功能：告警管理）
│   ├── v1.1.1（任务：告警规则 CRUD API）
│   ├── v1.1.2（任务：告警通知集成）
│   └── v1.1.3（任务：告警仪表盘页面）
├── v1.2.0（功能：报表分析）
│   ├── v1.2.1（任务：报表数据聚合 API）
│   └── v1.2.2（任务：报表可视化页面）
└── v1.3.0（优化：性能调优）
    └── v1.3.1（任务：查询缓存优化）
```

规则：
- 每个版本一经 tag 就不再修改
- MAJOR 或 MINOR 变更时，PATCH 重置为 0
- 同一工作线程内只能开发一个目标版本
- 每完成一个 `vX.Y.Z` 任务，PATCH 必须 +1 并同步更新 VERSION 文件

## 1.1.1 版本号跨文件一致性（强制）

以下所有位置的版本号**必须完全一致**，任何一处不一致即为质量门禁失败：

| 位置 | 文件/载体 | 格式要求 |
|---|---|---|
| VERSION 文件 | `/VERSION` | 单行纯文本，无 `v` 前缀（如 `0.39.0`） |
| CHANGELOG | `/CHANGELOG.md` | 最新条目版本号与 VERSION 一致 |
| Git Tag | `git tag` | `v` + VERSION 内容（如 `v0.39.0`） |
| Git Commit | commit message | `feat(v0.39.0): 功能描述` 格式 |
| 版本 PRD | `docs/prd-vX.md` | 精确到第一位 |
| 版本开发计划 | `docs/dev-plans/dev-plan-vX.Y.md` | 精确到前两位 |
| 任务实施计划 | `docs/dev-plans/impl-plan-vX.Y.Z.md` | 精确到三位 |
| 任务汇报 | `docs/versions/task-report-vX.Y.Z.md` | 精确到三位 |
| 审计报告 | `docs/versions/audit-report-vX.Y.Z.md` | 精确到三位 |
| 测试报告 | `docs/versions/test-report-vX.Y.Z.md` | 精确到三位 |
| 空闲循环测试报告 | `docs/versions/idle-test-report-vX.Y.Z-{a}.md` | 版本号 + 循环序号 |
| Bug 修复清单 | `docs/dev-plans/bugfix-list-vX.Y.Z-{a}.md` | 版本号 + 清单序号 |
| 阶段报告 | `docs/versions/phase-report-vX.Y.md` | 精确到前两位 |
| 版本发布说明 | `docs/versions/RELEASE_NOTES_vX.md` | 精确到第一位 |
| 技术规范文档头 | `docs/tech-specs/*.md` | 文档版本标注与项目版本一致 |

**检查时机**：每次 VERSION 文件更新后，必须检查以上所有位置是否同步。Phase 封板前、版本发布前必须做全量版本号一致性检查。

## 1.2 VERSION 文件管理

位置：`/项目根目录/VERSION`

格式（单行纯文本，无额外字符）：
```
0.39.0
```

更新规则：
- 每完成一个 `vX.Y.Z` 任务，PATCH +1，立即更新 VERSION 文件
- 每完成一个功能项（`vX.Y.0` 下所有任务完成），MINOR +1，PATCH 归零，更新 VERSION 文件
- 更新方式：`echo "x.y.z" > VERSION`
- 每个 git tag 对应一个 VERSION 内容快照
- VERSION 更新必须与 CHANGELOG.md 更新在同一个 commit 中完成

## 1.3 CHANGELOG.md 格式

位置：`/项目根目录/CHANGELOG.md`

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 规范：

```markdown
# 变更日志

所有重要变更都将被记录在此文件中。

## [未发布]

### 新增 (Added)
- 新功能描述

### 修改 (Changed)
- 现有功能的改进

### 修复 (Fixed)
- Bug 修复描述

### 移除 (Removed)
- 删除的功能

### 安全 (Security)
- 安全补丁

## [x.y.z] - YYYY-MM-DD

### 新增
- 功能描述

### 修复
- 修复描述

---
```

规则：
1. 每个 `vX.Y.Z` 任务完成后立即更新 CHANGELOG.md 中的"未发布"章节
2. 新增、修改、修复、移除、安全分类各占一行或多行
3. 每条记录简洁清晰，面向最终用户理解
4. 一个版本 release 前，将"未发布"章节改为"[x.y.z] - YYYY-MM-DD"
5. 严禁倒序；最新的版本始终在顶部

## 1.4 Git Commit Message 规范

格式遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 列表：**
- `feat`：新功能（MINOR 版本升级）
- `fix`：Bug 修复（PATCH 版本升级）
- `docs`：文档更新（无版本升级）
- `style`：代码风格调整、格式化（无版本升级）
- `refactor`：代码重构、无功能变更（PATCH 或 MINOR 取决于范围）
- `perf`：性能优化（PATCH）
- `test`：测试相关改动（无版本升级）
- `chore`：构建脚本、依赖更新等（无版本升级）

**Scope 规范：**
scope 统一使用当前任务的版本号 `vX.Y.Z`，这样每个 commit 都能直接追溯到对应任务。

**示例：**
```
feat(v0.39.1): 告警规则 CRUD API

- 新增 /api/v1/alerts 端点
- 支持创建、查询、更新、删除告警规则
- 添加对应的 pytest 测试

Closes #ISSUE_NUMBER
```

**其他 commit 示例：**
```
fix(v0.39.1): 修复告警规则删除后未清理通知

docs(v0.39.0): 更新告警管理功能的技术规范

chore(v0.39.0): 更新依赖版本
```

**Commit Message 自动化验证（可选但推荐）：**

为确保 commit message 格式一致性，推荐配置 commitlint + husky git hook：

```bash
# 安装（Node.js 项目）
npm install --save-dev @commitlint/cli @commitlint/config-conventional husky

# 初始化 husky
npx husky init

# 创建 commitlint 配置文件 commitlint.config.js
cat > commitlint.config.js << 'EOF'
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // scope 必须为 vX.Y.Z 格式
    'scope-enum': [0],  // 禁用枚举，改用自定义正则
    'scope-empty': [2, 'never'],  // scope 不能为空
  },
  plugins: [
    {
      rules: {
        'scope-version-format': ({scope}) => {
          const pattern = /^v\d+\.\d+\.\d+$/;
          return [
            pattern.test(scope),
            `scope 必须为 vX.Y.Z 格式，收到: ${scope}`
          ];
        }
      }
    }
  ]
};
EOF

# 创建 commit-msg hook
echo 'npx --no -- commitlint --edit "$1"' > .husky/commit-msg
```

```bash
# Python 项目替代方案：使用 pre-commit + commitizen
pip install commitizen pre-commit

# 在 .pre-commit-config.yaml 中添加：
# - repo: https://github.com/commitizen-tools/commitizen
#   hooks:
#     - id: commitizen
#       stages: [commit-msg]
```

> 如果项目暂不适合引入 commitlint，Phase 6 ③ 门禁中的 "commit message 格式检查" 仍然会通过人工/AI 自检方式验证。commitlint 只是将这个检查前置到 git hook 层，提供即时反馈。
