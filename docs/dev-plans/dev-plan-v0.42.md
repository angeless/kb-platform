# KB Platform v0.42 版本开发任务计划

**文档编号**: PLAN-2026-03-22-v042
**版本**: V3.0（完整版 — 含原子级任务拆解 + 审计全覆盖 + 上线清单 + 知识管理方法论 + 部署工具链）
**日期**: 2026-03-22
**基线 commit**: 当前 main HEAD (v0.41.8)
**基线分支**: main
**依据**: v0.41.8 全面深度审计报告 `docs/reports/v0.41-full-audit-report.md`
**作者**: 产品 Owner

---

## 第一章 开发管理（总原则）

### 1.1 不推倒重写

本计划所有任务均基于 v0.41.8 现有代码增量修复和增强。禁止重构无关模块、禁止重写已有业务逻辑、禁止变更已有 API 契约（除非本计划明确要求）。

### 1.2 继承已有能力

v0.41 已完成的全部能力（WebSocket 租户隔离、Refresh Token 安全加固、统一错误码、智能问答搜索、前端用户化、无障碍、移动端适配、CORS 收紧、部署加固等）均继承不变。

### 1.3 最小改动原则

每个任务只改必须改的文件。如果发现无关问题，记录到"衍生任务"但不执行。

### 1.4 任务领取规则

每次只能领取一个任务。完成后按第十五章格式汇报，确认后再领下一个。

---

## 第二章 当前阶段事实

### 2.1 项目目标（一句话）

将多模态原始资料自动整理为可追溯、可维护、可被 AI 使用的结构化知识系统。

### 2.2 当前基线

- **版本**: v0.41.8
- **分支**: main
- **v0.41 全部完成**: 智能搜索 + 错误体系 + 审计修复 + 前端用户化 + 无障碍 + 部署加固

### 2.3 v0.41.8 审计发现的待修复项

基于 2026-03-22 全面深度审计报告，按严重程度排列：

**严重（4 项）**:
1. C-01: forgot-password 页面语法错误导致渲染崩溃
2. C-02: 注册后跳转到 /projects 但未登录
3. C-03: Dashboard 认证守卫使用从未写入的 localStorage 值
4. C-04: 密码重置 Token 在生产环境也返回明文

**高危（9 项）**:
5. H-01: SSRF — URL 导入无域名/IP 限制
6. H-02: CORS 允许凭证但无 CSRF 保护
7. H-03: WebSocket JWT 通过 URL query 传递
8. H-04: Embedding JSONB 回退 N+1 查询 + 内存问题
9. H-05: Embedding 删除-插入非原子操作
10. H-06: QA 服务 decrypt_value() 函数不存在
11. H-07: MinIO 使用默认凭证硬编码
12. H-08: 无账户级登录锁定
13. H-09: Redis 无密码保护

**中等（15 项）**:
14. M-01: 搜索结果无分页（前端缺失，后端已有）
15. M-02: 文件上传无前端类型/大小校验
16. M-03: 密码重置 Token 前端明文显示（dev mode 未隔离）
17. M-04: ZIP 上传无 archive bomb 检测
18. M-05: Crypto PBKDF2 使用确定性 salt
19. M-06: `get_settings()` 每次创建新 Settings 实例
20. M-07: Export 端点无 rate limit
21. M-08: QA 服务 LLM 调用 30s 超时，无流式响应
22. M-09: Docker services 端口全部暴露到宿主机
23. M-10: Celery worker 任务缺少幂等性保护
24. M-11: 审核工作流缺少通知机制
25. M-12: 前端无 Error Boundary 保护列表页
26. M-13: QA 回答未做 Markdown 渲染
27. M-14: Alembic downgrade 直接 DROP TABLE，无数据保护
28. M-15: 邮箱唯一性检查是全局的，非租户级别

**审计覆盖状态**: 28/28 项全部由 v0.42 任务（T-42-01 ~ T-42-12）覆盖。

### 2.4 发布准备差距

除审计问题外，发布上线还需要：
- 前端 Wiki 化呈现改造
- 知识管理核心方法论落地（首建、增量、路由、跨库索引）
- 邮件通知基础能力
- 生产环境配置与监控
- 部署工具链搭建
- 用户文档 / 帮助系统

---

## 第三章 本轮目标与边界

### 3.1 版本主题

**v0.42: 发布准备 — 安全修复 + Wiki 呈现 + 知识管理增强 + 部署工具链 + 上线就绪**

### 3.2 版本划分

| 任务范围 | 内容 |
|---------|------|
| **P0 安全修复** | 4 个 CRITICAL + 6 个 HIGH 审计问题修复 |
| **P0 功能修复** | QA decrypt 修复、搜索分页 |
| **P1 Wiki 呈现** | 前端文档展示改造为 Wiki 形态（目录树导航 + 面包屑 + 文内锚点 + 关联推荐） |
| **P1 知识管理增强** | 首建方法论（MECE + 维度声明）、增量合入（五分类）、多库路由、跨库索引 |
| **P2 部署工具链** | Nginx 配置、HTTPS 模板、生产 compose、备份脚本、监控集成 |
| **P2 发布就绪** | 邮件骨架、生产配置模板、健康检查增强、用户引导、运维文档 |

### 3.3 明确不做什么（防止范围蔓延）

1. **不做**完整邮件服务集成（仅做接口骨架 + 模板）
2. **不做**实时协作编辑
3. **不做**SSO/OAuth/LDAP
4. **不做**多语言国际化
5. **不做**暗黑模式
6. **不做**知识图谱可视化（v0.43 考虑）
7. **不做**对话式多轮问答（v0.43 考虑）
8. **不做**文件在线预览（v0.43 考虑）

---

## 第四章 优先级与顺序

| 序号 | 任务编号 | 任务名称 | 优先级 | 依赖 | 预估工时 |
|:---:|:---:|---|:---:|:---:|:---:|
| 1 | T-42-01 | CRITICAL 修复批次（C-01~C-04 + H-06） | P0 | 无 | 4h |
| 2 | T-42-02 | 安全加固批次一（SSRF + CSRF + Redis 密码 + MinIO 参数化） | P0 | 无 | 12h |
| 3 | T-42-03 | 安全加固批次二（账户锁定 + Embedding 原子化 + ZIP bomb） | P0 | 无 | 10h |
| 4 | T-42-04 | 搜索分页 + QA 流式响应 | P1 | T-42-01 | 10h |
| 5 | T-42-05 | 前端 Wiki 呈现改造 | P1 | T-42-04 | 16h |
| 6 | T-42-06 | 知识管理增强 — 首建方法论 + 架构质量门禁 | P1 | 无 | 12h |
| 7 | T-42-07 | 知识管理增强 — 增量合入 + 多库路由 + 跨库索引 | P1 | T-42-06 | 16h |
| 8 | T-42-08 | 部署工具链 — Nginx + HTTPS + 生产 Compose + 备份 + 监控 | P2 | T-42-02 | 16h |
| 9 | T-42-09 | 发布就绪 — 邮件骨架 + 生产配置 + 用户引导 + 运维文档 | P2 | T-42-08 | 12h |
| 10 | T-42-10 | 上线验收 — 全量回归测试 + 上线清单逐项确认 | P0 | 全部 | 8h |
| 11 | T-42-11 | 审计补充修复一 — WebSocket JWT + Embedding N+1 + Settings 缓存 + Export 限流 | P1 | T-42-02 | 10h |
| 12 | T-42-12 | 审计补充修复二 — 上传校验 + Celery 幂等 + Error Boundary + Alembic 保护 + 邮箱隔离 | P1 | T-42-03 | 12h |

**总预估**: ~138h（约 18 个工作日）

---

## 第五章 各任务详细定义

---

### T-42-01: CRITICAL 修复批次

**任务版本号**: v0.42.1
**优先级**: P0
**预估工时**: 4h

#### 需求定义

**目标**: 修复 4 个严重问题 + 1 个 QA 功能阻塞问题，恢复核心用户流程。

#### 子任务清单

| 编号 | 问题 | 修改文件 | 修改内容 |
|------|------|---------|---------|
| C-01 | forgot-password 语法错误 | `apps/web/src/app/forgot-password/page.tsx` | 删除第 134-136 行多余的 `div>);}`  |
| C-02 | 注册后跳转错误 | `apps/web/src/app/register/page.tsx` | `router.push("/projects")` → `router.push("/login?registered=true")`；login/page.tsx 读取 `registered` 参数显示"注册成功，请登录" |
| C-03 | Dashboard 认证守卫竞态 | `apps/web/src/app/(dashboard)/layout.tsx` + `stores/auth-store.ts` | 添加 `isCheckingAuth` 状态；layout 等待 checkAuth 完成后再判断；loading 时显示骨架屏 |
| C-04 | reset_token 生产泄露 | `services/api/app/services/auth_service.py` | `forgot_password()` 中添加 `if self.settings.environment == "development":` 条件 |
| H-06 | QA decrypt 函数不存在 | `services/api/app/services/qa_service.py` | `decrypt_value` → `decrypt`，同时修正 import path |

#### 验收标准

1. `/forgot-password` 页面正常渲染
2. 注册成功后跳转到 `/login` 并显示成功提示
3. 刷新 dashboard 页面不再闪烁到登录页
4. `environment=production` 时 forgot-password API 不返回 reset_token 字段
5. QA 服务能正确解密 API Key 并调用 LLM

#### 原子级拆解（6 个子任务）

**T-42-01-A: 修复 forgot-password 页面语法错误（C-01）**
- 改动文件：`apps/web/src/app/forgot-password/page.tsx`
- 改动内容：删除第 134-136 行多余的 `div>);\}`
- 改动量：~3 行删除
- 验收：`/forgot-password` 页面正常渲染 + `npm run build` 无编译错误

**T-42-01-B: 修复注册后跳转逻辑（C-02）**
- 改动文件：`register/page.tsx` + `login/page.tsx`
- 改动内容：`router.push("/projects")` → `router.push("/login?registered=true")`；login 读取参数显示成功提示
- 改动量：~15 行修改
- 验收：注册后跳转 /login 并显示绿色成功提示

**T-42-01-C: 修复 Dashboard 认证守卫竞态（C-03）**
- 改动文件：`stores/auth-store.ts` + `(dashboard)/layout.tsx`
- 改动内容：新增 `isCheckingAuth` 状态；移除 localStorage 检查；等待 checkAuth 完成再判断
- 改动量：~15 行修改
- 验收：已登录用户刷新 dashboard 不闪烁到 login

**T-42-01-D: 修复 reset_token 生产泄露（C-04）**
- 改动文件：`services/api/app/services/auth_service.py`
- 改动内容：仅 `environment == "development"` 时返回 reset_token
- 改动量：~5 行修改
- 验收：production 模式 forgot-password API 不返回 reset_token 字段

**T-42-01-E: 修复 QA decrypt 调用（H-06）**
- 改动文件：`services/api/app/services/qa_service.py`
- 改动内容：`decrypt_value` → `decrypt`，修正 import path 和调用参数
- 改动量：~5 行修改
- 验收：QA 服务能正确解密加密的 API Key

**T-42-01-F: T-42-01 收尾**
- 改动文件：VERSION（→ 0.42.1）、CHANGELOG.md、TODO_NEXT.md
- 验收：`npm run build` + `pytest` 全部通过，VERSION = 0.42.1

---

### T-42-02: 安全加固批次一

**任务版本号**: v0.42.2
**优先级**: P0
**预估工时**: 12h

#### 子任务清单

| 编号 | 问题 | 修改内容 |
|------|------|---------|
| H-01 | SSRF | 新增 `app/utils/url_validator.py`：阻止内网 IP（10.x、172.16-31.x、192.168.x、127.x、169.254.x、::1）；`import_url` 调用前校验 |
| H-02 | CSRF | 所有变更请求要求 `X-Requested-With: XMLHttpRequest` 自定义头，前端 api.ts 统一添加 |
| H-07 | MinIO 默认凭证 | `docker-compose.yml` 中 MinIO 改用 `${MINIO_ROOT_USER:?}` 和 `${MINIO_ROOT_PASSWORD:?}`；`.env.example` 添加对应条目 |
| H-09 | Redis 无密码 | `docker-compose.yml` Redis 添加 `--requirepass ${REDIS_PASSWORD}`；所有 redis_url 添加密码；`settings.py` 添加 `redis_password` |

#### 验收标准

1. `import_url("http://169.254.169.254/")` → 400 "不允许访问内网地址"
2. 不携带 `X-Requested-With` 头的 POST 请求 → 403
3. MinIO 启动必须配置密码
4. Redis 启动必须配置密码

#### 原子级拆解（8 个子任务）

**T-42-02-A: URL 验证器（H-01）** — 新增 `services/api/app/utils/url_validator.py`（~40 行），阻止内网 IP + 非 HTTP 协议
**T-42-02-B: 集成到 import_url（H-01）** — 修改 `asset_service.py`，调用 `validate_url()`（~5 行）
**T-42-02-C: URL 验证器单元测试** — 新增 `tests/test_url_validator.py`（~40 行）
**T-42-02-D: CSRF middleware（H-02）** — 新增 csrf middleware，POST/PUT/PATCH/DELETE 要求 `X-Requested-With` 头（~30 行）
**T-42-02-E: 前端统一添加 CSRF 头** — 修改 `apps/web/src/lib/api.ts`（~3 行）
**T-42-02-F: MinIO 凭证参数化（H-07）** — 修改 `docker-compose.yml` + `.env.example`（~10 行）
**T-42-02-G: Redis 密码保护（H-09）** — 修改 `docker-compose.yml` + `settings.py` + `.env.example`（~15 行）
**T-42-02-H: T-42-02 收尾** — VERSION → 0.42.2，CHANGELOG，TODO_NEXT

---

### T-42-03: 安全加固批次二

**任务版本号**: v0.42.3
**优先级**: P0
**预估工时**: 10h

#### 子任务清单

| 编号 | 问题 | 修改内容 |
|------|------|---------|
| H-05 | Embedding 非原子 | 改用 `INSERT ... ON CONFLICT (doc_id) DO UPDATE` 原子 upsert |
| H-08 | 无账户锁定 | 新增 `login_attempts` Redis key（email 维度），连续 5 次失败锁定 15 分钟；返回 423 + 中文提示 |
| M-04 | ZIP bomb | `import_archive` 限制：最大解压后 500MB、最多 200 个文件、最深 5 层目录 |
| M-05 | Crypto salt | `crypto.py` 改用随机 16 字节 salt，与密文一起存储 |
| M-09 | 端口暴露 | docker-compose.yml 中 PostgreSQL/Redis/MinIO 端口改为仅内部网络暴露（去掉 `ports`，改用 `expose`） |

#### 验收标准

1. 并发 embedding upsert 不产生重复记录
2. 同一邮箱连续 5 次错误密码后 → 423 "账户已临时锁定"
3. 上传 1GB ZIP bomb → 400 "解压后体积超限"
4. 外部无法直接访问 PostgreSQL 5432 端口

#### 原子级拆解（6 个子任务）

**T-42-03-A-migration: doc_embeddings UNIQUE 约束** — 新增 alembic 迁移（~20 行）
**T-42-03-A: Embedding 原子 upsert（H-05）** — 修改 `embedding_service.py`，改用 `INSERT ON CONFLICT DO UPDATE`（~15 行）
**T-42-03-B: 账户登录锁定（H-08）** — 修改 `auth_service.py`，Redis 计数器 + 5 次锁定 15 分钟（~25 行）
**T-42-03-C: ZIP bomb 防护（M-04）** — 修改 `asset_service.py`，解压限制 500MB/200 文件/5 层（~30 行）
**T-42-03-D: Crypto salt 随机化（M-05）** — 修改 `crypto.py`，随机 salt + 向后兼容（~20 行）
**T-42-03-E: Docker 端口收紧（M-09）** — 修改 `docker-compose.yml`，内部服务 ports → expose（~10 行）
**T-42-03-F: T-42-03 收尾** — VERSION → 0.42.3

---

### T-42-04: 搜索分页 + QA 流式响应

**任务版本号**: v0.42.4
**优先级**: P1
**预估工时**: 10h

#### 搜索分页（前端集成）

> **注意**: 后端 `/v1/search/text` 和 `/v1/search/hybrid` 已支持 `page` / `page_size` 参数（默认 page=1, page_size=20），响应已包含 `PaginationMeta`。此任务仅需前端集成。

- 前端搜索页添加分页组件（上一页/下一页/页码）
- 前端搜索请求传递 page/page_size 参数并读取 meta.total
- 不改动后端搜索 API

#### QA 流式响应

- `/v1/qa/ask` 添加 `stream=true` 参数
- 后端使用 SSE (Server-Sent Events) 流式返回 LLM 响应
- 前端 QA 区域逐字显示答案（打字机效果）
- 保留非流式模式作为回退

#### 原子级拆解（6 个子任务）

**T-42-04-A: 前端分页组件** — 新增 `apps/web/src/components/pagination.tsx`（~50 行）
**T-42-04-B: 搜索页集成已有后端分页** — 修改 `search/page.tsx`，请求传递 page/page_size，读取 meta.total 渲染分页（~30 行）
**T-42-04-C: QA 流式后端 SSE** — 修改 `qa.py` + `qa_service.py`，stream=true 返回 SSE（~50 行）
**T-42-04-D: QA 流式前端打字机** — 修改搜索页 QA 区域，ReadableStream 逐字显示（~40 行）
**T-42-04-E: QA Markdown 渲染（M-13 补充）** — 修改搜索页，QA 回答改用 MarkdownView（~5 行）
**T-42-04-F: T-42-04 收尾** — VERSION → 0.42.4

---

### T-42-05: 前端 Wiki 呈现改造

**任务版本号**: v0.42.5
**优先级**: P1
**预估工时**: 16h

#### Wiki 布局结构

```
┌──────────────────────────────────────────────────┐
│  面包屑: 项目 > 架构节点A > 架构节点B > 当前文档    │
├─────────────┬────────────────────────────────────┤
│             │                                    │
│  左侧导航   │       文档正文区                     │
│  (架构树)   │                                     │
│             │  ┌─────────────────────────────┐    │
│  ▸ 节点A   │  │  # 文档标题                   │    │
│    ▸ 子节点 │  │  正文内容（Markdown 渲染）      │    │
│  ▸ 节点B   │  │  ## 来源追溯                   │    │
│  ▸ 节点C   │  │  ## 相关知识                   │    │
│             │  └─────────────────────────────┘    │
│             │                                    │
│             │  右侧悬浮: 文内目录 (TOC)           │
│             │                                    │
├─────────────┴────────────────────────────────────┤
│  底部: 版本信息 | 最后更新 | 贡献者               │
└──────────────────────────────────────────────────┘
```

#### 功能点

| 功能 | 描述 | 新增/改造 |
|------|------|---------|
| Wiki 布局 | 三栏布局（左导航 + 正文 + 右 TOC） | 新增页面 `projects/[id]/wiki/[docId]/page.tsx` |
| 架构树导航 | 左侧展示架构树，点击展开并显示关联文档 | 复用已有 tree-node 组件 |
| 面包屑导航 | 显示当前文档在架构中的路径 | 新增组件 `wiki-breadcrumb.tsx` |
| 文内目录 (TOC) | 自动提取 h2/h3 生成右侧浮动目录 | 新增组件 `wiki-toc.tsx` |
| 来源追溯卡片 | 文档底部显示关联的原始素材 | 新增组件 `source-refs.tsx` |
| 相关知识推荐 | 文档底部显示语义相似的其他文档 | 调用已有 embedding 接口 |
| Wiki 内搜索 | 顶部搜索框，支持全文 + 语义搜索 | 复用已有搜索页逻辑 |
| 移动端适配 | 小屏隐藏左导航，可滑出 | 使用已有 mobile-nav 模式 |

#### 路由设计

```
/projects/:id/wiki                → Wiki 首页（架构树概览 + 最近更新）
/projects/:id/wiki/:docId         → 文档阅读页
/projects/:id/wiki/:docId/edit    → 文档编辑页（复用已有编辑器）
/projects/:id/wiki/search?q=xxx  → Wiki 内搜索
```

#### 不改动后端

Wiki 呈现是纯前端改造，复用已有的所有后端 API。

#### 原子级拆解（12 个子任务）

**T-42-05-A: Wiki 路由注册 + 空白页面骨架** — 新增 3 个页面文件（wiki/page, wiki/[docId]/page, wiki/search/page）（~30 行）
**T-42-05-B: 左侧架构树导航** — 新增 `wiki-sidebar.tsx`，复用 tree-node 组件（~60 行）
**T-42-05-C: 面包屑导航** — 新增 `wiki-breadcrumb.tsx`（~35 行）
**T-42-05-D: 文档阅读页主体** — 三栏布局 + Markdown 渲染 + 元信息（~60 行）
**T-42-05-E: 文内目录 (TOC)** — 新增 `wiki-toc.tsx`，提取 h2/h3 + 平滑滚动（~45 行）
**T-42-05-F: 来源追溯卡片** — 新增 `source-refs.tsx`，文档底部显示关联 asset（~35 行）
**T-42-05-G: 相关知识推荐** — 调用语义搜索接口，显示 top-5 相关文档（~25 行）
**T-42-05-H: Wiki 内搜索** — 搜索页复用，结果链接指向 wiki 页面（~40 行）
**T-42-05-I: 移动端适配** — 小屏隐藏左导航和 TOC（~15 行）
**T-42-05-J: 侧栏添加 Wiki 入口** — 修改 `sidebar.tsx`（~5 行）
**T-42-05-K: Wiki 首页内容** — 架构概览卡片 + 最近更新列表（~40 行）
**T-42-05-L: T-42-05 收尾** — VERSION → 0.42.5

---

### T-42-06: 知识管理增强 — 首建方法论 + 架构质量门禁

**任务版本号**: v0.42.6
**优先级**: P1
**预估工时**: 12h

#### 方法论核心：首次创建知识库 — 三阶段渐进式建构

**总纲**：理解 → 结构 → 归位 → 连接 → 演化

##### 第一阶段：理解（Understanding）

对每个 chunk 提取 5 个知识元素：
- **主题标签**：2-5 个关键词
- **知识类型**：事实（Fact）/ 流程（Process）/ 规范（Rule）/ 定义（Definition）/ 案例（Case）
- **受众层级**：入门 / 进阶 / 专家
- **时效性**：永久有效 / 有时效 / 已过期
- **来源质量**：官方文档 / 教程 / 个人笔记 / 讨论

##### 第二阶段：结构（Structuring）— MECE + 分类维度声明

MECE（互斥且穷举）：每个知识单元应有且仅有一个"主位置"。

分类维度选择（按资料特征自动推荐）：

| 维度 | 适用场景 | 示例 |
|------|---------|------|
| **按主题**（Topic-based） | 知识百科、技术文档 | `数据库 > 索引 > B+树` |
| **按流程**（Process-based） | SOP、操作手册 | `需求 > 设计 > 开发 > 测试` |
| **按受众**（Audience-based） | 培训资料、分级教程 | `新手入门 > 进阶实践 > 专家深潜` |
| **按时间**（Chronological） | 日志、记录 | `2024Q1 > 2024Q2 > 2024Q3` |
| **混合**（Hybrid） | 复杂知识体系 | 一级按主题，二级按流程 |

架构提议流程：LLM 分析聚类 → 推荐分类维度 → 生成架构树 → 自动质量检查 → 输出覆盖度评分 → 用户审核

##### 第三阶段：归位（Placement）

```
对每个 chunk：
  1. 计算与每个叶子节点的语义相似度
  2. 选择相似度最高的节点作为"主归位"
  3. 相似度 < 0.3 → "未归类"，提交人工审核
  4. 与多个节点相似度都 > 0.7 → "交叉引用候选"
```

#### 后端改动

**1. 架构提议增强 — `orchestrator/prompts.py`**

在 `propose_architecture` prompt 中增加 MECE 原则检查 + 分类维度声明 + 覆盖度自检。

Prompt 模板：
```
请为以下知识内容设计架构树。要求：
1. 声明你选择的分类维度（按主题/按流程/按受众/混合）并解释原因
2. 确保节点满足 MECE 原则：
   - 互斥：任何一个知识 chunk 的主归位唯一
   - 穷举：所有 chunk 都能归入某个节点
3. 如果有无法归类的内容，列出并解释原因
4. 架构深度不超过 5 层，每层 3-7 个节点
5. 输出覆盖度评分（0-100%）
```

**2. 架构质量门禁 — `pipeline_worker/stages.py` stage 4**

在 stage 4（validate）增加自动检查：
- 节点深度不超过 5 层
- 叶子节点不少于 2 个文档
- 无孤立节点
- 节点名称无重复

**3. 文档生成增强 — `orchestrator/prompts.py`**

`generate_docs` prompt 增加：统一文档模板 + "关键词"元数据 + "知识类型"标注

**4. 前端：架构审核增强 — `projects/[id]/review/page.tsx`**

显示 MECE 检查结果 + 覆盖度评分 + 分类维度说明

#### 实现映射

| 方法论步骤 | 对应代码位置 | 现状 | v0.42 改动 |
|-----------|------------|------|-----------|
| 内容解析 | ingestion-worker/parsers/ | 已有 | 不变 |
| 知识元素提取 | pipeline-worker stage 3 | 仅做分类 | 增强：提取 5 个元素 |
| 领域识别 | orchestrator/propose_architecture | 已有 | 增强：输出领域声明 |
| MECE 架构 | orchestrator/propose_architecture | 无 MECE | 增加 MECE + 维度声明 |
| 质量门禁 | pipeline-worker stage 4 | 仅验长度 | 增加 4 项检查 |
| 归位 | orchestrator/generate_docs | 已有 | 增加交叉引用标记 |

#### 验收标准

1. 架构提议输出包含分类维度声明和覆盖度评分
2. 架构深度超过 5 层时触发警告
3. 文档生成结果包含"关键词"和"知识类型"字段

#### 原子级拆解（8 个子任务）

**T-42-06-A: 架构提议 prompt 增强** — 修改 `prompts.py`，增加 MECE + 维度声明 + 覆盖度评分（~20 行）
**T-42-06-B: 架构提议结果解析** — 修改 `tasks.py`，提取 classification_dimension + coverage_score 写入 metadata（~15 行）
**T-42-06-C: 架构质量门禁 stage 4 增强** — 修改 `quality_check.py`，新增 4 项检查（深度/稀疏/孤立/重名）（~40 行）
**T-42-06-D: 文档生成 prompt 增强** — 修改 `prompts.py`，输出增加 keywords + knowledge_type（~10 行）
**T-42-06-E: knowledge_docs 表 migration** — 新增 alembic 迁移 + 修改 Model（~25 行）
**T-42-06-F: 文档生成写入 keywords** — 修改 `doc_generate.py`，提取 LLM 结果中的 keywords/knowledge_type（~10 行）
**T-42-06-G: 前端架构审核页展示 MECE** — 修改 `review/page.tsx`，显示维度 + 评分 + 门禁结果（~30 行）
**T-42-06-H: T-42-06 收尾** — VERSION → 0.42.6

---

### T-42-07: 知识管理增强 — 增量合入 + 多库路由 + 跨库索引

**任务版本号**: v0.42.7
**优先级**: P1
**预估工时**: 16h

#### 方法论核心一：增量合入 — 五分类决策树

```
新资料进入 → 理解内容 → 分类：
  ├── NEW（新增）     — 语义相似度 < 0.3 → 创建新文档/新节点
  ├── SUPPLEMENT（补充）— 相似度 > 0.7 且含新信息 → 合并到已有文档
  ├── CORRECTION（修正）— 相似度 > 0.7 且明确否定已有结论 → 更新并保留旧版
  ├── CONFLICT（冲突） — 矛盾但无法判定谁对 → 标记冲突等待人工
  └── RESTRUCTURE（重构）— 节点过载(>15篇) / 跨域(>3节点) → 提议结构变更
```

**不适配时的三层自适应**：
- Level 1 局部生长：在现有节点下新增子节点
- Level 2 节点拆分：过载节点自动建议拆分
- Level 3 交叉引用：通过索引层解决跨域问题（不全面重构）

增量分类 Prompt 模板：
```
已有架构树如下：{architecture}
已有文档摘要如下：{existing_docs_summary}
新资料内容如下：{new_chunks}

请判断每个新 chunk 属于以下哪种分类：
- NEW / SUPPLEMENT / CORRECTION / CONFLICT / RESTRUCTURE
对每个 chunk 输出：分类、目标节点/文档、置信度、理由
```

#### 方法论核心二：多知识库路由 — 三层策略

```
Layer 1: 显式路由 — 用户指定 project_id → 直接路由
Layer 2: 语义匹配 — 对新内容生成 embedding → 与每个项目的"项目画像"做相似度
  → > 0.7 自动路由 | 0.4-0.7 推荐 top-3 用户确认 | < 0.4 建议创建新项目
Layer 3: 规则路由 — 关键词匹配 / 文件类型匹配（v0.43 考虑）
```

项目画像：每个项目维护 name + description + keywords + embedding（项目描述 + 架构节点名综合）。

#### 方法论核心三：跨知识库索引 — 主归位 + 交叉引用

**原则**：每个文档一个"主位置"（物理归属），多个"引用链接"（逻辑关联）。

5 种关联类型：

| 关联类型 | 含义 | 示例 |
|---------|------|------|
| `related` | 主题相关 | "React 性能" ↔ "DevTools" |
| `depends_on` | 前置依赖 | "部署指南" → "Docker 教程" |
| `extends` | 扩展延伸 | "Python 基础" → "Python 高级" |
| `contradicts` | 存在矛盾 | "方案 A" ↔ "方案 B" |
| `supersedes` | 替代 | "新版文档" → "旧版文档" |

3 种自动发现策略：
1. Embedding 相似度 > 0.75 → 建议 related
2. 关键词交集 >= 3 → 建议 related
3. 共享来源素材 → 建议 related

#### 后端改动

**1. 增量分类增强 — `orchestrator/prompts.py` + `tasks.py`**

`classify_incremental` 增加 RESTRUCTURE 分类 + 节点过载检测 + 交叉引用建议。

**2. 多库路由服务 — 新增 `services/api/app/services/project_router_service.py`**

```python
class ProjectRouterService:
    async def route(self, tenant_id, content_chunks) -> list[RoutingResult]:
        # 1. 显式指定 → 直接路由
        # 2. Embedding 匹配项目画像 → top-3 候选
        # 3. 返回置信度让用户确认
```

**3. 跨库索引 — 新增数据模型 + API**

```sql
CREATE TABLE cross_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    source_doc_id UUID NOT NULL REFERENCES knowledge_docs(id),
    target_doc_id UUID NOT NULL REFERENCES knowledge_docs(id),
    relation_type VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    created_by VARCHAR(20) NOT NULL DEFAULT 'system',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source_doc_id, target_doc_id, relation_type)
);
```

新增 API：
- `POST /v1/cross-refs` — 创建引用
- `GET /v1/docs/:id/cross-refs` — 获取文档的引用
- `DELETE /v1/cross-refs/:id` — 删除引用
- `POST /v1/cross-refs/auto-suggest` — 自动建议引用（异步）
- `GET /v1/projects/:id/cross-ref-graph` — 获取引用图谱数据

**4. 前端展示**

Wiki 文档页底部"关联知识"区域：同库引用直接链接，跨库引用显示 [项目名] 文档名。

#### 验收标准

1. 增量分类新增 restructure 类型且正确触发
2. 多库路由返回 top-3 候选项目
3. 跨库引用 CRUD 正常
4. 文档页显示跨库引用

#### 原子级拆解（11 个子任务）

**T-42-07-A: 增量分类 prompt 增加 RESTRUCTURE** — 修改 `prompts.py`（~15 行）
**T-42-07-B: 增量分类结果处理** — 修改 `classify.py`，restructure 标记 pending_review（~15 行）
**T-42-07-C: cross_references 数据模型** — 新增 alembic 迁移 + SQLAlchemy 模型（~50 行）
**T-42-07-D: 跨库索引 Pydantic schemas** — 新增 `cross_reference.py` schema（~30 行）
**T-42-07-E: 跨库索引 Service 层** — 新增 `cross_ref_service.py`（CRUD + auto_suggest）（~60 行）
**T-42-07-F: 跨库索引 Router 层** — 新增 `cross_refs.py` router，4 个 API 端点（~50 行）
**T-42-07-G: 项目画像字段 migration** — 新增 alembic 迁移（profile_embedding + profile_keywords）（~25 行）
**T-42-07-H: 多库路由 Service** — 新增 `project_router_service.py`，route() 返回 top-3 候选（~50 行）
**T-42-07-I: 多库路由 API 端点** — 新增 `POST /v1/projects/route`（~20 行）
**T-42-07-J: Wiki 文档页展示跨库引用** — 修改 wiki/[docId]/page.tsx，底部关联知识区域（~30 行）
**T-42-07-K: T-42-07 收尾** — VERSION → 0.42.7

---

### T-42-08: 部署工具链 — Nginx + HTTPS + 生产 Compose + 备份 + 监控

**任务版本号**: v0.42.8
**优先级**: P2
**预估工时**: 16h

#### 交付物清单

**1. Nginx 反向代理配置 — `infra/nginx/`**

```
infra/nginx/
├── nginx.conf                 # 主配置
├── conf.d/
│   └── kb-platform.conf       # 站点配置（含 WebSocket 代理）
└── ssl/                       # HTTPS 证书存放目录
```

配置要点：
- HTTP → HTTPS 301 重定向
- `/api/` → 反代到 `api:8080`
- `/ws/` → WebSocket 反代（`Upgrade` + `Connection` 头）
- `/` → 反代到 `web:3000`
- 静态资源缓存：`Cache-Control: max-age=31536000` for `/_next/static/`
- 请求体大小限制：`client_max_body_size 100m`（对齐 MAX_UPLOAD_SIZE_MB）
- 安全头：`X-Frame-Options`, `X-Content-Type-Options`, `HSTS`

**2. HTTPS 模板 — `infra/nginx/ssl/`**

提供两种方案：
- 方案 A：Let's Encrypt 自动续签（含 `certbot` 容器配置）
- 方案 B：自签证书脚本（`generate-self-signed.sh`，用于内网/测试）

**3. 生产 Docker Compose — `infra/docker/docker-compose.production.yml`**

override 文件，与基础 `docker-compose.yml` 配合使用：

```yaml
# 使用方式: docker compose -f docker-compose.yml -f infra/docker/docker-compose.production.yml up -d
```

内容：
- 去掉所有调试端口（仅暴露 80/443）
- 添加 `nginx` 服务
- 资源限制：每个服务 `mem_limit` + `cpus`
- 日志限制：`max-size: 50m`, `max-file: 5`
- 健康检查间隔调整为生产值
- `restart: always`（生产级）

推荐资源分配：

| 服务 | CPU | 内存 | 说明 |
|------|-----|------|------|
| api | 1.0 | 1GB | 主 API 服务 |
| web | 0.5 | 512MB | Next.js SSR |
| ingestion-worker | 1.0 | 1GB | PDF/OCR 解析较重 |
| pipeline-worker | 0.5 | 512MB | 流水线调度 |
| ai-orchestrator | 0.5 | 512MB | LLM 调用（IO 密集） |
| postgres | 2.0 | 2GB | 数据库 |
| redis | 0.5 | 512MB | 缓存/队列 |
| minio | 0.5 | 512MB | 文件存储 |
| nginx | 0.25 | 256MB | 反向代理 |

**4. 备份脚本 — `infra/scripts/`**

```
infra/scripts/
├── backup-db.sh              # PostgreSQL pg_dump + 压缩 + 保留 7 天
├── backup-minio.sh           # MinIO mc mirror 到备份目录
├── restore-db.sh             # 从备份恢复 PostgreSQL
└── crontab.example           # 建议的定时任务配置
```

crontab 建议：
```cron
# 每日 3:00 备份数据库
0 3 * * * /opt/kb-platform/infra/scripts/backup-db.sh
# 每日 4:00 备份 MinIO
0 4 * * * /opt/kb-platform/infra/scripts/backup-minio.sh
```

**5. 监控集成 — `infra/monitoring/`**

```
infra/monitoring/
├── docker-compose.monitoring.yml    # Prometheus + Grafana 服务
├── prometheus/
│   └── prometheus.yml               # 采集配置（api /metrics 端点）
└── grafana/
    └── dashboards/
        └── kb-platform.json         # 预置仪表盘
```

预置仪表盘面板：
- API 请求速率 / 错误率 / P95 延迟
- Worker 任务成功率 / 队列深度
- 数据库连接数 / 查询延迟
- Redis 内存使用 / 命中率
- MinIO 存储用量
- 系统 CPU / 内存 / 磁盘

**6. 部署一键脚本 — `infra/scripts/deploy.sh`**

```bash
#!/bin/bash
# 一键部署脚本（含前置检查）
# 1. 检查 .env.production 是否存在
# 2. 检查 Docker / Docker Compose 版本
# 3. 检查端口 80/443 是否可用
# 4. 拉取镜像 / 构建镜像
# 5. 执行 Alembic 迁移
# 6. 启动所有服务
# 7. 等待健康检查通过
# 8. 输出访问地址
```

#### 验收标准

1. `docker compose -f ... up -d` 一键启动全部服务
2. Nginx HTTPS 终端正常工作
3. WebSocket `/ws/` 通过 Nginx 代理正常
4. 备份脚本可成功生成备份文件
5. Grafana 仪表盘可显示实时数据

#### 原子级拆解（7 个子任务）

**T-42-08-A: Nginx 主配置 + 站点配置** — 新增 `infra/nginx/` 配置文件（~80 行）
**T-42-08-B: HTTPS 证书方案** — 新增自签脚本 + README（~40 行）
**T-42-08-C: 生产 Docker Compose** — 新增 `docker-compose.production.yml`（~80 行）
**T-42-08-D: 备份脚本** — 新增 backup-db/minio/restore-db + crontab（~100 行）
**T-42-08-E: Prometheus + Grafana** — 新增 monitoring compose + config + dashboard（~150 行）
**T-42-08-F: 部署一键脚本** — 新增 `deploy.sh`，前置检查+构建+迁移+启动（~60 行）
**T-42-08-G: T-42-08 收尾** — VERSION → 0.42.8

---

### T-42-09: 发布就绪 — 邮件骨架 + 生产配置 + 用户引导 + 运维文档

**任务版本号**: v0.42.9
**优先级**: P2
**预估工时**: 12h

#### 子任务清单

**1. 邮件通知骨架**

- 新增 `services/api/app/services/email_service.py`
- 接口：`send_reset_email()`, `send_review_notification()`, `send_welcome_email()`
- 开发模式：写日志不发邮件
- 生产模式：支持 SMTP 配置
- settings.py 添加 SMTP 相关配置项：

```python
# SMTP
smtp_host: str = ""
smtp_port: int = 587
smtp_user: str = ""
smtp_password: str = ""
smtp_from: str = "noreply@kb-platform.com"
smtp_tls: bool = True
```

**2. 生产配置模板 — `.env.production.example`**

```ini
# ============================================================
# KB Platform 生产环境配置模板
# 使用方式: cp .env.production.example .env.production
# ============================================================

# --- 环境 ---
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# --- 安全（必填，请使用强随机值）---
JWT_SECRET=               # 必须 >= 32 字符。生成: openssl rand -base64 48
ENCRYPTION_KEY=           # 必须 >= 32 字符。生成: openssl rand -base64 32
POSTGRES_PASSWORD=        # 生成: openssl rand -base64 24
REDIS_PASSWORD=           # 生成: openssl rand -base64 24
MINIO_ROOT_USER=          # 非 minioadmin
MINIO_ROOT_PASSWORD=      # 生成: openssl rand -base64 24

# --- 存储 ---
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=            # 同 MINIO_ROOT_USER
S3_SECRET_KEY=            # 同 MINIO_ROOT_PASSWORD
S3_BUCKET=kb-assets

# --- 网络 ---
CORS_ORIGINS=https://your-domain.com
APP_PORT=8080
WEB_PORT=3000

# --- LLM（至少填一个）---
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# --- 邮件（可选）---
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@your-domain.com

# --- 限流 ---
RATE_LIMIT_PER_MINUTE=100
UPLOAD_RATE_LIMIT_PER_MINUTE=20
AUTH_LOGIN_RATE_LIMIT=10
MAX_UPLOAD_SIZE_MB=100
```

**3. 健康检查增强（在已有端点基础上扩展）**

> **注意**: `/healthz`（轻量存活检查）、`/readyz`（DB SELECT 1）、`/api/health/ready`（深度检查 DB+Redis+MinIO 含延迟指标）、`/metrics`（Prometheus）均已存在。不重复创建，仅增量扩展。

- `/readyz` 增加 Alembic 迁移版本检查（在已有 DB check 基础上追加）
- 新增 `/_version` 端点返回 VERSION 文件内容（此端点确实不存在）
- 不改动已有的 `/healthz`、`/api/health/ready`、`/metrics` 逻辑

**4. 首次使用引导**

- 登录后检测是否有项目，无项目时显示引导卡片
- 引导步骤：创建项目 → 上传资料 → 查看架构 → 浏览 Wiki
- 纯前端实现，localStorage 记录是否已完成引导

**5. 运维文档**

| 文档 | 路径 | 内容 |
|------|------|------|
| 部署指南 | `docs/operations/deploy-guide.md` | 从零部署完整步骤 |
| 运维手册 | `docs/operations/runbook.md` | 常见问题处理 SOP |
| 升级指南 | `docs/operations/upgrade-guide.md` | 版本升级步骤 |

#### 验收标准

1. 邮件服务在 dev 模式下输出日志
2. `.env.production.example` 包含所有必需项
3. `/readyz` 增加 Alembic 版本检查 + `/_version` 返回版本号
4. 新用户首次登录看到引导
5. 三份运维文档完成

#### 原子级拆解（8 个子任务）

**T-42-09-A: 邮件服务骨架** — 新增 `email_service.py` + settings SMTP 配置（~60 行）
**T-42-09-B: 生产配置模板** — 新增 `.env.production.example`（~40 行）
**T-42-09-C: 健康检查增强（增量扩展）** — 修改 `health.py`，/readyz 增加 Alembic 检查 + 新增 /_version（~20 行，不改已有端点）
**T-42-09-D: 首次使用引导** — 新增 `onboarding-guide.tsx` + 修改 projects/page（~50 行）
**T-42-09-E: 部署指南文档** — 新增 `docs/operations/deploy-guide.md`（~100 行）
**T-42-09-F: 运维手册文档** — 新增 `docs/operations/runbook.md`（~80 行）
**T-42-09-G: 升级指南文档** — 新增 `docs/operations/upgrade-guide.md`（~50 行）
**T-42-09-H: T-42-09 收尾** — VERSION → 0.42.9

---

### T-42-10: 上线验收 — 全量回归测试 + 上线清单逐项确认

**任务版本号**: v0.42.10
**优先级**: P0（所有任务完成后执行）
**预估工时**: 8h

#### 目标

逐项确认上线代办清单，确保全部通过后方可上线。

#### 执行内容

按照下方第十二章"上线代办清单"逐项检查，全部 `[x]` 后标记为上线就绪。

---


### T-42-11: 审计补充修复一 — 安全与性能

**任务版本号**: v0.42.11
**优先级**: P1
**预估工时**: 10h
**依赖**: T-42-02

> 覆盖审计项：H-03、H-04、M-06、M-07

#### 子任务清单

| 编号 | 原审计编号 | 问题 | 修改文件 | 修改内容 |
|------|-----------|------|---------|---------|
| 11-A | H-03 | WebSocket JWT 通过 URL query 传递 | `services/api/app/routers/ws.py` + 前端 WebSocket 连接代码 | 改为从 httpOnly cookie 中读取 JWT，移除 URL query token 传递方式 |
| 11-B | H-04 | Embedding JSONB 回退 N+1 + 内存 | `services/api/app/services/embedding_service.py` | 回退路径改为批量查询（batch fetch），限制内存中持有的 embedding 数量上限 |
| 11-C | M-06 | Settings 每次 new 实例 | `packages/shared-config/shared_config/settings.py` | `get_settings()` 添加 `@lru_cache()` 或模块级单例 |
| 11-D | M-07 | Export 无 rate limit | `services/api/app/routers/export.py` | 添加 rate limit 装饰器 |

#### 原子级拆解

**T-42-11-A: WebSocket JWT 改用 Cookie 传递（H-03）**
- 改动文件：`services/api/app/routers/ws.py`
- 改动内容：WebSocket 握手时从 request.cookies 读取 access_token，移除 `token` query 参数
- 改动量：~15 行修改
- 验收标准：
  - [ ] WebSocket 连接不再需要 `?token=xxx` URL 参数
  - [ ] WebSocket 从 cookie 中正确读取 JWT 并验证
  - [ ] 浏览器访问日志中不出现 JWT token

**T-42-11-A2: 前端 WebSocket 连接适配**
- 改动文件：前端 WebSocket 连接代码
- 改动内容：移除 URL 中拼接 token 的逻辑，依赖 cookie 自动携带
- 改动量：~5 行修改
- 验收标准：
  - [ ] 前端 WebSocket 连接 URL 不再包含 token
  - [ ] WebSocket 通信正常

**T-42-11-B: Embedding JSONB 回退批量查询（H-04）**
- 改动文件：`services/api/app/services/embedding_service.py`
- 改动内容：逐条查询改为 `SELECT ... WHERE doc_id IN (...)` 批量查询；限制单次返回量
- 改动量：~20 行修改
- 验收标准：
  - [ ] 100 个文档的 embedding 查询从 N+1 次变为 1-2 次 SQL
  - [ ] 内存使用不超过 500MB
  - [ ] 已有 embedding 测试通过

**T-42-11-C: Settings 单例缓存（M-06）**
- 改动文件：`packages/shared-config/shared_config/settings.py`
- 改动内容：`get_settings()` 添加 `@lru_cache()` 装饰器
- 改动量：~3 行修改
- 验收标准：
  - [ ] 多次调用 `get_settings()` 返回同一实例
  - [ ] 环境变量修改后重启服务仍能生效

**T-42-11-D: Export 端点 Rate Limit（M-07）**
- 改动文件：`services/api/app/routers/export.py`
- 改动内容：添加 rate limit（每用户每分钟 10 次导出请求）
- 改动量：~10 行修改
- 验收标准：
  - [ ] 同一用户 1 分钟内超过 10 次导出请求 → 429
  - [ ] 不同用户互不影响

**T-42-11-E: T-42-11 收尾**
- 改动文件：`VERSION`（→ 0.42.11）、`CHANGELOG.md`、`TODO_NEXT.md`
- 验收标准：
  - [ ] 全部后端测试通过
  - [ ] VERSION = `0.42.11`

#### 验收标准

1. WebSocket 连接不再通过 URL 传递 JWT
2. Embedding 批量查询无 N+1
3. `get_settings()` 返回单例
4. Export 端点有频率限制

---

### T-42-12: 审计补充修复二 — 体验与稳定性

**任务版本号**: v0.42.12
**优先级**: P1
**预估工时**: 12h
**依赖**: T-42-03

> 覆盖审计项：M-02、M-10、M-12、M-14、M-15

#### 子任务清单

| 编号 | 原审计编号 | 问题 | 修改文件 | 修改内容 |
|------|-----------|------|---------|---------|
| 12-A | M-02 | 上传无前端类型/大小校验 | `apps/web/src/components/file-upload.tsx` | 添加文件类型白名单 + 大小预校验 |
| 12-B | M-10 | Celery 任务无幂等保护 | ingestion/pipeline worker tasks.py | 任务开始前检查 job 状态，已完成则跳过 |
| 12-C | M-12 | 列表页未包装 Error Boundary | dashboard 各列表页 | 用已有 `error-boundary.tsx`（v0.41.5）包装各列表页，不新建组件 |
| 12-D | M-14 | Alembic downgrade DROP TABLE | alembic versions | downgrade 改为 rename table 保留数据 |
| 12-E | M-15 | 邮箱全局唯一非租户级 | user.py + alembic 迁移 | 唯一约束改为 UNIQUE(email, tenant_id) |

#### 原子级拆解

**T-42-12-A: 前端上传类型/大小校验（M-02）**
- 改动文件：`apps/web/src/components/file-upload.tsx`
- 改动内容：
  - 文件类型白名单：`.pdf, .txt, .md, .docx, .zip, .csv, .json, .html, .xml`
  - 大小校验：`file.size` 超过 MAX_UPLOAD_SIZE_MB 时拒绝
  - 不支持的文件类型显示提示
- 改动量：~25 行修改
- 验收标准：
  - [ ] 选择 .exe 文件 → 提示"不支持的文件类型"
  - [ ] 选择 >100MB 文件 → 提示"文件大小超出限制"
  - [ ] 选择正常 PDF → 正常上传

**T-42-12-B: Celery 任务幂等性保护（M-10）**
- 改动文件：
  1. `services/ingestion-worker/worker/tasks.py`
  2. `services/pipeline-worker/worker/tasks.py`
- 改动内容：任务入口处检查 Job 记录 status，已 `completed`/`failed` 则跳过
- 改动量：~15 行修改
- 验收标准：
  - [ ] 同一 job_id 重复投递不会重复执行
  - [ ] 已完成的 job 被跳过时记录 warning 日志
  - [ ] 正常新任务不受影响

**T-42-12-C: Dashboard 列表页包装已有 ErrorBoundary（M-12）**

> **注意**: `error-boundary.tsx` 已在 v0.41.5 创建（含 class component + 错误提示 + 刷新按钮），不重复创建。

- 改动文件：`projects/page.tsx`、`assets/page.tsx`、`docs/page.tsx`、`jobs/page.tsx` 等列表页
- 改动内容：在列表页主内容外层包装已有的 `<ErrorBoundary>` 组件
- 改动量：每页 ~3 行修改（仅 import + 包装）
- 不修改已有的 `error-boundary.tsx` 组件
- 验收标准：
  - [ ] 列表页组件内部报错时显示友好错误提示（非白屏）
  - [ ] 错误提示包含"重新加载"按钮
  - [ ] 其他页面不受影响

**T-42-12-D: Alembic downgrade 数据保护（M-14）**
- 改动文件：`infra/sql/alembic/versions/` 下各迁移文件
- 改动内容：downgrade 中 `op.drop_table(...)` → `op.rename_table(..., ..._backup)`
- 改动量：每个迁移 ~5 行修改
- 验收标准：
  - [ ] `alembic downgrade` 不直接删除表
  - [ ] downgrade 后旧数据可在 backup 表中找到
  - [ ] `alembic upgrade` 仍然正常

**T-42-12-E: 邮箱唯一性租户隔离（M-15）**
- 新增文件：`infra/sql/alembic/versions/xxx_email_tenant_unique.py`
- 改动文件：`packages/shared-models/shared_models/user.py`
- 改动内容：移除 email 全局 UNIQUE → 添加 UNIQUE(email, tenant_id)
- 改动量：~25 行新增
- 验收标准：
  - [ ] 不同租户可使用相同邮箱注册
  - [ ] 同一租户内邮箱仍然唯一
  - [ ] 现有用户数据不受影响

**T-42-12-F: T-42-12 收尾**
- 改动文件：`VERSION`（→ 0.42.12）、`CHANGELOG.md`、`TODO_NEXT.md`
- 验收标准：
  - [ ] 前后端测试全部通过
  - [ ] VERSION = `0.42.12`

#### 验收标准

1. 上传不支持的文件类型或超大文件时前端拦截
2. Celery 重复投递不重复执行
3. 列表页报错不白屏
4. Alembic downgrade 不丢数据
5. 不同租户可用相同邮箱

---

## 第六章 数据库迁移计划

| 迁移 | 内容 | 任务 |
|------|------|------|
| 001 | 添加 `cross_references` 表 | T-42-07 |
| 002 | `knowledge_docs` 表添加 `keywords` JSONB 列和 `knowledge_type` 列 | T-42-06 |
| 003 | `doc_embeddings` 添加 `UNIQUE(doc_id)` 约束 | T-42-03 |
| 004 | `projects` 表添加 `profile_embedding` 和 `profile_keywords` 列 | T-42-07 |
| 005 | `users` 表邮箱唯一约束改为 UNIQUE(email, tenant_id) | T-42-12 |

---

## 第七章 不做清单（Explicit Not-Doing）

1. 完整邮件模板（仅做骨架，具体模板 v0.43）
2. 文件在线预览（v0.43）
3. 知识图谱可视化（v0.43）
4. 对话式多轮问答（v0.43）
5. SSO/OAuth（v0.43+）
6. 规则路由引擎（v0.43）
7. API v2（不做）
8. 暗黑模式（不做）

---

## 第八章 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| CSRF 方案选型争议 | 中 | 中 | 优先用 custom header，SameSite=strict 作为 plan B |
| 跨库索引 embedding 性能 | 中 | 中 | 限制 auto-suggest 为异步任务，前端显示"计算中" |
| Wiki 改造工作量超预期 | 高 | 中 | 先做最小可用版（左导航 + 正文），TOC 和相关推荐可延后 |
| 生产配置不同环境差异大 | 低 | 高 | 提供 .env.production.example + 部署文档 |
| Nginx 配置不当导致安全问题 | 中 | 高 | 提供模板 + 安全头检查脚本 |

---

## 第九章 建议但不在本版本

- LLM 调用成本追踪面板
- 前端 E2E 测试（Playwright）
- 批量操作前端 UI
- 知识库权限继承（项目级 → 文档级）
- API Rate Limit 自定义配置面板
- Kubernetes 部署 Helm Chart

---

## 第十章 验收标准（版本级）

v0.42 整体完成时，必须满足：

1. **0 个 CRITICAL 问题**（全部修复）
2. **0 个 HIGH 安全问题**（全部修复或有明确缓解）
3. **Wiki 呈现可用**（用户能像浏览维基一样阅读知识）
4. **知识管理方法论可运行**（首建 MECE、增量五分类、多库路由、跨库引用）
5. **部署工具链完整**（Nginx + HTTPS + 生产 Compose + 备份 + 监控）
6. **生产配置模板完整**（`.env.production.example`）
7. **健康检查通过**（/healthz 检查全部依赖）
8. **新用户引导存在**（首次登录有引导）
9. **运维文档齐全**（部署指南 + 运维手册 + 升级指南）
10. **上线代办清单全部通过**（第十二章所有项打勾）
11. **0 个 MEDIUM 安全/体验问题**（审计 28 项全部修复或缓解）
12. **WebSocket 不泄露 JWT**（T-42-11 H-03 修复）
13. **列表页健壮**（Error Boundary 保护，不白屏）

---

## 第十一章 LLM Prompt 设计要点（附录）

### A. 反幻觉约束（所有 prompt 必须包含）

```
严禁编造不在原始资料中的信息。
每一个事实性陈述必须附带来源标注 [来源N]。
如果原始资料中信息不足以回答某个问题，明确标注"信息不足"。
如果原始资料中存在矛盾，保留双方并标注"存在争议"。
```

### B. MECE 架构 prompt 增强

```
请为以下知识内容设计架构树。要求：
1. 声明你选择的分类维度（按主题/按流程/按受众/混合）并解释原因
2. 确保节点满足 MECE 原则：
   - 互斥：任何一个知识 chunk 的主归位唯一
   - 穷举：所有 chunk 都能归入某个节点
3. 如果有无法归类的内容，列出并解释原因
4. 架构深度不超过 5 层，每层 3-7 个节点
5. 输出覆盖度评分（0-100%）
```

### C. 增量分类 prompt 增强

```
已有架构树如下：{architecture}
已有文档摘要如下：{existing_docs_summary}
新资料内容如下：{new_chunks}

请判断每个新 chunk 属于以下哪种分类：
- NEW：全新主题，现有架构中无对应
- SUPPLEMENT：对已有文档的补充
- CORRECTION：对已有文档的修正/更新
- CONFLICT：与已有文档存在无法调和的矛盾
- RESTRUCTURE：暗示现有架构需要调整

对每个 chunk 输出：分类、目标节点/文档、置信度、理由
```

---

## 第十二章 上线代办清单

> 每完成一项，将 `[ ]` 改为 `[x]`。全部打勾后方可上线。

### 12.1 代码质量与安全

**CRITICAL 修复**：
- [ ] C-01: forgot-password 页面语法错误已修复
- [ ] C-02: 注册成功后跳转到 /login 并显示成功提示
- [ ] C-03: Dashboard 认证守卫已修复
- [ ] C-04: 生产环境不返回 reset_token
- [ ] H-06: QA 服务 decrypt 调用修复

**安全加固**：
- [ ] SSRF 防护生效
- [ ] CSRF 防护生效
- [ ] MinIO 凭证参数化
- [ ] Redis 密码保护
- [ ] 账户锁定生效
- [ ] Embedding 原子 upsert
- [ ] ZIP bomb 防护
- [ ] Docker 端口收紧
- [ ] Crypto salt 随机化
- [ ] WebSocket JWT 改用 Cookie 传递（H-03）
- [ ] Embedding 批量查询无 N+1（H-04）
- [ ] Settings 单例缓存生效（M-06）
- [ ] Export 端点有 rate limit（M-07）
- [ ] 前端上传有类型/大小校验（M-02）
- [ ] Celery 任务幂等保护（M-10）
- [ ] 邮箱唯一性为租户级（M-15）

**代码审查**：
- [ ] 所有 commit 已审查
- [ ] 无 TODO(SECURITY) 残留
- [ ] 无硬编码密码/密钥
- [ ] 无 console.log 泄露敏感数据
- [ ] 依赖无高危漏洞（`npm audit` + `pip audit`）

### 12.2 功能完整性

**核心流程**：
- [ ] 注册 → 登录 → 创建项目 → 上传 → 解析
- [ ] 架构审核 → 文档生成 → Wiki 浏览
- [ ] 搜索（关键词 + 语义 + AI 问答）
- [ ] 文档编辑 → diff
- [ ] 导出 Markdown / ZIP
- [ ] 忘记密码 → 重置（dev 模式）
- [ ] 管理员邀请用户 → 新用户登录

**新功能**：
- [ ] Wiki 布局正常
- [ ] 面包屑 + TOC 正常
- [ ] 搜索分页正常
- [ ] QA 流式响应正常
- [ ] 跨库引用 CRUD 正常
- [ ] 新用户引导正常
- [ ] 列表页 Error Boundary 生效（M-12）
- [ ] QA 回答 Markdown 渲染正常（M-13）
- [ ] Alembic downgrade 不丢数据（M-14）

**兼容性**：
- [ ] Chrome / Firefox / Safari 最新版
- [ ] iOS Safari + Android Chrome

### 12.3 基础设施

**生产配置**：
- [ ] `.env.production` 所有必填项已填写
- [ ] ENVIRONMENT=production
- [ ] JWT_SECRET >= 32 字符随机串
- [ ] ENCRYPTION_KEY >= 32 字符随机串
- [ ] POSTGRES_PASSWORD 非默认值
- [ ] REDIS_PASSWORD 已设置
- [ ] MINIO_ROOT_USER/PASSWORD 非默认值
- [ ] CORS_ORIGINS 仅允许生产域名
- [ ] OPENAI_API_KEY 或 ANTHROPIC_API_KEY 已配置

**数据库**：
- [ ] PostgreSQL 16 + pgvector 已安装
- [ ] Alembic 迁移全部成功
- [ ] 每日自动备份已配置
- [ ] 连接池 min=5, max=20

**Redis**：
- [ ] 密码已配置
- [ ] 内存上限 512MB
- [ ] 持久化已开启

**MinIO**：
- [ ] bucket `kb-assets` 已创建
- [ ] 备份策略已配置

**容器化**：
- [ ] `docker-compose.production.yml` 就绪
- [ ] 所有容器非 root 用户
- [ ] 资源限制已配置
- [ ] 日志大小限制

**网络**：
- [ ] Nginx 反向代理就绪
- [ ] HTTPS 证书已配置
- [ ] HTTP → HTTPS 重定向
- [ ] WebSocket 代理正常

### 12.4 监控与可观测性

- [ ] `/healthz` 返回 200（含深度检查）
- [ ] `/readyz` 返回 200
- [ ] Docker healthcheck 正确
- [ ] 外部监控已接入
- [ ] 日志 JSON 结构化 + 集中收集
- [ ] 敏感信息不记录
- [ ] Prometheus + Grafana 仪表盘就绪（建议）

### 12.5 数据安全

- [ ] 数据库每日备份 + 7 天保留
- [ ] MinIO 定期快照
- [ ] 备份恢复测试通过
- [ ] .env 在 .gitignore 中
- [ ] DB/Redis/MinIO 端口不对外暴露
- [ ] SSH 使用密钥认证

### 12.6 运维准备

- [ ] 部署文档完成 (`docs/operations/deploy-guide.md`)
- [ ] 运维手册完成 (`docs/operations/runbook.md`)
- [ ] OpenAPI 文档可访问
- [ ] 回滚脚本准备
- [ ] 回滚演练至少一次
- [ ] 上线时间窗口确定
- [ ] 上线操作人确定
- [ ] 回滚决策人确定

### 12.7 上线后 30 分钟巡检

- [ ] `/healthz` 返回 200
- [ ] 注册 / 登录 / 创建项目 / 上传 / 搜索 均正常
- [ ] WebSocket 连接正常
- [ ] 日志无 ERROR / CRITICAL
- [ ] CPU / 内存 < 70%
- [ ] Celery worker 活跃

### 12.8 上线后 7 天跟踪

- [ ] 收集用户反馈
- [ ] 监控错误率 / API P95 / Worker 成功率
- [ ] 评估是否需要 hotfix
- [ ] 规划 v0.43

---

## 第十三章 部署工具完整清单

v0.42 完成后，`infra/` 目录的最终结构：

```
infra/
├── docker/
│   ├── api.Dockerfile
│   ├── ingestion-worker.Dockerfile
│   ├── pipeline-worker.Dockerfile
│   ├── ai-orchestrator.Dockerfile
│   ├── web.Dockerfile
│   └── docker-compose.production.yml        # T-42-08 新增
│
├── nginx/                                    # T-42-08 新增
│   ├── nginx.conf
│   ├── conf.d/
│   │   └── kb-platform.conf
│   └── ssl/
│       └── generate-self-signed.sh
│
├── monitoring/                               # T-42-08 新增
│   ├── docker-compose.monitoring.yml
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       └── dashboards/
│           └── kb-platform.json
│
├── scripts/                                  # T-42-08 新增
│   ├── deploy.sh
│   ├── backup-db.sh
│   ├── backup-minio.sh
│   ├── restore-db.sh
│   └── crontab.example
│
└── sql/
    └── alembic/
        ├── env.py
        └── versions/
            ├── ... (现有迁移)
            ├── xxx_add_cross_references.py     # T-42-07
            ├── xxx_add_doc_keywords.py         # T-42-06
            ├── xxx_add_embedding_unique.py     # T-42-03
            ├── xxx_add_project_profile.py      # T-42-07
            └── xxx_email_tenant_unique.py      # T-42-12
```

---

## 第十四章 方法论演化路线图

| 阶段 | 版本 | 能力 |
|------|------|------|
| **基础** | v0.42 | MECE 架构 + 五分类增量 + 语义路由 + 跨库引用 + Wiki 呈现 |
| **质量** | v0.43 | 术语表 + 覆盖度仪表盘 + 文档生命周期 + 知识图谱可视化 + 文件预览 |
| **智能** | v0.44 | 自动废弃检测 + 多轮对话问答 + 知识推荐引擎 |
| **治理** | v0.45 | SLA 追踪 + 知识健康度评分 + 治理报告自动生成 |

---

## 第十五章 任务拆解统计总表

| 任务批次 | 任务名称 | 子任务数 | 预估工时 |
|---------|---------|---------|---------|
| T-42-01 | CRITICAL 修复 | 6 | 4h |
| T-42-02 | 安全加固一 | 8 | 12h |
| T-42-03 | 安全加固二 | 7 | 10h |
| T-42-04 | 搜索分页 + QA 流式 | 6 | 10h |
| T-42-05 | Wiki 呈现 | 12 | 16h |
| T-42-06 | 首建方法论 | 8 | 12h |
| T-42-07 | 增量 + 路由 + 索引 | 11 | 16h |
| T-42-08 | 部署工具链 | 7 | 16h |
| T-42-09 | 发布就绪 | 8 | 12h |
| T-42-10 | 上线验收 | 6 | 8h |
| T-42-11 | 审计补充一（安全性能） | 6 | 10h |
| T-42-12 | 审计补充二（体验稳定） | 6 | 12h |
| **合计** | **12 个任务** | **91 个子任务** | **138h（~18 工作日）** |

> 审计覆盖率：28/28（100%），含 4 CRITICAL + 9 HIGH + 15 MEDIUM 全部覆盖。
> 详细拆解文档：`docs/dev-plans/v0.42-task-breakdown.md`

---

## 第十六章 开发报告格式

每个 `vX.Y.Z` 任务完成后，按以下 9 项结构报告：

1. 计划 / 当前迭代目标（目标 + 最小闭环 + 排除范围）
2. 文件变更清单（路径 | 新增/修改/删除 | 职责描述）
3. 用户可见能力（用户现在可以做什么）
4. 真实场景验证（至少 5 个场景）
5. 开放问题（高/中/低优先级）
6. 收尾说明（是否闭环 + 残留风险）
7. 版本状态更新（VERSION / CHANGELOG / TODO_NEXT.md）
8. commit 信息
9. 是否继续下一个任务
