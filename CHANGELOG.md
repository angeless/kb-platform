# 变更日志

所有重要变更都将被记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [未发布]

### 新增 (Added)
- 自动化开发工作流（dev-workflow-upgrade v1.3）
- 技术规范四件套（architecture.md, dev-governance.md, coding-standards.md, testing-strategy.md）
- UI 设计规范（交互式 HTML，12 个章节，双主题）
- CI 整合检查脚本 scripts/ci_verify.sh
- 冒烟测试 test_smoke.py
- VERSION 文件

### 修改 (Changed)
- CLAUDE.md 升级为双模式（产品模式 + 开发模式）
- 文档目录重组：PRD → docs/prd/，安全 → docs/security/，报告 → docs/reports/

## [0.39.5] - 2026-03-20

### 新增
- 4 个服务的 requirements.lock 文件（精确锁定所有第三方依赖版本）(T-39-05)
- requirements.in 约束文件（记录依赖来源，支持 `uv pip compile` 重新生成）

### 修改
- 4 个 Dockerfile 改用 `--no-deps -r requirements.lock` 安装依赖，确保构建可重现 (T-39-05)

## [0.39.0] - 2026-03-20

### 新增
- .dockerignore 文件（减少构建上下文，保护敏感文件）(T-39-03)
- Celery 死信队列 DLQ 实现 (T-39-04)

### 修复
- build.yml Dockerfile 路径修复 (T-39-01)
- Docker 容器非 root 用户运行 (T-39-02)

## [0.35.1] - 2026-03-19

### 新增
- 完整的知识库管理后端 API（15 个路由模块）
- 文档生命周期管理（创建/编辑/审核/发布/版本管理）
- 架构树管理（fork/compare/rollback/节点分配）
- 全文搜索 + 语义搜索（tsvector + pgvector 双模式）
- Celery 异步任务系统（解析/流水线/AI 编排）
- JWT 认证 + RBAC 权限控制
- 多租户隔离
- MinIO 文件存储
- Prometheus 指标监控
- 前端 SPA（Next.js 15 + React 19）

---
