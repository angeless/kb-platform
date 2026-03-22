# KB Platform v0.41 版本开发任务计划

**文档编号**: PLAN-2026-03-22
**版本**: V1.0
**日期**: 2026-03-22
**基线 commit**: 当前 main HEAD (v0.40.3)
**基线分支**: main
**依据**: 2026-03-22 全面深度审计报告 `docs/reports/v0.40-full-audit-report.md`
**作者**: 产品 Owner

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.40.3 现有代码增量修复和增强。禁止重构无关模块、禁止重写已有业务逻辑、禁止变更已有 API 契约（除非本计划明确要求）。

### 1.2 继承已有能力

以下模块/能力已存在且稳定，本计划只在其上做最小改动：

**后端服务层** (services/api/app/services/):
- AuthService: 注册/登录/刷新/忘记密码/重置密码（JWT HS256 + httpOnly cookie）
- ProjectService: 项目 CRUD（租户隔离）
- UserService: 用户邀请/管理（角色层级保护）
- AssetService: 上传/URL导入/ZIP导入（含 SSRF 防护、路径穿越检测、SHA-256 去重）
- DocService(TenantService): 文档 CRUD/审核/发布/版本/diff
- ArchitectureService(TenantService): 架构树管理/fork/compare/rollback（含循环引用检测）
- SearchService(TenantService): 全文 tsvector + ILIKE 回退 + ts_headline 高亮
- EmbeddingService(TenantService): pgvector + JSONB 双模式语义搜索
- ExportService(TenantService): 单文档 Markdown + 项目 ZIP 导出
- JobService(TenantService): 任务创建/重试/Celery 派发
- ConflictService(TenantService): 冲突列表/解决（含权限检查）
- AuditService: 审计日志记录/查询
- ModelProviderService: 模型配置 AES-256-GCM 加密存储/路由管理

**中间件** (services/api/app/middleware/):
- RateLimitMiddleware: Redis 滑动窗口限流（含本地降级 + OOM 防护）
- MetricsMiddleware: Prometheus 指标
- RequestIdMiddleware: 请求追踪 ID

**Worker 服务**:
- ingestion-worker: text/pdf/ocr/asr 解析器 + DLQ
- pipeline-worker: 9 阶段流水线
- ai-orchestrator: LLM 调用/分类/生成/架构提议

**前端** (apps/web/):
- Next.js 15 / React 19 / TypeScript / Tailwind CSS
- 认证页面（登录/注册/忘记密码/重置密码）
- 项目管理页面组
- 文档管理/编辑/审核/diff 页面
- 架构树编辑器
- 搜索页面（全文+语义+高亮）+ 上传进度条
- 系统管理页面（模型/用户/审计）

**基础设施**:
- docker-compose.yml（7 服务 + 2 卷）
- Alembic 5 个迁移脚本
- CI/CD (ci.yml + build.yml)
- Prometheus + Grafana 监控栈
- 非 root 容器 + .dockerignore + 依赖锁定 + DLQ

### 1.3 最小改动原则

每个任务只改必须改的文件。如果发现无关问题，记录到"衍生任务"但不执行。

### 1.4 任务领取规则

每次只能领取一个任务。完成后按第十一章格式汇报，确认后再领下一个。

---

## 第二章 当前阶段事实

### 2.1 项目目标（一句话）

将多模态原始资料自动整理为可追溯、可维护、可被 AI 使用的结构化知识系统。

### 2.2 当前基线

- **版本**: v0.40.3
- **分支**: main
- **前端版本**: 0.25.0 (package.json)
- **Alembic 迁移**: 5 个版本（最新: e4f5a6b7c8d9_add_password_reset_fields）
- **数据库表**: 16 张
- **v0.36-v0.40 全部完成**: 安全修复 + 数据完整性 + 前端体验 + 基础设施 + 体验打磨

### 2.3 v0.40 审计发现的待修复项

基于 2026-03-22 全面深度审计报告，排除"新手引导"后的全部问题：

**高优先级（5 项）**:
1. WebSocket 缺少项目级租户隔离（S-01, 跨租户数据泄露）
2. Refresh Token 无轮换/吊销机制（S-02, 被盗后 7 天无法失效）
3. docker-compose 含默认密码（O-01, 生产泄露风险）
4. 核心链路无 API Key 时无提示（F-01, 用户困惑）
5. 忘记密码无邮件发送（F-02, 功能不完整）

**中优先级（10 项）**:
6. 搜索结果 dangerouslySetInnerHTML（S-03, XSS 代码气味）
7. CORS allow_headers 过宽（S-05）
8. 前端 API 默认端口 8000 ≠ 后端 8080（A-02）
9. 前后端密码验证规则不一致（UX-01）
10. 全面缺少 accessibility 属性（UX-02）
11. 移动端不可用（UX-03）
12. 无 404 页面（UX-04）
13. 无会话过期提醒（UX-05）
14. 退出无确认（UX-06）
15. API 错误无重试按钮（UX-08）

**低优先级（5 项）**:
16. main.py 版本号硬编码不一致（A-01/B-03）
17. 加载状态使用纯文本（UX-07）
18. 大文件全量读入内存（B-01）
19. docker-compose 缺前端容器定义（O-03）
20. WebSocket Redis 连接未池化（B-02）

---

## 第三章 本轮目标与边界

### 3.1 版本主题

**v0.41: 智能搜索 + 错误体系 + 审计修复 + 前端用户化**

### 3.2 版本划分

| 任务范围 | 内容 |
|---------|------|
| **安全修复** | WebSocket 租户隔离、Refresh Token 安全加固（轻量方案）、CORS 收紧 |
| **核心新功能** | 智能问答搜索（关键词+向量混合搜索 + AI 问答 + 衍生答案） |
| **错误体系** | 前后端统一错误码系统，中文友好提示 |
| **前端用户化** | 去除所有技术用词，替换为用户可理解的自然语言 |
| **UX 修复** | 404 页面、错误恢复、骨架屏、会话管理、无障碍、移动端 |
| **后端优化** | 流式上传、版本号同步、WebSocket 连接池化 |
| **部署加固** | docker-compose 密码安全、前端容器、API Key 检测提示 |

### 3.3 明确不做什么（防止范围蔓延）

1. **不做**新手引导/onboarding 流程
2. **不做**完整的账户体系深度开发（未来会接中台 PaaS）
3. **不做**邮件发送集成（因账户将迁移至 PaaS，仅保留接口预留）
4. **不做**完整 refresh token 轮换（仅做数据库记录 + 登出吊销，不做完整族链管理）
5. **不做**前端 E2E 测试（Playwright）
6. **不做**多语言国际化（i18n 框架）
7. **不做**暗黑模式
8. **不做**API v2 版本变更
9. **不做**实时协作编辑
10. **不做**SSO/OAuth/LDAP 集成

### 3.4 建议但不在本版本范围内

- 对话式多轮知识问答（v0.41 只做单轮问答）
- 知识图谱可视化
- 前端 E2E 测试覆盖
- LLM 调用成本追踪面板
- 批量操作前端 UI

---

## 第四章 优先级与顺序

| 序号 | 任务编号 | 任务名称 | 优先级 | 依赖 | 理由 |
|:---:|:---:|---|:---:|:---:|---|
| 1 | T-41-01 | WebSocket 租户隔离 + Refresh Token 安全加固 | P0 | 无 | 高危安全漏洞，生产必修 |
| 2 | T-41-02 | 前后端统一错误码系统 | P0 | 无 | 后续所有任务的基础设施 |
| 3 | T-41-03 | 智能问答搜索（混合检索 + AI 问答 + 衍生答案） | P0 | T-41-02 | 核心新功能，需错误码支持 |
| 4 | T-41-04 | 前端用户化语言 + 搜索 XSS 修复 | P0 | T-41-03 | 搜索页面改动后统一处理用语 |
| 5 | T-41-05 | 前端体验修复（404 + 错误恢复 + 骨架屏 + 会话管理） | P1 | T-41-02 | 依赖错误码系统 |
| 6 | T-41-06 | 前端无障碍（a11y）+ 移动端适配 | P1 | T-41-04 | 依赖用户化语言完成后的最终 DOM |
| 7 | T-41-07 | 后端优化（流式上传 + CORS 收紧 + 版本号同步） | P1 | 无 | 技术债务清理 |
| 8 | T-41-08 | 部署加固（docker-compose 安全 + 前端容器 + API Key 检测） | P1 | 无 | 部署就绪度 |

---

## 第五章 各任务详细定义

---

### T-41-01: WebSocket 租户隔离 + Refresh Token 安全加固

**任务版本号**: v0.41.1
**所属功能项**: v0.41.0 — 安全修复
**优先级**: P0

---

#### 需求定义

**目标**: 修复 WebSocket 跨租户数据泄露漏洞；为 Refresh Token 增加数据库记录和登出吊销能力（轻量方案，不做完整轮换）。

**输入**:
- WebSocket 连接请求，包含 JWT token 和 project_id
- Refresh token 请求

**输出**:
- WebSocket 非法 project_id 连接被拒绝（4003 错误码）
- 登出后 refresh token 立即失效

---

#### 改动范围

**修改文件**:
- `services/api/app/routers/ws.py` — 增加 project_id → tenant_id 归属校验
- `services/api/app/services/auth_service.py` — refresh token 存储/校验/吊销
- `services/api/app/routers/auth.py` — logout 时吊销 refresh token

**新增数据库表**:

| 表名 | 说明 |
|------|------|
| `refresh_token` | Refresh token 记录表 |

**refresh_token 表字段定义**:

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| user_id | UUID | FK → user.id, NOT NULL | 所属用户 |
| token_hash | VARCHAR(64) | NOT NULL, UNIQUE | SHA-256 哈希（不存明文） |
| expires_at | TIMESTAMPTZ | NOT NULL | 过期时间 |
| revoked | BOOLEAN | NOT NULL, DEFAULT FALSE | 是否已吊销 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |

**索引**:
- `ix_refresh_token_hash` ON (token_hash) — 快速查找
- `ix_refresh_token_user_id` ON (user_id) — 用户维度查询

**已有表变更**: 无

**Alembic 迁移**: `f5a6b7c8d9e0_add_refresh_token_table.py`

---

#### API 定义

无新增端点。修改现有行为：

| 端点 | 方法 | 变更 |
|------|------|------|
| `/v1/auth/login` | POST | 登录时生成 refresh token 并写入 refresh_token 表 |
| `/v1/auth/refresh` | POST | 校验 refresh token 是否在数据库中存在且未吊销且未过期；通过后生成新 access token |
| `/v1/auth/logout` | POST | 将当前 refresh token 标记为 revoked=TRUE |
| `/v1/ws/jobs/{project_id}` | WebSocket | 在 accept 前校验 project_id 归属 |

---

#### 业务规则

**WebSocket 隔离**:
1. 提取 JWT 中的 tenant_id（已有逻辑）
2. 查询 Project 表：`WHERE id = project_id AND tenant_id = tenant_id`
3. 如不匹配，关闭连接：`code=4003, reason="项目不存在或无权访问"`
4. 匹配后才调用 `websocket.accept()`

**Refresh Token 存储**:
1. 登录成功后，生成 refresh_token JWT（保持现有格式）
2. 对 token 做 SHA-256 哈希，写入 refresh_token 表
3. refresh 时，计算请求中 token 的 SHA-256，查 refresh_token 表
4. 如 token_hash 不存在 或 revoked=TRUE 或 expires_at < NOW()，拒绝刷新，返回 401
5. logout 时，将 token_hash 对应的记录 revoked 设为 TRUE
6. 可选：用户修改密码时，批量吊销该用户所有 refresh_token（`UPDATE refresh_token SET revoked=TRUE WHERE user_id=?`）

**错误码**:
- `AUTH_REFRESH_TOKEN_INVALID` — token 不在数据库中或已吊销

---

#### 前端变更

无。现有 logout 流程已调用 `/v1/auth/logout`。

---

#### 不做什么

- 不做 refresh token 自动轮换（即刷新时不生成新 refresh token）
- 不做 token 族链管理（不追踪 token 血缘关系）
- 不做 token 重用检测
- 不修改 access token 逻辑
- 不做 WebSocket 运行中断开（只在连接时校验）

---

#### 验收标准

- [ ] 租户 A 的 JWT 连接租户 B 的项目 WebSocket → 返回 4003，不接受连接
- [ ] 同租户内正常 WebSocket 连接仍然可用
- [ ] 登录后 refresh_token 表中有记录
- [ ] logout 后再用旧 refresh token 调用 /refresh → 返回 401
- [ ] 正常 refresh（未 logout）仍然可用
- [ ] 修改密码后旧 refresh token 全部失效

**预估工作量**: 1.5 天

---

### T-41-02: 前后端统一错误码系统

**任务版本号**: v0.41.2
**所属功能项**: v0.41.0 — 错误体系
**优先级**: P0

---

#### 需求定义

**目标**: 搭建前后端贯通的错误码系统。后端返回结构化错误码 + 中文消息，前端统一拦截和展示，用户永远看到友好的中文提示，不看到 error_code、stack trace 或 HTTP 状态码。

**输入**:
- 后端所有 AppException 和验证错误
- 前端 API 调用失败

**输出**:
- 后端：统一格式的错误响应 `{ error_code, message, detail, meta }`
- 前端：Toast/Alert 显示友好中文消息 + 可选的重试按钮

---

#### 改动范围

**修改文件**:
- `packages/shared-errors/shared_errors/codes.py` — 完善错误码，每个码增加中文消息映射
- `packages/shared-errors/shared_errors/exceptions.py` — 确保所有异常携带中文 message
- `services/api/app/routers/auth.py` — 补充缺失的错误码使用
- `apps/web/src/lib/api.ts` — 统一错误拦截层
- `apps/web/src/lib/error-messages.ts` — 新增，前端错误码 → 中文消息映射

**新增文件**:
- `apps/web/src/lib/error-messages.ts` — 错误码到用户友好中文消息的映射表
- `apps/web/src/components/error-toast.tsx` — 通用错误 Toast 组件

---

#### 错误码体系设计

**后端错误响应格式**（已有，确认统一）:
```json
{
  "error_code": "AUTH_INVALID_CREDENTIALS",
  "message": "邮箱或密码不正确",
  "detail": {},
  "meta": { "request_id": "uuid" }
}
```

**新增/完善的错误码**:

| 错误码 | HTTP | 中文消息（面向用户） |
|--------|------|---------------------|
| `AUTH_INVALID_CREDENTIALS` | 401 | 邮箱或密码不正确 |
| `AUTH_TOKEN_EXPIRED` | 401 | 登录已过期，请重新登录 |
| `AUTH_TOKEN_INVALID` | 401 | 身份验证失败，请重新登录 |
| `AUTH_INSUFFICIENT_ROLE` | 403 | 您没有权限执行此操作 |
| `AUTH_EMAIL_ALREADY_EXISTS` | 409 | 该邮箱已被注册 |
| `AUTH_REFRESH_TOKEN_INVALID` | 401 | 登录已失效，请重新登录 |
| `AUTH_RESET_TOKEN_INVALID` | 400 | 重置链接已失效，请重新申请 |
| `PROJECT_NOT_FOUND` | 404 | 项目不存在或已被删除 |
| `PROJECT_NAME_DUPLICATE` | 409 | 项目名称已存在，请换一个 |
| `ASSET_NOT_FOUND` | 404 | 文件不存在或已被删除 |
| `ASSET_DUPLICATE_HASH` | 409 | 该文件已上传过，无需重复上传 |
| `ASSET_TYPE_NOT_ALLOWED` | 400 | 不支持该文件格式 |
| `ASSET_TOO_LARGE` | 400 | 文件大小超出限制 |
| `ARCH_NOT_FOUND` | 404 | 知识架构不存在 |
| `ARCH_NODE_NOT_FOUND` | 404 | 分类节点不存在 |
| `ARCH_ALREADY_PUBLISHED` | 409 | 该架构已发布，无法再次发布 |
| `ARCH_CYCLE_DETECTED` | 400 | 检测到循环引用，请调整节点关系 |
| `DOC_NOT_FOUND` | 404 | 文档不存在或已被删除 |
| `DOC_ALREADY_PUBLISHED` | 409 | 该文档已发布 |
| `DOC_STATUS_INVALID` | 400 | 文档当前状态不允许此操作 |
| `JOB_NOT_FOUND` | 404 | 任务不存在 |
| `JOB_ALREADY_RUNNING` | 409 | 该任务正在运行中，请等待完成 |
| `CONFLICT_NOT_FOUND` | 404 | 冲突记录不存在 |
| `CONFLICT_ALREADY_RESOLVED` | 409 | 该冲突已解决 |
| `MODEL_PROVIDER_NOT_FOUND` | 404 | 模型服务未配置 |
| `MODEL_ROUTE_NOT_FOUND` | 404 | 未找到匹配的模型路由 |
| `MODEL_PROVIDER_UNREACHABLE` | 502 | AI 服务暂时不可用，请稍后重试 |
| `USER_NOT_FOUND` | 404 | 用户不存在 |
| `SYSTEM_INTERNAL_ERROR` | 500 | 系统开了个小差，请稍后重试 |
| `SYSTEM_RATE_LIMITED` | 429 | 操作太频繁，请稍后再试 |
| `SYSTEM_SSRF_BLOCKED` | 400 | 该地址不允许访问 |
| `SEARCH_NO_RESULTS` | 200 | （新增）搜索无结果，非错误 |
| `SEARCH_QUERY_TOO_SHORT` | 400 | （新增）请输入至少 2 个字的搜索内容 |
| `QA_MODEL_NOT_CONFIGURED` | 400 | （新增）AI 问答功能需要先配置模型服务 |
| `VALIDATION_ERROR` | 422 | （新增）提交的信息有误，请检查后重试 |

**前端错误拦截层设计**:

`apps/web/src/lib/error-messages.ts`:
```typescript
// 错误码 → 用户友好中文消息 映射
export const ERROR_MESSAGES: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: "邮箱或密码不正确",
  AUTH_TOKEN_EXPIRED: "登录已过期，请重新登录",
  // ... 全部映射
};

export function getUserMessage(errorCode: string, fallback?: string): string {
  return ERROR_MESSAGES[errorCode] || fallback || "操作失败，请稍后重试";
}
```

`apps/web/src/lib/api.ts` 改造:
1. 所有 API 错误响应统一解析 `error_code` 字段
2. 通过 `getUserMessage(error_code)` 获取中文提示
3. 通过 Toast 组件显示给用户
4. 对 401 自动 refresh 逻辑不变
5. 对 500 显示通用友好提示，不暴露技术细节

---

#### 业务规则

1. 后端每个 `raise AppException(...)` 调用必须携带 `ErrorCode` 枚举值和中文 `message`
2. 后端 422 验证错误由 FastAPI 自动生成，在全局 handler 中转换为统一格式
3. 前端永远不直接显示 error_code 给用户
4. 前端错误消息优先使用后端返回的 `message` 字段，fallback 到本地映射表
5. HTTP 状态码不展示给用户

---

#### 不做什么

- 不修改现有 API 的路径或参数
- 不修改已有 AppException 子类的 class 结构
- 不引入第三方错误追踪服务（如 Sentry）
- 不做错误消息的 i18n（只做中文）

---

#### 验收标准

- [ ] 后端所有 `raise AppException` 调用都使用 `ErrorCode` 枚举
- [ ] 后端 422 验证错误返回统一格式（不暴露 Pydantic 内部 detail）
- [ ] 前端所有 API 错误都通过 Toast 显示中文消息
- [ ] 前端不出现任何英文 error_code、HTTP 状态码、stack trace
- [ ] 网络断开时显示"网络连接失败，请检查网络后重试"
- [ ] 500 错误显示"系统开了个小差，请稍后重试"

**预估工作量**: 1.5 天

---

### T-41-03: 智能问答搜索（混合检索 + AI 问答 + 衍生答案）

**任务版本号**: v0.41.3
**所属功能项**: v0.41.0 — 智能搜索
**优先级**: P0

---

#### 需求定义

**目标**: 用户在搜索框中可以同时使用关键词搜索和向量搜索（混合检索），也可以输入自然语言问题获得 AI 生成的完整答案和可能的衍生问题。搜索体验从"找文档"升级为"找答案"。

**输入**:
- 用户输入的搜索关键词或自然语言问题
- project_id（当前项目）

**输出**:
- 混合检索模式：同时返回关键词匹配结果和语义相似结果，去重排序
- 问答模式：返回 AI 生成的完整答案 + 引用来源文档 + 3-5 个衍生问题

---

#### 改动范围

**新增文件**:
- `services/api/app/services/qa_service.py` — 问答服务（RAG: 检索增强生成）
- `services/api/app/routers/qa.py` — 问答 API 路由
- `packages/shared-schemas/shared_schemas/qa.py` — 问答请求/响应 schema
- `apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx` — 重构（增加混合搜索和问答模式）

**修改文件**:
- `services/api/app/services/search_service.py` — 新增 hybrid_search 方法
- `services/api/app/routers/search.py` — 新增 hybrid 端点
- `packages/shared-schemas/shared_schemas/search.py` — 新增 HybridSearchRequest/HybridSearchHit
- `services/api/app/main.py` — 注册 qa_router
- `packages/shared-errors/shared_errors/codes.py` — 新增 QA 相关错误码

---

#### 新增数据库表

无新增表。

---

#### 已有表变更

无。

---

#### API 定义

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `POST /v1/search/hybrid` | POST | 登录用户 | 混合搜索（关键词+向量，去重合并排序） |
| `POST /v1/qa/ask` | POST | 登录用户 | AI 问答（检索→LLM→答案+衍生问题） |

**`POST /v1/search/hybrid` 入参**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | UUID | 是 | 项目 ID |
| query | string | 是 | 搜索词，最少 2 字 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20，最大 50 |

**`POST /v1/search/hybrid` 响应**:

```json
{
  "data": [
    {
      "doc_id": "uuid",
      "title": "文档标题",
      "doc_type": "topic",
      "status": "published",
      "snippet": "匹配的内容片段...",
      "score": 0.85,
      "match_type": "keyword+semantic"
    }
  ],
  "meta": { "total": 42, "page": 1, "page_size": 20 }
}
```

**`POST /v1/qa/ask` 入参**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | UUID | 是 | 项目 ID |
| question | string | 是 | 用户问题，最少 5 字 |
| top_k | int | 否 | 检索参考文档数，默认 5 |

**`POST /v1/qa/ask` 响应**:

```json
{
  "data": {
    "answer": "根据知识库中的内容，...",
    "sources": [
      {
        "doc_id": "uuid",
        "title": "文档标题",
        "snippet": "引用的原文片段",
        "relevance": 0.92
      }
    ],
    "related_questions": [
      "关于这个主题，还有哪些注意事项？",
      "这与 XX 有什么关系？",
      "如何实际操作？"
    ]
  },
  "meta": { "request_id": "uuid" }
}
```

---

#### 业务规则

**混合搜索（hybrid_search）**:
1. 同时执行全文搜索（tsvector）和语义搜索（pgvector）
2. 全文搜索结果：使用 ts_rank 评分，归一化到 0-1
3. 语义搜索结果：使用余弦相似度评分，已在 0-1
4. 合并两个结果集，按 doc_id 去重
5. 对同时出现在两个结果集中的文档，取较高分并标记 match_type 为 `keyword+semantic`
6. 仅出现在全文搜索中的标记为 `keyword`，仅出现在语义搜索中的标记为 `semantic`
7. 最终按 score 降序排列
8. 如果项目没有 embedding 数据，则 fallback 为纯关键词搜索（不报错）
9. 租户隔离：通过 _verify_project 验证

**AI 问答（qa/ask）**:
1. 校验 project_id 归属（租户隔离）
2. 先执行混合搜索，获取 top_k 个最相关文档
3. 如果搜索无结果，返回 `{ answer: "知识库中暂未找到相关内容", sources: [], related_questions: [] }`
4. 查询 ModelRoute 获取对应的 LLM 配置（task_type = "qa"）
5. 如果无可用模型配置，返回错误码 `QA_MODEL_NOT_CONFIGURED`，消息"AI 问答功能需要先配置模型服务"
6. 构建 prompt：系统提示词 + 用户问题 + 检索到的文档内容
7. 系统提示词要求 LLM：
   - 仅基于提供的知识库内容回答
   - 如果内容不足以回答，明确说明
   - 引用来源文档标题
   - 生成 3-5 个衍生问题
8. 调用 LLM，解析返回结果
9. 返回结构化答案
10. LLM 调用超时（30 秒）时返回友好错误

**Prompt 模板**:
```
你是一个知识库助手。用户会提出一个问题，你需要仅根据以下知识库内容来回答。

## 知识库内容
{检索到的文档内容，每段标注来源文档标题}

## 规则
1. 只回答知识库中有依据的内容，不要编造
2. 如果知识库内容不足以回答，请诚实说明
3. 引用来源时使用文档标题
4. 回答完毕后，生成 3-5 个用户可能感兴趣的衍生问题

## 用户问题
{question}

## 输出格式（JSON）
{
  "answer": "...",
  "cited_docs": ["文档标题1", "文档标题2"],
  "related_questions": ["问题1", "问题2", "问题3"]
}
```

**错误码**:
- `QA_MODEL_NOT_CONFIGURED` — 未配置 AI 模型
- `SEARCH_QUERY_TOO_SHORT` — 搜索词太短
- `MODEL_PROVIDER_UNREACHABLE` — AI 服务不可用

---

#### 前端变更

重构搜索页面 `apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx`:

1. 搜索模式改为三个标签页：**智能搜索** | **关键词搜索** | **AI 问答**
   - **智能搜索**（默认）：调用 `/v1/search/hybrid`，同时展示关键词和语义匹配结果
   - **关键词搜索**：调用 `/v1/search/text`，与现有行为一致
   - **AI 问答**：调用 `/v1/qa/ask`，展示 AI 答案 + 来源 + 衍生问题
2. **智能搜索**结果卡片增加匹配类型标签（关键词匹配 / 语义匹配 / 双重匹配）
3. **AI 问答**界面：
   - 上方展示 AI 生成的答案（Markdown 渲染）
   - 下方折叠面板展示"参考来源"（可点击跳转文档）
   - 底部展示"你可能还想了解"卡片组（衍生问题，可点击作为新搜索）
4. 所有模式下搜索框共用
5. 如果 AI 问答返回 `QA_MODEL_NOT_CONFIGURED`，显示提示："AI 问答功能需要管理员先配置模型服务，您可以使用智能搜索或关键词搜索查找文档"

---

#### 不做什么

- 不做多轮对话（每次独立问答）
- 不做流式输出（SSE），整体返回
- 不做问答历史记录保存
- 不修改现有 `/v1/search/text` 和 `/v1/search/semantic` 端点
- 不修改 EmbeddingService
- 不做自动 embedding 生成触发

---

#### 验收标准

- [ ] 智能搜索返回关键词和语义双重结果，去重排序
- [ ] 没有 embedding 的项目中智能搜索 fallback 为纯关键词搜索
- [ ] AI 问答返回完整答案 + 引用来源 + 衍生问题
- [ ] 衍生问题可点击，点击后作为新问题自动搜索
- [ ] 未配置模型时 AI 问答返回友好提示，不报 500
- [ ] 知识库无相关内容时 AI 回答"暂未找到相关内容"
- [ ] 前端搜索页面三个模式切换流畅
- [ ] 所有搜索结果的文档类型显示为中文（不显示 topic/glossary 等英文）
- [ ] 租户隔离生效：不能搜索到其他租户的内容

**预估工作量**: 3 天

---

### T-41-04: 前端用户化语言 + 搜索 XSS 修复

**任务版本号**: v0.41.4
**所属功能项**: v0.41.0 — 前端用户化
**优先级**: P0

---

#### 需求定义

**目标**: 去除前端所有面向用户的技术用词，全部替换为用户可理解的自然语言。同时修复搜索结果中 `dangerouslySetInnerHTML` 的 XSS 风险。

**输入**: 前端所有页面中面向用户的文本
**输出**: 所有用户可见文本均为自然语言，无技术术语

---

#### 改动范围

**修改文件**:
- `apps/web/src/components/status-badge.tsx` — 状态文案优化
- `apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx` — 去除 "embedding" 术语，修复 XSS
- `apps/web/src/app/(dashboard)/projects/[id]/docs/page.tsx` — doc_type 中文化
- `apps/web/src/app/(dashboard)/projects/[id]/docs/pending/page.tsx` — 术语替换
- `apps/web/src/app/(dashboard)/docs/[id]/page.tsx` — 术语替换
- `apps/web/src/app/(dashboard)/assets/[id]/page.tsx` — parse_status/asset_type 中文化
- `apps/web/src/app/(dashboard)/projects/[id]/page.tsx` — 术语替换
- `apps/web/src/stores/auth-store.ts` — tenant_name 相关文案
- `apps/web/src/app/(auth)/register/page.tsx` — "租户名" → "团队名称"
- `apps/web/src/lib/label-maps.ts` — **新增**：统一标签映射文件

**新增文件**:
- `apps/web/src/lib/label-maps.ts` — 所有技术值→中文标签的集中映射

---

#### 术语替换清单

**状态标签**:

| 技术值 | 当前显示 | 替换为 |
|--------|---------|--------|
| `draft` | 草稿 | 草稿 ✅ 保持 |
| `pending_review` | 待审核 | 待审核 ✅ 保持 |
| `published` | 已发布 | 已发布 ✅ 保持 |
| `rejected` | 已驳回 | 已驳回 ✅ 保持 |
| `pending` | 待处理 | 等待中 |
| `parsing` | 解析中 | 处理中 |
| `parsed` | 已解析 | 处理完成 |
| `failed` | 失败 | 处理失败 |
| `unsupported` | 暂不支持 | 暂不支持 ✅ 保持 |

**文档类型**:

| 技术值 | 替换为 |
|--------|--------|
| `category` | 分类 |
| `topic` | 主题文档 |
| `document` | 知识文档 |
| `glossary` | 术语表 |
| `conflict` | 待确认内容 |
| `index` | 目录索引 |

**资产类型**:

| 技术值 | 替换为 |
|--------|--------|
| `text` | 文本文件 |
| `pdf` | PDF 文件 |
| `image` | 图片文件 |
| `audio` | 音频文件 |
| `video` | 视频文件 |
| `archive` | 压缩包 |

**其他替换**:

| 当前文案 | 替换为 |
|---------|--------|
| "没有找到语义相关的文档，请先为文档生成 embedding" | "暂无搜索结果。如需更精准的搜索，请联系管理员启用智能搜索功能" |
| "匹配字段：标题/内容" | "匹配位置：标题/正文" |
| "解析片段" | "内容片段" |
| "未分配到架构节点" | "未归类" |
| "知识架构节点" | "所属分类" |
| "租户名称" (注册页) | "团队名称" |
| "tenant_name" (注册表单字段) | 保持字段名不变，仅改 UI 标签和占位符 |

---

#### XSS 修复

**位置**: `apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx` 第 144-147 行

**当前代码**:
```tsx
<p dangerouslySetInnerHTML={{ __html: hit.snippet }} />
```

**替换方案**: 使用安全的 `<mark>` 标签解析函数替代 `dangerouslySetInnerHTML`:

```tsx
// apps/web/src/lib/highlight.ts
export function renderHighlight(snippet: string): React.ReactNode[] {
  // 仅解析 <mark>...</mark> 标签，其余文本作为纯文本渲染
  // 防止任何其他 HTML 标签注入
}
```

1. 将 snippet 按 `<mark>` 和 `</mark>` 分割
2. 非 mark 部分作为纯文本 React 节点
3. mark 部分包裹在 `<mark className="...">` 中
4. 任何其他 HTML 标签都作为纯文本显示，不渲染

---

#### 业务规则

1. `label-maps.ts` 是唯一的标签映射来源，所有页面 import 使用
2. 如果后端返回的值不在映射表中，显示原始值（不崩溃）
3. 映射函数签名：`getLabel(type: string, value: string): string`
4. status-badge.tsx 从 label-maps.ts 读取配置

---

#### 不做什么

- 不修改后端 API 的返回值（后端仍然返回英文枚举值）
- 不做 i18n 框架
- 不修改数据库存储值
- 不修改 Pydantic schema 的字段名

---

#### 验收标准

- [ ] 前端所有页面不出现 "embedding"、"tsvector"、"pgvector"、"node_id"、"parse_status" 等技术词
- [ ] 文档类型显示为中文（主题文档、术语表等）
- [ ] 资产状态显示为中文（处理中、处理完成等）
- [ ] 注册页面显示"团队名称"而不是"租户名称"
- [ ] 搜索结果高亮使用安全渲染（不使用 dangerouslySetInnerHTML）
- [ ] 搜索结果中输入 `<script>alert(1)</script>` 不执行脚本
- [ ] 所有标签从 label-maps.ts 统一管理

**预估工作量**: 1.5 天

---

### T-41-05: 前端体验修复（404 + 错误恢复 + 骨架屏 + 会话管理）

**任务版本号**: v0.41.5
**所属功能项**: v0.41.0 — 前端 UX
**优先级**: P1

---

#### 需求定义

**目标**: 修复审计报告中的前端体验问题：404 页面、错误恢复、骨架屏加载、会话过期提醒、退出确认、密码验证规则一致性。

---

#### 改动范围

**新增文件**:
- `apps/web/src/app/not-found.tsx` — 全局 404 页面
- `apps/web/src/app/(dashboard)/projects/[id]/not-found.tsx` — 项目级 404
- `apps/web/src/components/skeleton-card.tsx` — 骨架屏组件
- `apps/web/src/components/error-retry.tsx` — 错误恢复组件（带重试按钮）
- `apps/web/src/components/session-guard.tsx` — 会话过期守卫
- `apps/web/src/components/confirm-dialog.tsx` — 确认弹窗组件

**修改文件**:
- `apps/web/src/app/(auth)/register/page.tsx` — 密码规则提示同步后端
- `apps/web/src/app/(auth)/reset-password/page.tsx` — 密码规则提示同步后端
- `apps/web/src/app/(dashboard)/layout.tsx` — 包裹 SessionGuard + 退出确认
- 所有列表页面（projects/page.tsx, docs/page.tsx, assets/page.tsx 等）— 使用骨架屏替代"加载中..."

---

#### 各子功能详细设计

**404 页面**:
- 全局 not-found.tsx：显示友好中文提示"页面不存在"+ 返回首页按钮
- 项目级 not-found.tsx：显示"项目不存在或已被删除"+ 返回项目列表按钮
- 样式：居中卡片布局，有简洁图标

**错误恢复组件**:
- 当 API 调用失败时，在错误消息下方显示"重试"按钮
- 重试按钮调用原始请求
- 支持传入自定义 retry 函数
- 接口：`<ErrorRetry message="..." onRetry={() => refetch()} />`

**骨架屏**:
- 通用骨架屏组件：支持配置行数、是否有头像、是否有标题
- 替换所有页面的"加载中..."纯文本
- 卡片列表骨架屏：3-4 个灰色矩形脉冲动画

**会话过期守卫**:
- SessionGuard 组件包裹在 dashboard layout 中
- 监听 API 401 响应（refresh 也失败时）
- 弹出 Modal："登录已过期，请重新登录"+ 确认按钮跳转登录页
- 不使用强制跳转，给用户反应时间

**退出确认**:
- 点击"退出"按钮时，弹出确认弹窗："确定要退出登录吗？"
- 确认 → 调用 logout API → 跳转登录页
- 取消 → 关闭弹窗

**密码规则同步**:
- 注册页面、重置密码页面的密码提示文本同步为后端规则："至少 8 位，包含大小写字母、数字和特殊字符"
- 前端增加实时密码强度检测（绿/黄/红三级）：
  - 红：不满足基本长度
  - 黄：满足长度但缺少某类字符
  - 绿：满足所有规则

---

#### 不做什么

- 不做全局错误边界（v0.38 已完成 Error Boundary）
- 不做离线缓存
- 不做密码强度评分算法（只做规则匹配）

---

#### 验收标准

- [ ] 访问 `/nonexistent-path` 显示 404 页面（不显示系统错误）
- [ ] 访问不存在的项目 ID 显示"项目不存在"
- [ ] API 错误下方出现"重试"按钮，点击后重新请求
- [ ] 列表加载时显示骨架屏动画（不是纯文本"加载中..."）
- [ ] Refresh token 过期后弹出"登录已过期"提示（不直接跳转）
- [ ] 退出按钮弹出确认弹窗
- [ ] 注册时输入弱密码，实时显示红色提示

**预估工作量**: 2 天

---

### T-41-06: 前端无障碍（a11y）+ 移动端适配

**任务版本号**: v0.41.6
**所属功能项**: v0.41.0 — 无障碍与适配
**优先级**: P1

---

#### 需求定义

**目标**: 为所有前端页面添加基础无障碍支持；使侧边栏和主要页面在移动端可用。

---

#### 改动范围

**修改文件**:
- `apps/web/src/components/sidebar.tsx` — 响应式折叠 + 汉堡菜单
- `apps/web/src/app/(dashboard)/layout.tsx` — 移动端布局适配
- 所有包含 `<input>` 的页面 — 添加 `<label>` 或 `aria-label`
- 所有包含错误提示的位置 — 添加 `role="alert"`
- 搜索模式切换 — 添加 `role="tablist"` / `role="tab"` / `aria-selected`

**新增文件**:
- `apps/web/src/components/mobile-nav.tsx` — 移动端导航组件（汉堡菜单 + 抽屉）

---

#### 无障碍（a11y）改动清单

| 组件/页面 | 改动 |
|----------|------|
| 所有 `<input>` | 添加 `aria-label` 或关联 `<label htmlFor>` |
| 必填字段 | 添加 `aria-required="true"` |
| 错误提示 | 添加 `role="alert"` + `aria-live="polite"` |
| 搜索模式切换 | 添加 `role="tablist"`, 子按钮 `role="tab"` + `aria-selected` |
| 状态徽章 | 添加 `aria-label`（如 `aria-label="状态：草稿"`） |
| 侧边栏导航链接 | 添加 `aria-current="page"` 标记当前页面 |
| Modal / Dialog | 添加 `role="dialog"` + `aria-modal="true"` + focus trap |
| 按钮 | 图标按钮添加 `aria-label`（如关闭、删除按钮） |

---

#### 移动端适配

1. **侧边栏**：在 `< 768px` 宽度时默认隐藏，通过汉堡菜单图标打开
2. **汉堡菜单**：固定在顶部左侧，点击展开侧边栏（overlay 覆盖）
3. **侧边栏展开时**：全屏覆盖，点击外部区域或关闭按钮收起
4. **主内容区**：在移动端占满宽度
5. **表格**：在移动端改为卡片布局或允许水平滚动
6. **搜索页面**：输入框和按钮在移动端纵向排列

---

#### 不做什么

- 不做 WAI-ARIA 完整审计（只做最常见的基础项）
- 不做键盘快捷键系统
- 不做高对比度主题
- 不做 screen reader 全流程优化

---

#### 验收标准

- [ ] 所有 `<input>` 有 `aria-label` 或 `<label>`
- [ ] 错误提示有 `role="alert"`
- [ ] 在 375px 宽度下侧边栏不遮挡内容
- [ ] 汉堡菜单可展开/收起侧边栏
- [ ] Tab 键可在页面元素间导航
- [ ] axe DevTools 扫描无 critical 或 serious 级别问题

**预估工作量**: 2 天

---

### T-41-07: 后端优化（流式上传 + CORS 收紧 + 版本号同步）

**任务版本号**: v0.41.7
**所属功能项**: v0.41.0 — 后端优化
**优先级**: P1

---

#### 需求定义

**目标**: 修复大文件上传全量读入内存问题；收紧 CORS 配置；同步 API 版本号。

---

#### 改动范围

**修改文件**:
- `services/api/app/services/asset_service.py` — 流式上传到 MinIO
- `services/api/app/main.py` — CORS allow_headers 收紧 + 版本号从 VERSION 文件读取
- `services/api/app/routers/ws.py` — Redis 连接池化
- `services/api/app/routers/auth.py` — 前后端密码验证规则对齐

---

#### 各子功能详细设计

**流式上传**:
1. `asset_service.py` 中 `_upload_file()` 方法改为流式：
   - 不再 `await file.read()` 读全量到内存
   - 使用 `file.file`（SpooledTemporaryFile）直接传给 MinIO `put_object()`
   - MinIO SDK 的 `put_object()` 支持 file-like object + content_length
   - 同时计算 SHA-256（边读边 hash）
2. 预期效果：上传 100MB 文件不再占用 100MB+ 内存

**CORS 收紧**:
1. `allow_headers` 从 `["*"]` 改为明确列表：`["Content-Type", "Authorization", "X-Request-ID"]`
2. 保持 `allow_credentials=True` + `allow_origins` 从环境变量读取

**版本号同步**:
1. `main.py` 的 `create_app()` 中从 `VERSION` 文件读取版本号
2. `FastAPI(title="KB Platform API", version=version_from_file)`
3. 如 VERSION 文件不存在，fallback 为 "0.0.0"

**WebSocket Redis 连接池化**:
1. 使用全局 Redis 连接池而非每连接创建新客户端
2. 在 app startup 创建 `redis.asyncio.ConnectionPool`
3. WebSocket handler 从池中获取连接

---

#### 不做什么

- 不修改上传 API 的接口契约
- 不修改 MinIO 客户端库
- 不做上传断点续传

---

#### 验收标准

- [ ] 上传 50MB 文件时 API 内存占用不超过 20MB
- [ ] CORS 预检请求只允许 Content-Type/Authorization/X-Request-ID
- [ ] `/openapi.json` 中版本号与 VERSION 文件一致
- [ ] 10 个并发 WebSocket 连接只创建一个 Redis 连接池

**预估工作量**: 1.5 天

---

### T-41-08: 部署加固（docker-compose 安全 + 前端容器 + API Key 检测）

**任务版本号**: v0.41.8
**所属功能项**: v0.41.0 — 部署加固
**优先级**: P1

---

#### 需求定义

**目标**: 移除 docker-compose 中的默认密码；添加前端容器定义；API 启动时检测 AI 模型配置并在前端提示。

---

#### 改动范围

**修改文件**:
- `docker-compose.yml` — 移除默认密码，改为必须通过 .env 注入
- `docker-compose.yml` — 新增 web 前端服务定义
- `services/api/app/routers/health.py` — 新增 `/v1/system/status` 端点

**新增文件**:
- `infra/docker/web.Dockerfile` — Next.js 生产构建 Dockerfile
- `.env.example` — 更新，标注哪些变量是必填

---

#### docker-compose 安全改造

**当前问题**:
```yaml
POSTGRES_PASSWORD: change_me          # 硬编码默认值
JWT_SECRET: ${JWT_SECRET:-change-me-in-production}  # 有默认值
```

**改造为**:
```yaml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?必须在 .env 中设置 POSTGRES_PASSWORD}
JWT_SECRET: ${JWT_SECRET:?必须在 .env 中设置 JWT_SECRET}
ENCRYPTION_KEY: ${ENCRYPTION_KEY:?必须在 .env 中设置 ENCRYPTION_KEY}
```

使用 `${VAR:?msg}` 语法，如果变量未设置则 docker-compose up 时直接报错。

---

#### 前端容器

```yaml
web:
  build:
    context: .
    dockerfile: infra/docker/web.Dockerfile
  ports:
    - "${WEB_PORT:-3000}:3000"
  environment:
    NEXT_PUBLIC_API_URL: http://api:8080
  depends_on:
    api:
      condition: service_healthy
  restart: unless-stopped
```

**web.Dockerfile**:
1. Stage 1: Node.js 20-slim 构建 `npm run build`
2. Stage 2: Node.js 20-slim 运行 `npm start`
3. 非 root 用户运行
4. 暴露 3000 端口

---

#### API Key 检测

**新增端点**: `GET /v1/system/status`（需登录，任意角色）

**返回**:
```json
{
  "data": {
    "ai_configured": true,
    "search_embeddings_available": true,
    "model_providers": ["openai"]
  }
}
```

**业务规则**:
1. 查询 ModelProvider 表，是否有至少一条 status=active 的记录
2. 查询 ModelRoute 表，是否有 task_type 包含 qa/generate 的路由
3. 查询 DocEmbedding 表，当前项目是否有 embedding 数据
4. 前端在项目详情页加载时调用此端点
5. 如果 `ai_configured=false`，在项目详情页顶部显示黄色提示条："AI 智能功能尚未启用，请前往[模型配置]页面添加 AI 服务"

---

#### 不做什么

- 不做 secret rotation 自动化
- 不做 K8s deployment manifests
- 不做自动迁移竞争解决（记录为已知风险）

---

#### 验收标准

- [ ] 未设置 POSTGRES_PASSWORD 时 `docker-compose up` 报错并提示
- [ ] 未设置 JWT_SECRET 时 `docker-compose up` 报错并提示
- [ ] `docker-compose up` 可启动前端容器，访问 :3000 正常
- [ ] 未配置 ModelProvider 时项目详情页显示黄色提示条
- [ ] 已配置 ModelProvider 后提示条消失

**预估工作量**: 1.5 天

---

## 第六章 实现约束

### 6.1 目录结构规范

- 新增服务文件放在对应 service 目录下（如 `qa_service.py` → `services/api/app/services/`）
- 新增前端组件放在 `apps/web/src/components/`
- 新增前端工具函数放在 `apps/web/src/lib/`
- Alembic 迁移文件路径：`infra/sql/alembic/versions/`

### 6.2 Migration 命名规范

格式：`{hash}_{描述}.py`，如 `f5a6b7c8d9e0_add_refresh_token_table.py`

### 6.3 审计要求

每个涉及数据写入的 API 操作必须记录审计日志。

### 6.4 权限要求

新增的 `/v1/qa/ask` 和 `/v1/search/hybrid` 端点需要登录认证（任意角色可用）。

---

## 第七章 任务领取规则

1. 每次只能领取一个任务
2. 完成后按第十一章格式汇报，确认再领下一个
3. 不混做不同任务
4. 衍生任务仅记录不执行

---

## 第八章 测试要求

引用 `docs/tech-specs/testing-strategy.md`。

- 后端：pytest，每个新 service 至少 5 个测试用例
- 前端：vitest，每个新组件至少 3 个测试用例
- 集成：`scripts/ci_verify.sh`
- 搜索功能：需测试中文、英文、特殊字符、空查询
- AI 问答：需 mock LLM 响应进行测试

---

## 第九章 版本号管理

引用 `docs/tech-specs/dev-governance.md` §1.1–§1.4。

| 任务编号 | 版本号 |
|---------|--------|
| T-41-01 | v0.41.1 |
| T-41-02 | v0.41.2 |
| T-41-03 | v0.41.3 |
| T-41-04 | v0.41.4 |
| T-41-05 | v0.41.5 |
| T-41-06 | v0.41.6 |
| T-41-07 | v0.41.7 |
| T-41-08 | v0.41.8 |

---

## 第十章 文档产出要求

引用 `docs/tech-specs/dev-governance.md` §0.7。

每个任务完成后必须更新：
- VERSION 文件
- CHANGELOG.md
- TODO_NEXT.md

版本全部完成后必须产出：
- 封板审计报告 `docs/versions/seal-audit-v0.41.md`
- 版本发布说明 `docs/versions/RELEASE_NOTES_v0.41.md`

---

## 第十一章 汇报格式

引用 `docs/tech-specs/dev-governance.md` §0.7。

每个任务完成后按以下 9 项结构汇报：
1. 计划 / 当前迭代目标
2. 文件变更清单
3. 用户可见能力
4. 真实场景验证（至少 5 个场景）
5. 开放问题
6. 收尾说明
7. 版本状态更新
8. commit 信息
9. 是否继续下一个任务

---

## 第十二章 新增数据库表汇总

| 任务编号 | 新增表名 | 字段数 |
|---------|---------|-------|
| T-41-01 | refresh_token | 6 |

总计新增 1 张表。

---

## 第十三章 开始前必须先输出

Agent 在开始 T-41-01 之前，必须先输出：
1. 当前代码现状理解（确认 v0.40.3 基线）
2. T-41-01 的实施计划
3. T-41-01 的预计修改文件清单

**在这三项输出之前，不要开始写代码。**

---

## 第十四章 完成状态追踪

| 任务版本号 | 任务名称 | 计划周期 | 实际完成日期 | 迭代次数 | 状态 |
|----------|--------|--------|----------|--------|------|
| v0.41.1 | T-41-01 WebSocket 租户隔离 + Refresh Token 安全加固 | 1.5 天 | — | 0 | Planned |
| v0.41.2 | T-41-02 前后端统一错误码系统 | 1.5 天 | — | 0 | Planned |
| v0.41.3 | T-41-03 智能问答搜索 | 3 天 | — | 0 | Planned |
| v0.41.4 | T-41-04 前端用户化语言 + 搜索 XSS 修复 | 1.5 天 | — | 0 | Planned |
| v0.41.5 | T-41-05 前端体验修复 | 2 天 | — | 0 | Planned |
| v0.41.6 | T-41-06 前端无障碍 + 移动端适配 | 2 天 | — | 0 | Planned |
| v0.41.7 | T-41-07 后端优化 | 1.5 天 | — | 0 | Planned |
| v0.41.8 | T-41-08 部署加固 | 1.5 天 | — | 0 | Planned |

**总计预估**: 14.5 个工作日

---

## 第十五章 决策和假设

**关键决策**:
1. Refresh token 采用轻量方案（数据库记录+吊销），不做完整轮换。原因：账户体系未来迁移至中台 PaaS，不值得投入完整实现
2. AI 问答采用同步 API 而非 SSE 流式。原因：当前阶段 MVP，简化实现
3. 错误码系统不引入 i18n 框架，硬编码中文。原因：产品定位为中文市场

**重要假设**:
1. 假设 LLM 调用延迟 < 30 秒（超时后返回友好错误）
2. 假设 pgvector embedding 已由 ai-orchestrator 生成（本版本不做自动触发）
3. 假设移动端用户只做查看操作，不做复杂编辑

---

## 第十六章 风险和缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|------|------|---------|
| LLM 调用延迟过高导致问答体验差 | 中 | 中 | 30 秒超时 + 前端 loading 动画 + 友好错误提示 |
| 混合搜索在大数据量下性能问题 | 低 | 高 | 分页 + 限制 top_k + 数据库索引已建 |
| 前端标签映射遗漏导致显示技术词 | 中 | 低 | fallback 为原始值 + 测试全覆盖 |
| docker-compose 必填变量变更导致现有部署失败 | 低 | 中 | .env.example 完整文档 + 升级说明 |

---

## 第十七章 变更记录

| 日期 | 变更内容 | 责任人 |
|------|---------|--------|
| 2026-03-22 | 初始版本 V1.0 | 产品 Owner |

---

*计划文档结束。*
