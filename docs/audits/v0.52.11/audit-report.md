# 版本审计报告 v0.52.11

## 审计概要
- **版本号**: v0.52.11
- **分支**: test-v-0-52-a
- **审计日期**: 2026-04-04
- **审计 Stage 数量**: 3（规格合规 + 质量工程 + 完整性与UX）
- **整体健康度**: **A**

## 发现统计

| 级别 | 数量 | 多维度发现 | 已修复 | 延后 |
|------|------|-----------|--------|------|
| Critical | 1 | 0 | 1 | 0 |
| Important | 7 | 0 | 4 | 3 |
| Minor | 8 | 1 | 8 | 0 |
| Observation | 0 | 0 | 0 | 0 |
| **合计** | **16** | **1** | **13** | **3** |

> 3 项 Important 延后（I-001/I-002/I-003）均为 dev-plan 明确划分至 v0.53 的 UI 页面，不影响本版本健康度评分。
> 评分依据: 0 Critical（已全部修复）, 0 Important（本版本范围内已全部修复）, ≤3 Minor → **A**

---

## Critical 发现（必须修复）

### C-001: 428 确认流 前端未处理
- **发现来源**: Stage 3（完整性与UX）
- **文件**: `apps/web/src/lib/api.ts`, `apps/web/src/components/phrase-confirm-dialog.tsx`, `apps/web/src/app/(dashboard)/projects/[id]/settings/page.tsx`, `apps/web/src/lib/error-messages.ts`
- **证据引用**: 见 Stage 3 [C-001]
- **描述**: 后端 v0.52.9 实现 HTTP 428 确认码流程（项目删除 + 架构发布），但前端 api.ts 未识别 428 状态码，无对话框组件，删除按钮不支持确认重试。后前联动断裂。
- **修复建议**: 在 api.ts request() 中检测 428、创建确认对话框组件、在 settings 页面 handleDelete 中捕获并重试
- **验证方式**: 删除项目时触发 428 → 弹出输入框 → 输入确认码 → 成功删除
- **状态**: **已修复** (commit `11961ac`)

---

## Important 发现（建议本版本修复）

### I-001: skills.py 租户隔离缺失
- **发现来源**: Stage 1（规格合规）
- **文件**: `services/api/app/routers/skills.py`
- **证据引用**: 见 Stage 1 [I-001]
- **描述**: Skills CRUD 四个端点未校验 `Project.kb_id == kb_id`，攻击者可跨租户操作 skill
- **状态**: **已修复** (commit `2a7aac4`)

### I-002: agent.py 同步 Redis 阻塞事件循环
- **发现来源**: Stage 2（质量工程）
- **文件**: `services/api/app/routers/agent.py`
- **证据引用**: 见 Stage 2 [I-001]
- **描述**: rate limiter 在 async handler 中使用同步 `get_redis_client()`
- **状态**: **已修复** (commit `a5a9f4d`)

### I-003: review_notify.py Redis 连接泄漏
- **发现来源**: Stage 2（质量工程）
- **文件**: `services/pipeline-worker/worker/stages/review_notify.py`
- **证据引用**: 见 Stage 2 [I-002]
- **描述**: Redis 连接未显式关闭
- **状态**: **已修复** (commit `a5a9f4d`)

### I-004: 死代码 `import redis`（两处）
- **发现来源**: Stage 2（质量工程）
- **文件**: `services/pipeline-worker/worker/tasks.py`, `services/pipeline-worker/worker/stages/review_notify.py`
- **证据引用**: 见 Stage 2 [I-003]
- **描述**: 顶部 `import redis` 无用
- **状态**: **已修复** (commit `a5a9f4d`)

### I-005: StatusBadge 缺少 assigned/approved 样式
- **发现来源**: Stage 3（完整性与UX）
- **文件**: `apps/web/src/components/status-badge.tsx`, `apps/web/src/lib/label-maps.ts`
- **证据引用**: 见 Stage 3 [I-004]
- **描述**: Review Kanban 使用的新状态无对应 badge 样式
- **状态**: **已修复** (commit `11961ac`)

### I-006: Skills CRUD 无前端 UI 页面（延后）
- **发现来源**: Stage 3（完整性与UX）
- **证据引用**: 见 Stage 3 [I-001]
- **状态**: **延后至 v0.53**（dev-plan 明确划分）

### I-007: Ontology 提取无触发 UI（延后）
- **发现来源**: Stage 3（完整性与UX）
- **证据引用**: 见 Stage 3 [I-002]
- **状态**: **延后至 v0.53**

### I-008: Asset 下载无前端入口（延后）
- **发现来源**: Stage 3（完整性与UX）
- **证据引用**: 见 Stage 3 [I-003]
- **状态**: **延后至 v0.53**

---

## Minor 发现（可延后）

### M-001: video_parser.py IR 字段不完整
- **发现来源**: Stage 1（规格合规）
- **证据引用**: 见 Stage 1 [M-001]
- **状态**: **已修复** (commit `2a7aac4`)

### M-002: skills.py Gap 编号注释错误
- **发现来源**: Stage 1（规格合规）
- **证据引用**: 见 Stage 1 [M-002]
- **状态**: **已修复** (commit `2a7aac4`)

### M-003: Content-Disposition 不符合 RFC 5987
- **发现来源**: Stage 2（质量工程）
- **证据引用**: 见 Stage 2 [M-001]
- **状态**: **已修复** (commit `a5a9f4d`)

### M-004: 手动 JSONResponse(403) 绕过统一错误处理
- **发现来源**: Stage 2（质量工程）
- **证据引用**: 见 Stage 2 [M-002]
- **状态**: **已修复** (commit `a5a9f4d`)

### M-005: test_confirmation.py 测试不完整
- **发现来源**: Stage 2（质量工程）
- **证据引用**: 见 Stage 2 [M-003]
- **状态**: **已修复** (commit `a5a9f4d`)

### M-006: 租户隔离检查代码重复 7 处
- **发现来源**: Stage 2（质量工程）
- **证据引用**: 见 Stage 2 [M-004]
- **描述**: 同时也是 Stage 1 I-001 修复的衍生优化（多维度发现）
- **状态**: **已修复** (commit `a5a9f4d`)

### M-007: RejectModal 缺少 ARIA 属性
- **发现来源**: Stage 3（完整性与UX）
- **证据引用**: 见 Stage 3 [M-001]
- **状态**: **已修复** (commit `11961ac`)

### M-008: error-messages.ts 缺少确认错误码映射
- **发现来源**: Stage 3（完整性与UX）
- **证据引用**: 见 Stage 3 [M-002]
- **状态**: **已修复** (commit `11961ac`)

---

## 趋势分析

- **相比 v0.42**:
  - 已修复: v0.42 的 2 Critical 已不再出现（均已在 v0.42 审计后修复）
  - 新增: 16 项（本版本新功能引入，v0.52 新增 11 个子版本，新代码量大）
  - 持续存在: 0 项
  - 恶化: 0 项
- **趋势**: 新增发现数量虽多（16 项），但全部在审计中修复或按计划延后，无跨版本遗留问题。健康度从 B → A，**↑ 改善**。

---

## 下版本关注点

1. **前端 UI 覆盖缺口**: v0.53 需补全 Skills CRUD UI、Ontology 触发 UI、Asset 下载入口（3 项延后的 Important）
2. **428 确认流扩展**: 当前仅 project delete 前端闭环，架构 publish/rollback 的前端确认流需在对应 UI 页面实现时补齐
3. **租户隔离回归**: 后续新增任何接受 `project_id` 的端点必须使用 `ensure_project_access()` 而非内联查询
4. **Redis 连接管理**: async handler 统一使用 `get_async_redis_client()` + `aclose()`，sync worker 使用 `get_redis_client()` + `close()`

---

## 各维度审计详情
> 详见同目录下各 Stage 原始报告：
> - [Stage 1: 规格合规](stage1-spec-review.md)
> - [Stage 2: 质量工程](stage2-quality-review.md)
> - [Stage 3: 完整性与UX](stage3-completeness-review.md)
