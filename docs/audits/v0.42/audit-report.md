# 版本审计报告 v0.42

## 审计概要
- **版本号**：v0.42
- **分支**：claude/gracious-poincare (基于 main)
- **审计日期**：2026-03-25
- **审计 Stage 数量**：3（规格合规 + 质量工程 + 完整性与UX）
- **整体健康度**：B

## 发现统计

| 级别 | Stage 1 | Stage 2 | Stage 3 | 合并去重后 | 多维度发现 |
|------|---------|---------|---------|-----------|-----------|
| Critical | 1 | 0 | 1 | 2 | 0 |
| Important | 4 | 6 | 4 | 13 | 1 |
| Minor | 5 | 8 | 5 | 16 | 2 |
| Observation | 4 | 5 | 3 | 12 | 0 |
| **合计** | **14** | **19** | **13** | **43** | **3** |

> 2 个 Critical 均已在审计过程中修复。合并后实际 0 Critical 未解决。

## Critical 发现（已全部修复）

### C-001: health.py 中 logger 未定义导致 /readyz 异常路径崩溃
- **发现来源**：Stage 1
- **文件**：services/api/app/routers/health.py:54
- **证据引用**：见 Stage 1 [C-001]
- **描述**：readyz 端点在 Alembic 版本检查失败时调用 logger.warning，但 logger 未定义，抛出 NameError
- **修复状态**：已修复 -- 添加 import logging + logger 定义
- **验证方式**：确认 health.py 顶部有 import logging 和 logger 定义

### C-002: Wiki 3 处搜索使用 GET 调用 POST-only hybrid search 接口
- **发现来源**：Stage 3
- **文件**：wiki-sidebar.tsx:206, wiki/search/page.tsx:31, wiki/[docId]/page.tsx:99
- **证据引用**：见 Stage 3 [C-001]
- **描述**：后端 /v1/search/hybrid 只注册 POST，Wiki 组件用 GET + query string 调用，返回 405
- **修复状态**：已修复 -- 3 处改为 api.post + request body
- **验证方式**：搜索 api.get.*hybrid 应返回 0 结果

## Important 发现（建议本版本修复）

### I-001: cross_ref_service.list_for_doc N+1 查询
- **发现来源**：Stage 2 [I-001]
- **文件**：services/api/app/services/cross_ref_service.py:59-63
- **描述**：循环内逐条查 doc/project，20 条引用产生 40-60 次查询
- **修复建议**：批量 select...where(id.in_(all_ids))

### I-002: cross_ref_service.auto_suggest 全量 embedding 内存加载
- **发现来源**：Stage 2 [I-002]
- **文件**：services/api/app/services/cross_ref_service.py:130-141
- **描述**：加载租户全部 embedding 到内存，无上限。大规模数据有 OOM 风险
- **修复建议**：使用 pgvector 数据库端检索或至少 .limit(500)

### I-003: _cosine_similarity 函数在 3 个文件重复定义
- **发现来源**：Stage 2 [I-003]
- **文件**：cross_ref_service.py:287, project_router_service.py:111, embedding_service.py:183
- **修复建议**：提取至 shared utils

### I-004: email_service HTML 注入风险
- **发现来源**：Stage 2 [I-004]
- **文件**：services/api/app/services/email_service.py:49-52
- **描述**：username 直接拼入 HTML 模板未做 html.escape()
- **修复建议**：对用户输入使用 html.escape()

### I-005: qa_service 解密失败静默吞异常
- **发现来源**：Stage 2 [I-005]
- **文件**：services/api/app/services/qa_service.py:163-171
- **描述**：except Exception: pass，密文被当作 API key 发送
- **修复建议**：添加 logger.warning + 提取为共享方法

### I-006: projects.route_content 使用裸 dict（多维度发现）
- **发现来源**：Stage 1 [M-001] + Stage 2 [I-006]
- **文件**：services/api/app/routers/projects.py:155-171
- **修复建议**：创建 RouteContentRequest schema

### I-007: Tier 1 保护文件被修改
- **发现来源**：Stage 1 [I-001]
- **文件**：docs/tech-specs/dev-governance.md
- **修复建议**：确认人类授权

### I-008: VERSION 文件未更新至 0.42.12
- **发现来源**：Stage 1 [I-002]
- **文件**：VERSION
- **修复建议**：更新为 0.42.12

### I-009: TODO_NEXT.md 严重过期
- **发现来源**：Stage 1 [I-003]
- **文件**：TODO_NEXT.md
- **修复建议**：覆写反映全部完成

### I-010: 跨库引用 API 路径与计划不一致
- **发现来源**：Stage 1 [I-004]
- **文件**：services/api/app/routers/cross_refs.py
- **修复建议**：在计划中添加变更记录

### I-011: TOC 滚动追踪绑定 window 而非实际滚动容器
- **发现来源**：Stage 3 [I-001]
- **文件**：apps/web/src/components/wiki-toc.tsx:73
- **修复建议**：WikiToc 接收滚动容器 ref

### I-012: 搜索结果链接跳出项目上下文（多维度发现）
- **发现来源**：Stage 2 [M-008] + Stage 3 [I-002, I-003]
- **文件**：search/page.tsx:261,304,339; review/page.tsx:286
- **修复建议**：统一为 /projects/${projectId}/wiki/${docId}

### I-013: forgot-password 前端缺少环境守卫
- **发现来源**：Stage 3 [I-004]
- **文件**：apps/web/src/app/forgot-password/page.tsx:34,54-66
- **修复建议**：添加 process.env.NODE_ENV === "development" 条件

## Minor 发现（可延后）

16 条 Minor 发现详见各 Stage 原始报告。多维度合并：
- Stage 2 [M-006] + Stage 3 [M-004]：file-upload 闭包陷阱
- Stage 2 [M-008] 已提升为 Important I-012

## Observation（仅记录）

12 条 Observation 详见各 Stage 原始报告。

## 趋势分析

本次为 v0.42 基线审计，无历史对比。

## 下版本关注点

1. **cross_ref_service 性能瓶颈**：auto_suggest 全量内存加载和 N+1 查询应在 v0.43 前优化
2. **前端路由一致性**：搜索/审核页文档链接路径需统一
3. **dev-workflow 升级管理**：升级 commit 不应混入版本开发流
4. **文档状态同步**：VERSION 和 TODO_NEXT.md 需纳入自动化收尾流程

## 健康度评分说明

评定 **B**：2 个 Critical 已修复（实际 0 未解决），13 Important 中 3 条为文档管理问题。核心代码无阻断风险。

## 各维度审计详情
> - [Stage 1: 规格合规](stage1-spec-review.md)
> - [Stage 2: 质量工程](stage2-quality-review.md)
> - [Stage 3: 完整性与UX](stage3-completeness-review.md)
