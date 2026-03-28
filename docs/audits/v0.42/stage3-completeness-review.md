# Stage 3 审计报告：完整性与体验 — v0.42

**审计日期**：2026-03-25
**项目类型**：全栈
**审计范围**：22 个前端变更文件，4 个 API 端点变更

## 发现统计
| 级别 | 数量 |
|------|------|
| Critical | 1 |
| Important | 4 |
| Minor | 5 |
| Observation | 3 |

---

## 发现详情

### C-001: Wiki 侧边栏和搜索页使用 GET 调用 POST-only 的搜索接口

- **级别**：Critical
- **检测项**：1 — 前后端对齐
- **文件**：
  - `apps/web/src/components/wiki-sidebar.tsx:206-207`
  - `apps/web/src/app/(dashboard)/projects/[id]/wiki/search/page.tsx:31-33`
  - `apps/web/src/app/(dashboard)/projects/[id]/wiki/[docId]/page.tsx:99-101`
  - `services/api/app/routers/search.py:83-94`
- **证据**：
  后端 hybrid search 只注册了 POST 方法：
  ```python
  # search.py:83-84
  @router.post(
      "/hybrid",
  ```
  但 3 处前端代码使用 GET 请求（带 query string 参数）：
  ```typescript
  // wiki-sidebar.tsx:206-207
  const resp = await api.get<SearchHit[]>(
    `/v1/search/hybrid?project_id=${projectId}&query=${encodeURIComponent(searchQuery)}&page_size=15`,
  );
  // wiki/search/page.tsx:31-33
  const resp = await api.get<SearchHit[]>(
    `/v1/search/hybrid?project_id=${projectId}&query=${encodeURIComponent(query)}&page_size=20`,
  );
  // wiki/[docId]/page.tsx:99-101
  const searchResp = await api.get<SearchHit[]>(
    `/v1/search/hybrid?project_id=${projectId}&query=...&page_size=6`,
  );
  ```
  仅 `projects/[id]/search/page.tsx:81` 正确使用了 `api.post`。
- **用户影响**：Wiki 侧边栏搜索、Wiki 搜索页、文档页的"相关知识"功能全部失效，后端返回 405 Method Not Allowed。Wiki 的核心搜索能力完全不可用。
- **修复建议**：将三处 `api.get` 改为 `api.post`，参数从 query string 移到 request body，与 `HybridSearchRequest` schema 对齐。

---

### I-001: TOC 滚动追踪绑定 window 而非实际滚动容器

- **级别**：Important
- **检测项**：2 — 端到端可用性
- **文件**：
  - `apps/web/src/components/wiki-toc.tsx:73-74`
  - `apps/web/src/components/wiki-layout.tsx:64`
- **证据**：
  ```typescript
  // wiki-toc.tsx:73
  window.addEventListener("scroll", handleScroll, { passive: true });
  ```
  ```tsx
  // wiki-layout.tsx:64
  <main className="flex-1 overflow-y-auto bg-white">
  ```
  内容区域使用 `overflow-y-auto`，滚动事件发生在 `<main>` 元素上而非 `window`。
- **用户影响**：TOC 目录高亮永远不会随用户滚动更新，点击 TOC 的 `scrollIntoView` 也可能失效，因为目标 heading 在嵌套滚动容器中。
- **修复建议**：WikiToc 接收实际滚动容器的 ref（即 `<main>` 元素），将 scroll 事件绑定到该元素而非 window。

---

### I-002: 搜索结果和 QA 来源链接跳出项目上下文

- **级别**：Important
- **检测项**：2 — 端到端可用性
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx:261,304,339`
- **证据**：
  ```tsx
  // search/page.tsx:261 (QA sources)
  href={`/docs/${src.doc_id}`}
  // search/page.tsx:304 (hybrid results)
  href={`/docs/${hit.doc_id}`}
  // search/page.tsx:339 (text results)
  href={`/docs/${hit.doc_id}`}
  ```
- **用户影响**：用户从项目搜索页点击结果后跳转到 `/docs/{id}` 独立文档页，脱离了项目上下文（失去侧边栏、Wiki 导航等），且返回时需要手动导航回项目。对比 Wiki 内部的链接使用 `/projects/{projectId}/wiki/{docId}` 格式，体验不一致。
- **修复建议**：改为 `href={/projects/${projectId}/wiki/${hit.doc_id}}`，保持用户在项目 Wiki 上下文中。

---

### I-003: 审核页文档链接同样跳出项目上下文

- **级别**：Important
- **检测项**：2 — 端到端可用性
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/review/page.tsx:286`
- **证据**：
  ```tsx
  // review/page.tsx:286
  <Link href={`/docs/${doc.id}`} className="font-medium text-primary-600 hover:underline">
  ```
- **用户影响**：与 I-002 相同，审核页点击文档标题后跳出项目上下文。
- **修复建议**：改为 `/projects/${projectId}/wiki/${doc.id}` 或 `/projects/${projectId}/docs/${doc.id}`。

---

### I-004: forgot-password 页面在生产环境泄露重置 token

- **级别**：Important
- **检测项**：7 — 新用户/老用户兼容
- **文件**：`apps/web/src/app/forgot-password/page.tsx:34,54-66`
- **证据**：
  ```tsx
  // forgot-password/page.tsx:34
  if (json.data?.reset_token) {
    setResetToken(json.data.reset_token);
  }
  // :54-66
  {resetToken && (
    <div className="mb-6 rounded-lg bg-yellow-50 p-3 text-sm">
      <p className="font-medium text-yellow-800">开发模式 — 重置 Token:</p>
      <p className="mt-1 break-all font-mono text-xs text-yellow-700">{resetToken}</p>
      <Link href={`/reset-password?token=${resetToken}`} ...>
  ```
  标注为"开发模式"但没有环境判断条件，在生产环境中如果后端返回了 token，前端将直接显示。
- **用户影响**：如果后端不小心在生产环境返回 reset_token，用户将在页面上看到令牌明文，存在安全风险。虽然后端应当负责不返回此字段，但前端缺少环境守卫是防线缺失。
- **修复建议**：添加 `process.env.NODE_ENV === "development"` 条件判断，或后端确保生产环境绝不返回 reset_token。

---

### M-001: Wiki 文档页缺少文档不存在（404）的专用提示

- **级别**：Minor
- **检测项**：4 — UX 状态完整性
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/wiki/[docId]/page.tsx:123`
- **证据**：
  ```tsx
  if (error || !doc) return <div className="py-12 text-center text-red-500">{error}</div>;
  ```
  当 `!doc && !error` 时（即 API 返回成功但 data 为 null），用户看到空白的红色文字区域，没有任何提示文字。
- **用户影响**：用户访问已删除或不存在的文档时看到空白红色区域，不理解发生了什么。
- **修复建议**：`{error || "文档不存在"}`。

---

### M-002: 搜索页 QA 模式下 "no results" 判断可能误触发

- **级别**：Minor
- **检测项**：4 — UX 状态完整性
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx:362-366`
- **证据**：
  ```tsx
  {searched && total === 0 && !searching && (
    <div className="py-8 text-center text-gray-400">
      {mode === "qa" ? "AI 暂时无法回答..." : "没有找到匹配的结果"}
    </div>
  )}
  ```
  QA 模式下 `total` 初始为 0，直到 SSE `sources` 事件到达后才更新。如果 AI 回答了但没有返回 sources（`total` 保持 0），同时 `streaming` 已结束（`!searching` 为 true），则"AI 暂时无法回答"消息会显示在已生成的回答下方。
- **用户影响**：AI 成功回答后，页面底部仍显示"AI 暂时无法回答"提示，造成困惑。
- **修复建议**：QA 模式的空结果判断应同时检查 `qaAnswer?.answer` 是否为空。

---

### M-003: OnboardingGuide 步骤 2-4 在无 projectId 时链接指向 "#"

- **级别**：Minor
- **检测项**：7 — 新用户/老用户兼容
- **文件**：`apps/web/src/components/onboarding-guide.tsx:50-51`
- **证据**：
  ```tsx
  const href = typeof step.href === "function"
    ? projectId ? step.href(projectId) : "#"
    : step.href;
  ```
  引导组件仅在 `projects.length === 0` 时显示（`projects/page.tsx:45`），此时 `projectId` 为 undefined。步骤 2/3/4 的链接全部为 `#`。
- **用户影响**：新用户看到引导卡片，点击"上传资料"、"查看架构"、"浏览 Wiki" 三个步骤没有任何反应，只有"创建项目"可点击。
- **修复建议**：步骤 2-4 在无 projectId 时显示为禁用状态并添加提示"请先创建项目"，或调整引导逻辑在创建项目后自动填充 projectId。

---

### M-004: file-upload 组件 handleFiles 存在闭包陷阱

- **级别**：Minor
- **检测项**：2 — 端到端可用性
- **文件**：`apps/web/src/components/file-upload.tsx:100`
- **证据**：
  ```tsx
  const startIndex = items.length;  // captures stale items.length
  for (let i = 0; i < newItems.length; i++) {
    if (newItems[i].status === "error") continue;
    await uploadFile(newItems[i].file, startIndex + i);
  }
  ```
  `handleFiles` 的依赖数组包含 `items.length`（第 107 行），但 `startIndex` 使用的是闭包中的 `items.length`。如果用户快速连续选择两批文件，第二批的 `startIndex` 可能不正确，导致进度更新到错误的条目。
- **用户影响**：快速连续上传两批文件时，第二批文件的进度条可能显示在第一批文件的条目上。
- **修复建议**：使用 `useRef` 存储当前 items 长度，或使用 functional state update 获取最新 length。

---

### M-005: 注册页密码强度规则与实际校验不匹配

- **级别**：Minor
- **检测项**：5 — 文案一致性
- **文件**：`apps/web/src/app/register/page.tsx:33-36,105`
- **证据**：
  ```tsx
  // :33 — 校验规则
  if (!/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
    setLocalError("密码需包含大写字母和数字");
  }
  // :105 — placeholder
  placeholder="至少 8 位，含大写字母和数字"
  ```
  校验不要求小写字母或特殊字符，但也不检查连续字符或常见弱密码。登录页（`login/page.tsx:25-28`）只检查 `password.length < 8`，没有大写字母/数字要求。
- **用户影响**：不会阻塞注册流程，但如果后端有更严格的密码策略，前端校验可能让用户误以为密码已满足要求。前后端密码规则应明确对齐。
- **修复建议**：确认后端密码策略，确保前端校验完全匹配。

---

### O-001: 项目详情页 Quick Stats 大部分显示硬编码的 "—"

- **级别**：Observation
- **检测项**：4 — UX 状态完整性
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/page.tsx:90-97`
- **证据**：
  ```tsx
  { label: "文档", count: "—", href: `/projects/${projectId}/docs` },
  { label: "架构", count: "—", href: `/projects/${projectId}/architectures` },
  { label: "任务", count: "—", href: `/projects/${projectId}/jobs` },
  // ... 5 of 8 cards show "—"
  ```
- **用户影响**：用户看到 8 个统计卡片中有 7 个显示"—"，给人"功能不完整"的印象。
- **修复建议**：后续版本中接入实际数据或移除暂不支持的统计卡片。

---

### O-002: 审核页客户端过滤而非服务端过滤

- **级别**：Observation
- **检测项**：2 — 端到端可用性
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/review/page.tsx:111-117`
- **证据**：
  ```tsx
  const endpoint = tab === "reviewing"
    ? `/v1/docs?project_id=${projectId}&page_size=50`
    : `/v1/docs?project_id=${projectId}&page_size=50`;
  const resp = await api.get<Doc[]>(endpoint);
  const filtered = resp.data.filter((d) => d.status === tab);
  ```
  两个 tab 的 endpoint 完全相同（没有 status 过滤参数），然后在客户端按 status 过滤。
- **用户影响**：当项目文档超过 50 篇时，部分 "reviewing" 或 "draft" 状态的文档可能不在前 50 条结果中，导致用户看不到完整的待审核/草稿列表。
- **修复建议**：后端 `/v1/docs` 添加 `status` 查询参数，或前端确认后端已支持此参数并传入。

---

### O-003: Wiki TOC 仅提取 h2/h3，忽略 h1

- **级别**：Observation
- **检测项**：3 — UI 规范合规
- **文件**：`apps/web/src/components/wiki-toc.tsx:26`
- **证据**：
  ```tsx
  const headings = el.querySelectorAll("h2, h3");
  ```
- **用户影响**：如果文档 Markdown 内容使用了 `#` (h1) 作为章节标题，这些章节不会出现在 TOC 中。这在大多数 Wiki 系统中是合理的（h1 作为文档标题），但如果作者在正文中使用了 h1，TOC 会缺少顶级节点。
- **修复建议**：考虑是否需要支持 h1，或在 MarkdownView 组件中将所有 heading 降一级。

---

## 审计结论

- **Stage 3 通过/未通过**：**未通过**（存在 1 个 Critical 发现）

- **端到端流程完整性**：

  | 流程 | 状态 | 说明 |
  |------|------|------|
  | 注册 -> 登录 -> 项目列表 | 完整 | 注册后正确跳转登录页并显示成功提示 |
  | 登录 -> 创建项目 -> 项目详情 | 完整 | 表单校验、loading、error 状态齐全 |
  | 忘记密码 -> 重置 | 完整 | 端到端可用但有 I-004 安全隐患 |
  | Wiki 三栏布局 + 导航树 | 完整 | 布局响应式处理到位，移动端有侧滑导航 |
  | Wiki 侧边栏搜索 | **不完整** | C-001: GET 调用 POST 接口，405 报错 |
  | Wiki 搜索页 | **不完整** | C-001: 同上 |
  | Wiki 文档页"相关知识" | **不完整** | C-001: 同上 |
  | Wiki TOC 高亮滚动追踪 | **不完整** | I-001: 绑定 window 而非实际滚动容器 |
  | 项目搜索（hybrid/text/QA） | 部分完整 | hybrid 和 text 搜索正常，QA 流式正常，但结果链接跳出上下文 (I-002) |
  | 文档审核（批量通过/驳回） | 完整 | 多选、批量操作、驳回弹窗齐全 |
  | 文件上传 | 完整 | 拖拽、进度条、取消、校验齐全 |
  | 跨库引用 + 关联文档 | 完整 | 前端已适配 CrossRef 数据结构和跨项目链接 |
  | WebSocket 任务推送 | 完整 | JWT cookie 认证 + 租户隔离 |
  | 新用户引导 | 部分完整 | M-003: 3/4 步骤链接为 "#" |

- **前后端对齐状态**：**存在 1 个未对齐 API**
  - `/v1/search/hybrid`: 后端 POST，前端 3 处使用 GET（Wiki 相关组件）
  - `/v1/cross-refs/doc/{doc_id}`: 前后端对齐 (ListResponse -> array)
  - `/v1/qa/ask`: 前后端对齐 (SSE streaming)
  - `/v1/projects/*`: 前后端对齐
  - `/v1/ws/jobs/{project_id}`: 前后端对齐 (WebSocket + cookie auth)
