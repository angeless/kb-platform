# Stage 3: 完整性与体验审计 — v0.52.11

## 审计概要
- **版本**: v0.52.11
- **审计日期**: 2026-04-04
- **审计范围**: v0.52.1 ~ v0.52.11 前端 + 后前联动完整性
- **审计人**: Claude Code (Phase 8 Stage 3)

## 检查项与结果

### 1. 428 确认流 前端闭环
- **[C-001] 428 CONFIRMATION_REQUIRED 前端未处理** — Critical
  - 文件: `apps/web/src/lib/api.ts`, `apps/web/src/components/phrase-confirm-dialog.tsx` (新增), `apps/web/src/app/(dashboard)/projects/[id]/settings/page.tsx`, `apps/web/src/lib/error-messages.ts`
  - 描述: 后端 v0.52.9 实现了 428 确认码流程，但前端 `api.ts` 未识别 428 状态码，无确认对话框组件，设置页删除按钮不支持确认重试
  - 修复:
    - `api.ts`: 新增 `ApiConfirmationError` 类，request() 中 428 检测，`del()` 支持 query params
    - `phrase-confirm-dialog.tsx`: 新增确认对话框组件（输入短语 + ESC 关闭 + a11y）
    - `settings/page.tsx`: `handleDelete` 捕获 `ApiConfirmationError` 弹出对话框，确认后带 `confirmation_id` + `phrase` 重试
    - `error-messages.ts`: 添加 `CONFIRMATION_REQUIRED` / `CONFIRMATION_INVALID` 映射
  - 状态: **已修复** (commit `11961ac`)

### 2. 新增功能 UI 覆盖
- **[I-001] Skills CRUD 无专属 UI 页面** — Important（延后）
  - 描述: v0.52.8 后端新增 skills CRUD 端点，但前端无对应管理页面
  - 判定: dev-plan 中明确标注 Skills UI 为 v0.53 范围，本版本仅后端端点，不阻断
  - 状态: **延后至 v0.53**

- **[I-002] Ontology 提取无触发 UI** — Important（延后）
  - 描述: v0.52.7 后端新增 ontology extract Celery task，但前端无触发按钮
  - 判定: dev-plan 中 ontology UI 为 v0.53 范围
  - 状态: **延后至 v0.53**

- **[I-003] Asset 下载无前端触发入口** — Important（延后）
  - 描述: 后端 download endpoint 已存在且已改为 StreamingResponse，但前端文件列表无下载按钮
  - 判定: 前端资产管理 UI 改进为 v0.53 范围
  - 状态: **延后至 v0.53**

### 3. 状态标签完整性
- **[I-004] StatusBadge 缺少 `assigned`/`approved` 样式** — Important
  - 文件: `apps/web/src/components/status-badge.tsx`, `apps/web/src/lib/label-maps.ts`
  - 描述: Review Kanban (v0.52.11) 使用 `assigned`/`approved` 状态，但 StatusBadge 无对应样式映射
  - 修复: 添加 `assigned: "bg-blue-50 text-blue-600"` / `approved: "bg-green-50 text-green-700"` + label 映射
  - 状态: **已修复** (commit `11961ac`)

### 4. 无障碍（a11y）
- **[M-001] RejectModal 缺少 ARIA 属性** — Minor
  - 文件: `apps/web/src/components/reject-modal.tsx`
  - 描述: 模态框缺少 `role="dialog"`、`aria-modal="true"`、`aria-labelledby`
  - 修复: 添加 ARIA 属性
  - 状态: **已修复** (commit `11961ac`)

### 5. 错误提示覆盖
- **[M-002] error-messages.ts 缺少确认相关错误码** — Minor
  - 文件: `apps/web/src/lib/error-messages.ts`
  - 描述: `CONFIRMATION_REQUIRED` / `CONFIRMATION_INVALID` 无中文映射
  - 修复: 添加映射
  - 状态: **已修复** (commit `11961ac`)（与 C-001 合并修复）

## 统计

| 级别 | 发现数 | 已修复 | 延后 |
|------|--------|--------|------|
| Critical | 1 | 1 | 0 |
| Important | 4 | 1 | 3 |
| Minor | 2 | 2 | 0 |
| **合计** | **7** | **4** | **3** |

## 结论
Critical 和本版本范围内 Important 均已修复。3 项 Important 按 dev-plan 延后至 v0.53（UI 页面补全）。通过。
