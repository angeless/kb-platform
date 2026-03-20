# KB Platform 编码标准 — 错误处理

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**优先级**：必读（所有任务）

---

## 1. 异常体系

KB Platform 使用 `packages/shared-errors/` 统一的异常层级：

```
AppError (base)
├── ValidationError       # 输入校验失败 (400)
├── AuthenticationError   # 认证失败 (401)
├── AuthorizationError    # 权限不足 (403)
├── NotFoundError         # 资源不存在 (404)
├── ConflictError         # 资源冲突 (409)
├── RateLimitError        # 限流 (429)
├── ExternalServiceError  # 外部服务异常 (502)
└── InternalError         # 内部错误 (500)
```

### 1.1 规则

- 所有业务异常必须使用 `shared_errors` 中定义的异常类
- 每个异常必须携带 `error_code`（来自 `shared_errors.codes`）
- 禁止在业务代码中直接 `raise HTTPException`——用 `AppError` 子类代替
- 异常处理器通过 `register_exception_handlers(app)` 统一注册到 FastAPI app

---

## 2. HTTP 错误响应格式

所有 API 错误响应必须遵循以下 JSON 结构：

```json
{
  "error_code": "KNOWLEDGE_UNIT_NOT_FOUND",
  "message": "Knowledge unit does not exist",
  "detail": "No knowledge unit found with id=abc-123 in tenant=tenant-1"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `error_code` | 是 | 来自 `shared_errors.codes` 的枚举值 |
| `message` | 是 | 面向用户的错误描述 |
| `detail` | 否 | 面向开发者的额外信息（生产环境可隐藏） |

---

## 3. Python 后端错误处理规则

### 3.1 禁止裸捕获

```python
# 禁止 — 吞掉所有异常
try:
    do_something()
except:
    pass

# 禁止 — 捕获 Exception 但不处理
try:
    do_something()
except Exception:
    pass

# 正确 — 捕获具体异常，记录日志
try:
    do_something()
except IntegrityError as e:
    logger.error("Duplicate entry: %s", e)
    raise ConflictError(error_code="DUPLICATE_ENTRY", message="Resource already exists")
```

### 3.2 数据库异常

- 捕获 `IntegrityError`（唯一约束、外键约束）并转换为 `ConflictError` 或 `ValidationError`
- 捕获 `OperationalError`（连接超时、数据库宕机）并转换为 `InternalError`，同时记录 ERROR 级日志
- 禁止在 Router 层捕获数据库异常——由 Service 层处理

### 3.3 验证异常

- Pydantic 验证失败由 FastAPI 自动转换为 422 响应，无需手动处理
- 业务验证失败（如金额不能为负）使用 `ValidationError` 手动抛出

### 3.4 外部服务异常

- 调用 LLM（ai-orchestrator）、MinIO、Redis 等外部服务时，必须设置超时
- 超时和网络异常使用指数退避重试（最多 3 次）
- 重试耗尽后抛出 `ExternalServiceError`

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def call_llm(prompt: str) -> str:
    ...
```

---

## 4. Celery 任务错误处理

### 4.1 基本规则

- 每个 Celery 任务必须有 try/except 包裹核心逻辑
- 可重试的异常（网络超时、临时不可用）使用 `self.retry(exc=e, countdown=...)`
- 不可重试的异常（数据格式错误、权限问题）发送到 DLQ（`shared_config.dlq`）
- 必须设置 `max_retries` 和 `task_time_limit`

```python
from shared_config.dlq import send_to_dlq

@app.task(bind=True, max_retries=3, time_limit=300)
def parse_file(self, file_id: str):
    try:
        do_parse(file_id)
    except TransientError as e:
        self.retry(exc=e, countdown=2 ** self.request.retries)
    except PermanentError as e:
        logger.error("Permanent failure for file %s: %s", file_id, e)
        send_to_dlq(task_name="parse_file", payload={"file_id": file_id}, error=str(e))
```

---

## 5. 前端错误处理

### 5.1 React 组件错误

- 使用 `error-boundary.tsx` 包裹路由级组件，捕获渲染异常
- 错误边界展示用户友好的错误页面，并记录错误信息

### 5.2 API 调用错误

- 所有 API 调用通过 `lib/api.ts` 发起，统一拦截错误响应
- 根据 HTTP 状态码分类处理：
  - 401: 跳转登录页
  - 403: 展示权限不足提示
  - 404: 展示资源不存在
  - 422: 展示表单验证错误
  - 429: 展示限流提示，建议稍后重试
  - 500/502: 展示通用错误提示

### 5.3 前端禁令

- 禁止 `catch(e) {}` 空捕获
- 禁止在 `console.log` 中输出错误后不做任何处理
- 必须给用户可见的错误反馈（toast、错误页面、内联错误信息）
