# 变更日志

所有重要变更都将被记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [未发布]

### 新增 (Added)
- 自动化开发工作流（dev-workflow-upgrade v1.3）

## [0.42.2] - 2026-03-22

### 安全修复
- SSRF 防护增强：新增 DNS 解析检查，阻止 DNS rebinding 攻击 (H-01/T-42-02)
- CSRF 中间件：变更请求必须携带 X-Requested-With 头 (H-02/T-42-02)
- MinIO 凭证参数化：移除所有硬编码 minioadmin (H-07/T-42-02)
- Redis 密码保护：启用 requirepass + settings.py redis_password (H-09/T-42-02)

### 新增
- url_validator.py：独立 URL 验证器（含 DNS 解析 SSRF 检查）
- csrf.py：CSRF 中间件
- test_url_validator.py：SSRF 防护测试

## [0.42.1] - 2026-03-22

### 安全修复
- reset_token 仅在 development 环境返回，production 不再泄露明文 (C-04)
- QA decrypt 调用修复 (H-06)

### 修复
- forgot-password 页面语法错误 (C-01)
- 注册后跳转到 /login 并显示成功提示 (C-02)
- Dashboard 认证守卫竞态：添加 isCheckingAuth 状态 (C-03)

## [0.41.8] - 2026-03-22

### 安全修复
- docker-compose 移除所有硬编码默认密码，改为 `${VAR:?msg}` 强制注入 (T-41-08)

### 新增
- web.Dockerfile 前端生产构建容器（Node.js 20, 非 root 运行）(T-41-08)
- docker-compose 新增 web 前端服务定义
- .env.example 标注必填变量

## [0.41.7] - 2026-03-22

### 安全修复
- CORS allow_headers 从 `["*"]` 收紧为 `["Content-Type", "Authorization", "X-Request-ID"]` (T-41-07)

### 修改
- API 版本号从 VERSION 文件动态读取（不再硬编码）(T-41-07)

## [0.41.6] - 2026-03-22

### 新增
- 移动端汉堡菜单导航 mobile-nav.tsx (T-41-06)
- 状态徽章 aria-label 支持
- confirm-dialog aria 属性 (role=dialog, aria-modal)

### 修改
- dashboard layout 移动端响应式（侧边栏可折叠、主内容区全宽）
- 搜索页面移动端适配（按钮自适应）

## [0.41.5] - 2026-03-22

### 新增
- 全局 404 页面（中文友好提示 + 返回首页按钮）(T-41-05)
- 骨架屏加载组件 skeleton-card.tsx（替代"加载中..."纯文本）
- 错误恢复组件 error-retry.tsx（带重试按钮）
- 确认弹窗组件 confirm-dialog.tsx（退出登录等场景）
- 会话过期守卫 session-guard.tsx（过期后弹窗提示而非硬跳转）
- Toast 容器注入到 dashboard layout

### 修改
- dashboard layout 使用骨架屏替代纯文本加载
- api.ts 401 过期改为 dispatch session-expired 事件

## [0.41.4] - 2026-03-22

### 安全修复
- 搜索结果高亮改用安全 mark 解析器，消除 `dangerouslySetInnerHTML` XSS 风险 (T-41-04)

### 修改
- 新增 `label-maps.ts`：统一管理所有技术值→中文标签映射 (T-41-04)
- `status-badge.tsx` 改用 label-maps 映射（解析中→处理中，已解析→处理完成，失败→处理失败）
- 注册页面"组织名称"→"团队名称"
- 搜索结果"匹配字段"→"匹配位置"
- 新增 `highlight.ts`：安全 mark 标签解析器

## [0.41.3] - 2026-03-22

### 新增
- 混合搜索 API `POST /v1/search/hybrid`：关键词 + 语义双路检索，去重合并排序 (T-41-03)
- AI 问答 API `POST /v1/qa/ask`：RAG 模式（检索→LLM→答案+衍生问题）(T-41-03)
- 前端搜索页面三模式：智能搜索 / 关键词搜索 / AI 问答
- 搜索结果匹配类型标签（关键词/语义/双重匹配）
- 文档类型中文显示映射
- 衍生问题一键点击作为新搜索

## [0.41.2] - 2026-03-22

### 新增
- 前后端统一错误码系统：34 个错误码 + 中文消息映射 (T-41-02)
- 前端 `error-messages.ts` 错误码 → 中文消息映射表
- 前端 `error-toast.tsx` 通用错误 Toast 组件
- 后端 422 验证错误统一格式化处理

### 修改
- api.ts 错误拦截层改用 `getUserMessage()` 获取中文提示
- 网络断开时显示友好中文提示
- 500 错误统一显示"系统开了个小差，请稍后重试"

## [0.41.1] - 2026-03-22

### 安全修复
- WebSocket 租户隔离：连接前校验 project_id 归属，跨租户访问返回 4003 (T-41-01/S-01)
- Refresh Token 数据库记录：登录写入 hash、refresh 时校验 DB、logout 时吊销 (T-41-01/S-02)
- 修改密码时批量吊销所有 refresh token

### 新增
- `refresh_token` 数据库表（user_id, token_hash, expires_at, revoked）
- Alembic 迁移：`f5a6b7c8d9e0_add_refresh_token_table`

## [0.40.3] - 2026-03-22

### 修改
- 搜索结果高亮：后端使用 PostgreSQL ts_headline 生成带 mark 标记的摘要 (T-40-03)
- 前端搜索页面渲染高亮 snippet，匹配关键词黄色背景显示

## [0.40.2] - 2026-03-21

### 修改
- 文件上传组件：新增实时进度条显示（XHR `upload.onprogress`）(T-40-02)
- 支持取消上传（AbortController + xhr.abort）
- api.ts 新增 `uploadWithProgress()` 方法

## [0.40.1] - 2026-03-21

### 新增
- 忘记密码流程：`POST /v1/auth/forgot-password` + `POST /v1/auth/reset-password` (T-40-01)
- User 模型新增 `reset_token` 和 `reset_token_expires_at` 字段
- 前端忘记密码页面和重置密码页面
- 登录页面添加"忘记密码？"链接
- Alembic 迁移：`e4f5a6b7c8d9_add_password_reset_fields`
- 技术规范四件套（architecture.md, dev-governance.md, coding-standards.md, testing-strategy.md）
- UI 设计规范（交互式 HTML，12 个章节，双主题）
- CI 整合检查脚本 scripts/ci_verify.sh
- 冒烟测试 test_smoke.py
- VERSION 文件

### 修改 (Changed)
- CLAUDE.md 升级为双模式（产品模式 + 开发模式）
- 文档目录重组：PRD → docs/prd/，安全 → docs/security/，报告 → docs/reports/

## [0.39.6] - 2026-03-20

### 修改
- RateLimit 中间件：Redis 不可用时降级为本地内存固定窗口限流（50% 保守阈值）(T-39-06)
- 新增 OOM 防护（10K key 上限 + 60s 清理）和日志防风暴（60s 去重）

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
