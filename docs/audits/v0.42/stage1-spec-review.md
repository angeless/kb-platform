# Stage 1 审计报告：规格合规 — v0.42

**审计日期**：2026-03-25
**审计范围**：107 个变更文件，12 个开发计划任务 (T-42-01 ~ T-42-12)
**基线 commit**：372f1c7
**HEAD commit**：8449e07

## 发现统计

| 级别 | 数量 |
|------|------|
| Critical | 1 |
| Important | 4 |
| Minor | 5 |
| Observation | 4 |

## 发现详情

### C-001: health.py 中 logger 未定义 — 运行时 NameError [已修复]
- **级别**：Critical
- **检测项**：#6 占位符残留
- **文件**：services/api/app/routers/health.py:54
- **证据**：readyz 端点调用 logger.warning 但未 import logging
- **修复状态**：已修复 — 添加 import logging + logger 定义

### I-001: Tier 1 保护文件 dev-governance.md 被修改
- **级别**：Important
- **检测项**：#8 文件保护合规
- **文件**：docs/tech-specs/dev-governance.md
- **证据**：新增 4 行 part6/part7 导航条目，来自 dev-workflow upgrade commits

### I-002: VERSION 与计划最终版本不一致
- **级别**：Important
- **检测项**：#1 计划覆盖度
- **文件**：VERSION (0.42.10，计划要求 0.42.12)

### I-003: TODO_NEXT.md 严重过期
- **级别**：Important
- **检测项**：#1 计划覆盖度
- **文件**：TODO_NEXT.md (显示 T-42-05~T-42-12 为 Planned，实际全部完成)

### I-004: 跨库引用 API 路径与计划定义不一致
- **级别**：Important
- **检测项**：#3 接口合约偏移
- **文件**：services/api/app/routers/cross_refs.py
- **证据**：计划 GET /v1/docs/:id/cross-refs 实际 GET /v1/cross-refs/doc/{doc_id}

### M-001: 多库路由使用原始 dict 无 Pydantic schema
- **级别**：Minor
- **文件**：services/api/app/routers/projects.py:156

### M-002: Wiki 编辑路由设计中定义但未实现（存疑）
- **级别**：Minor
- **文件**：路由设计表

### M-003: docs/TODO_NEXT.md 计划外文件
- **级别**：Minor
- **文件**：docs/TODO_NEXT.md（与根目录重复）

### M-004: CLAUDE.md 被修改不在任务范围内
- **级别**：Minor
- **文件**：CLAUDE.md

### M-005: 4 个 dev-workflow 升级 commit 引入计划外治理文件变更
- **级别**：Minor
- **文件**：多个 docs/tech-specs/ 文件（520 行变更）

### O-001: assets.py 保留 v0.41 TODO 注释
- **级别**：Observation

### O-002: embed.py placeholder embedding 实现
- **级别**：Observation

### O-003: settings.py MinIO 默认值保留开发环境
- **级别**：Observation

### O-004: /_version 端点无认证保护
- **级别**：Observation

## 审计结论
- **Stage 1 通过/未通过**：**通过**（C-001 已修复）
- **未覆盖的计划任务**：无
- **计划外变更**：4 个 dev-workflow 升级 commit + CLAUDE.md + docs/TODO_NEXT.md
