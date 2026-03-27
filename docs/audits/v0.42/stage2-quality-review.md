# Stage 2 审计报告：质量工程 — v0.42

**审计日期**：2026-03-25
**审计范围**：46 个变更文件，5695 行新增代码，785 行删除代码
**审计基线**：372f1c7..8449e07（26 commits）

## 发现统计
| 级别 | 数量 |
|------|------|
| Critical | 0 |
| Important | 6 |
| Minor | 8 |
| Observation | 5 |

---

## 发现详情

### I-001: cross_ref_service.list_for_doc 存在 N+1 查询
- **级别**：Important
- **检测项**：#7 性能隐患
- **文件**：`services/api/app/services/cross_ref_service.py:59-63`
- **证据**：
  ```python
  for ref in refs:
      source_doc = await self.db.get(KnowledgeDoc, ref.source_doc_id)
      target_doc = await self.db.get(KnowledgeDoc, ref.target_doc_id)
      target_project = await self.db.get(Project, target_doc.project_id) if target_doc else None
  ```
- **违反规范**：每个 cross-reference 触发 2~3 次独立 DB 查询。若一个文档有 20 条交叉引用，将产生 40~60 次查询。
- **修复建议**：先收集所有 source_doc_id/target_doc_id，批量 `select(KnowledgeDoc).where(KnowledgeDoc.id.in_(all_ids))`，再从 map 中取值。

### I-002: cross_ref_service.auto_suggest 加载全量 embedding 到内存
- **级别**：Important
- **检测项**：#7 性能隐患
- **文件**：`services/api/app/services/cross_ref_service.py:130-141`
- **证据**：
  ```python
  all_embs = await self.db.execute(
      select(DocEmbedding).where(
          DocEmbedding.project_id.in_(
              select(KnowledgeDoc.project_id).where(
                  KnowledgeDoc.tenant_id == self.tenant_id
              )
          ),
          DocEmbedding.doc_id != doc_id,
      )
  )
  for emb in all_embs.scalars().all():
  ```
- **违反规范**：全量加载租户所有 embedding 向量（每个 1536 维 float），租户有 1000+ 文档时将消耗大量内存。循环内还有 `await self.db.get(KnowledgeDoc, emb.doc_id)` 造成额外 N+1。
- **修复建议**：1) 使用 pgvector 的 `<=>` 操作符做数据库端相似度过滤，2) 至少添加 `.limit(500)` 防止内存溢出（如 embedding_service 中的 `_semantic_search_jsonb_fallback` 已做的那样），3) 批量获取 doc 标题。

### I-003: _cosine_similarity 函数重复定义
- **级别**：Important
- **检测项**：#6 重复代码
- **文件**：`services/api/app/services/cross_ref_service.py:287-296` 和 `services/api/app/services/project_router_service.py:111-120`
- **证据**：
  ```python
  # cross_ref_service.py:287
  def _cosine_similarity(a: list, b: list) -> float:
      ...
  # project_router_service.py:111
  def _cosine_similarity(a: list, b: list) -> float:
      ...
  ```
  `embedding_service.py:183-187` 中还有第三份内联实现。
- **违反规范**：同一函数在 3 个文件中重复实现，未提取为共享工具。
- **修复建议**：提取至 `packages/shared-utils/` 或 `services/api/app/utils/math_utils.py`，统一引用。

### I-004: email_service.send_reset_email 存在 HTML 注入风险
- **级别**：Important
- **检测项**：#8 安全基线
- **文件**：`services/api/app/services/email_service.py:49-52`
- **证据**：
  ```python
  def send_reset_email(self, to: str, reset_link: str) -> None:
      self._send(
          to=to,
          subject="KB Platform — 重置密码",
          html_body=f'<p>点击以下链接重置密码：</p><p><a href="{reset_link}">{reset_link}</a></p>...',
      )
  ```
- **违反规范**：`reset_link` 直接拼接进 HTML，未做 HTML 转义。虽然 reset_link 由后端生成，但 `send_welcome_email` 中的 `username` 参数（第 45 行 `f"<h2>欢迎，{username}！</h2>"`）来自用户输入 `tenant_name`，存在 XSS/HTML 注入风险（邮件客户端渲染 HTML）。
- **修复建议**：对所有用户输入使用 `html.escape()` 后再插入 HTML 模板。

### I-005: qa_service 解密失败静默吞异常
- **级别**：Important
- **检测项**：#2 错误处理
- **文件**：`services/api/app/services/qa_service.py:163-171`
- **证据**：
  ```python
  try:
      from app.utils.crypto import decrypt
      from shared_config.settings import get_settings
      if isinstance(api_key, (bytes, memoryview)):
          api_key = decrypt(bytes(api_key), get_settings().encryption_key)
      elif isinstance(api_key, str) and api_key.startswith("KDF1"):
          api_key = decrypt(api_key.encode("latin-1"), get_settings().encryption_key)
  except Exception:
      pass
  ```
  同样的模式在 `_call_llm` (line 234-242) 中重复出现。
- **违反规范**：如果解密失败，会将加密后的密文直接作为 API key 发送到外部 LLM 服务，请求必然失败但错误信息不明确，增加调试难度。
- **修复建议**：至少添加 `logger.warning("Failed to decrypt API key: %s", e)` 以提供可追溯的错误日志。此外，解密逻辑重复 2 次，应提取为私有方法。

### I-006: projects.route_content 接受原始 dict 而非 Pydantic schema
- **级别**：Important
- **检测项**：#3 类型安全 / #8 安全基线
- **文件**：`services/api/app/routers/projects.py:155-171`
- **证据**：
  ```python
  async def route_content(
      body: dict,
      ...
  ):
      from app.services.project_router_service import ProjectRouterService
      svc = ProjectRouterService(db, tenant_id)
      exclude_id = body.get("exclude_project_id")
      candidates = await svc.route(
          content_embedding=body.get("embedding"),
          content_keywords=body.get("keywords"),
          exclude_project_id=uuid.UUID(exclude_id) if exclude_id else None,
      )
  ```
- **违反规范**：使用裸 `dict` 作为请求体类型，绕过了 FastAPI/Pydantic 的自动验证。`body.get("embedding")` 可以是任意类型，`uuid.UUID(exclude_id)` 可能因无效输入抛出未处理的 ValueError。其他所有路由均使用 Pydantic schema。
- **修复建议**：创建 `RouteContentRequest` schema（如 `shared_schemas.cross_reference.RoutingResult` 已定义了输出 schema，应补充对应的输入 schema）。

---

### M-001: cross_ref_service.auto_suggest 中 existing_links 只查 source 方向
- **级别**：Minor
- **检测项**：#1 命名与可读性 / 业务逻辑准确性
- **文件**：`services/api/app/services/cross_ref_service.py:100-106`
- **证据**：
  ```python
  existing_links = await self.db.execute(
      select(CrossReference.target_doc_id).where(
          CrossReference.source_doc_id == doc_id,
          CrossReference.tenant_id == self.tenant_id,
      )
  )
  linked_ids = {row[0] for row in existing_links.all()}
  ```
- **违反规范**：只排除了 doc 作为 source 的已有链接，未排除 doc 作为 target 的链接。如果 A->B 已存在，auto_suggest 仍会建议 B 作为 A 的目标（因为反向链接未被排除）。
- **修复建议**：同时查询 `CrossReference.target_doc_id == doc_id` 的 source_doc_id。

### M-002: WebSocket 路由中 Redis 连接未保证在异常路径关闭
- **级别**：Minor
- **检测项**：#7 性能隐患（资源泄漏）
- **文件**：`services/api/app/routers/ws.py:73-99`
- **证据**：
  ```python
  try:
      redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
      pubsub = redis_client.pubsub()
      await pubsub.subscribe(channel_name)
      ...
  finally:
      try:
          await pubsub.unsubscribe(channel_name)
          await redis_client.aclose()
      except Exception:
          pass
  ```
- **违反规范**：如果 `redis_client.pubsub()` 或 `pubsub.subscribe()` 抛出异常，`finally` 中引用 `pubsub` 或 `redis_client` 可能导致 `NameError`（变量未定义）。
- **修复建议**：在 `try` 块之前初始化 `redis_client = None` 和 `pubsub = None`，`finally` 中检查非 None 再关闭。

### M-003: CSRF 中间件豁免路径未使用前缀匹配
- **级别**：Minor
- **检测项**：#8 安全基线
- **文件**：`services/api/app/middleware/csrf.py:16-25`
- **证据**：
  ```python
  _EXEMPT_PATHS = {
      "/healthz",
      "/readyz",
      ...
  }
  ...
  if path not in _EXEMPT_PATHS:
  ```
- **违反规范**：使用精确匹配，`/healthz/` (带尾斜杠)、`/docs/oauth2-redirect` 等路径不在豁免列表中，可能导致合法请求被拒。`/v1/auth/login` 等 POST 路由也需要 CSRF 头（前端已设置 `X-Requested-With`），但第三方集成可能遗漏。
- **修复建议**：1) 使用 `path.rstrip("/")` 标准化后再匹配，或 2) 对 `/docs` `/redoc` 使用 `path.startswith()` 前缀匹配。

### M-004: url_validator.validate_import_url 使用同步 DNS 解析
- **级别**：Minor
- **检测项**：#7 性能隐患
- **文件**：`services/api/app/utils/url_validator.py:65-66`
- **证据**：
  ```python
  addrinfo = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
  ```
- **违反规范**：在 async FastAPI 应用中使用 `socket.getaddrinfo` 会阻塞事件循环。DNS 解析可能耗时数秒（慢 DNS 或超时场景）。
- **修复建议**：使用 `asyncio.get_event_loop().getaddrinfo()` 或 `loop.run_in_executor(None, socket.getaddrinfo, ...)`。

### M-005: cross_refs 路由 create_cross_ref 中对 body.source_doc_id 做了冗余的 uuid.UUID 转换
- **级别**：Minor
- **检测项**：#3 类型安全
- **文件**：`services/api/app/routers/cross_refs.py:38-39`
- **证据**：
  ```python
  ref = await svc.create(
      source_doc_id=uuid.UUID(body.source_doc_id),
      target_doc_id=uuid.UUID(body.target_doc_id),
  ```
- **违反规范**：`CrossRefCreate.source_doc_id` 类型为 `str`，但没有 UUID 格式验证。`uuid.UUID()` 转换可能在运行时抛出 ValueError 而不是在 Pydantic 验证阶段捕获。同时 `AutoSuggestRequest.doc_id` 也是 `str` 类型而非 `UUID`。
- **修复建议**：在 schema 中将 `source_doc_id`、`target_doc_id`、`doc_id` 字段类型改为 `UUID`，让 Pydantic 在请求验证阶段就捕获格式错误。

### M-006: file-upload 组件 handleFiles 中 items.length 作为 startIndex 在并发场景下可能不准确
- **级别**：Minor
- **检测项**：#7 性能隐患 / React 状态竞态
- **文件**：`apps/web/src/components/file-upload.tsx:100-104`
- **证据**：
  ```typescript
  const startIndex = items.length;
  for (let i = 0; i < newItems.length; i++) {
    if (newItems[i].status === "error") continue;
    await uploadFile(newItems[i].file, startIndex + i);
  }
  ```
- **违反规范**：`items.length` 在 `handleFiles` 被 `useCallback` 捕获时可能是过时的闭包值。如果用户快速拖入两批文件，第二批的 `startIndex` 可能与第一批重叠，导致 `updateItem` 更新错误的条目。
- **修复建议**：使用 `useRef` 追踪真实的 item 数量，或使用唯一 ID 而非数组 index 标识上传项。

### M-007: review/page.tsx 中相同 endpoint 被重复定义
- **级别**：Minor
- **检测项**：#6 重复代码
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/review/page.tsx:111-113`
- **证据**：
  ```typescript
  const endpoint = tab === "reviewing"
    ? `/v1/docs?project_id=${projectId}&page_size=50`
    : `/v1/docs?project_id=${projectId}&page_size=50`;
  ```
- **违反规范**：三元表达式两个分支完全相同，结果在客户端筛选。说明后端缺少 `status` 查询参数，或者条件表达式是未完成的 TODO。
- **修复建议**：后端 `/v1/docs` 应支持 `status` 查询参数实现服务端过滤，或至少去掉无意义的三元表达式。

### M-008: search/page.tsx 和 wiki doc page 中搜索结果链接路径不一致
- **级别**：Minor
- **检测项**：#1 命名与可读性
- **文件**：`apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx:263`, `304`, `339`
- **证据**：
  ```typescript
  // search/page.tsx 中引用来源和搜索结果使用:
  href={`/docs/${src.doc_id}`}
  href={`/docs/${hit.doc_id}`}

  // 而 wiki doc page 中使用:
  href={`/projects/${projectId}/wiki/${hit.doc_id}`}
  ```
- **违反规范**：搜索结果页使用 `/docs/{id}` 路径，而 Wiki 页面使用 `/projects/{pid}/wiki/{id}` 路径。`/docs/{id}` 路径在当前路由结构中可能不存在，会导致 404。
- **修复建议**：统一使用 `/projects/${projectId}/wiki/${docId}` 路径格式。

---

### O-001: auth_service._clear_login_attempts 中 except 块静默 pass
- **级别**：Observation
- **检测项**：#2 错误处理
- **文件**：`services/api/app/services/auth_service.py:126-127`
- **证据**：
  ```python
  except Exception:
      pass
  ```
- **说明**：清除登录计数器失败不影响业务流程（用户已成功登录），fail-open 设计合理。但建议至少保留 `logger.debug` 以便排查 Redis 连接问题。

### O-002: get_project_graph 中外部节点逐个查询
- **级别**：Observation
- **检测项**：#7 性能隐患
- **文件**：`services/api/app/services/cross_ref_service.py:262-272`
- **证据**：
  ```python
  for ext_id in external_ids:
      ext_doc = await self.db.get(KnowledgeDoc, ext_id)
      if ext_doc:
          ext_project = await self.db.get(Project, ext_doc.project_id)
  ```
- **说明**：与 I-001 类似的 N+1 模式。外部引用数量通常较少，影响有限，但应在文档量增长后重新评估。

### O-003: ingestion-worker 和 ai-orchestrator 中 _publish_job_event / _update_job_* 函数完全重复
- **级别**：Observation
- **检测项**：#6 重复代码
- **文件**：`services/ingestion-worker/worker/tasks.py:174-218` 和 `services/ai-orchestrator/orchestrator/tasks.py:634-678`
- **说明**：两个 worker 中的 Job 状态更新和 Redis 事件发布逻辑完全相同（约 45 行）。建议提取至 `packages/shared-models/` 或 `packages/shared-utils/` 中的共享模块。

### O-004: classify.py 中 _build_classification_from_chunks 使用位置分配而非 LLM 返回的 chunk_index
- **级别**：Observation
- **检测项**：#1 命名与可读性
- **文件**：`services/pipeline-worker/worker/stages/classify.py:75-101`
- **证据**：
  ```python
  def _build_classification_from_chunks(chunks: list[dict], response: dict) -> dict:
      new_count = response.get("new", 0)
      ...
      idx = 0
      for category, count in [("new", new_count), ...]:
          for _ in range(count):
              if idx < len(chunks):
                  result[category].append(chunks[idx]["chunk_id"])
                  idx += 1
  ```
- **说明**：orchestrator 的 `classify_incremental` 返回的是分类计数（`new=3, supplement=2`）而非逐 chunk 分类结果。此函数用计数做位置分配（前 3 个是 new，接下来 2 个是 supplement），这假设了 chunk 顺序与 LLM 分类顺序一致，实际上 LLM 可能以任意顺序分类。不过当前这是两个服务之间的约定，暂不影响功能正确性。

### O-005: 提交历史质量良好
- **级别**：Observation
- **检测项**：#10 提交质量
- **说明**：26 个 commits 遵循 conventional commit 格式（`feat/fix/docs/refactor`），按任务编号（T-42-01 至 T-42-12）有序推进，每个 commit 都是原子化的业务单元。安全修复（`fix(security)`）和审计修复（`fix(audit)`）与功能 commit 分离。

---

## 审计结论

- **Stage 2 通过/未通过**：**通过**（无 Critical 级别发现）
- **质量热点文件**：
  1. `services/api/app/services/cross_ref_service.py` — N+1 查询 + 全量内存加载 + 函数重复
  2. `services/api/app/services/qa_service.py` — 静默吞异常 + 解密逻辑重复
  3. `apps/web/src/app/(dashboard)/projects/[id]/search/page.tsx` — 链接路径不一致
- **主要质量风险**：`cross_ref_service` 的 auto_suggest 方法在大规模数据下存在内存和性能瓶颈，应在进入生产前优化为数据库端向量检索。
