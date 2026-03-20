# KB Platform 编码标准 — 数据持久化与外部调用

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**优先级**：条件必读（涉及 API 调用 / 数据库时）

---

## 1. 数据库操作（PostgreSQL + SQLAlchemy）

### 1.1 会话管理

- 使用 FastAPI 依赖注入获取异步数据库会话（`deps.py` 中的 `get_db_session`）
- 所有数据库操作在 Service 层执行，禁止在 Router 层直接操作
- 会话生命周期与请求绑定，请求结束自动关闭

```python
from ..deps import get_db_session

@router.get("/knowledge-units")
async def list_units(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    service = KnowledgeUnitService(session)
    return await service.list_by_tenant(current_user.tenant_id)
```

### 1.2 事务管理

- 使用 session 上下文管理器控制事务边界
- 单个 Service 方法内的多步操作应在同一事务中
- 显式 `await session.commit()` 提交，异常时自动回滚
- 批量操作使用 savepoint 实现部分失败容忍

```python
async def batch_create(self, items: list[CreateSchema]) -> list[Model]:
    results = []
    for item in items:
        async with self.session.begin_nested():  # savepoint
            obj = Model(**item.model_dump())
            self.session.add(obj)
            results.append(obj)
    await self.session.commit()
    return results
```

### 1.3 Schema 变更

- 所有数据库 schema 变更必须通过 Alembic 迁移
- 禁止手动执行 DDL 语句
- 迁移文件必须可回滚（实现 `upgrade()` 和 `downgrade()`）
- 每次迁移只做一件事

### 1.4 多租户查询

- 所有查询必须包含 `tenant_id` 过滤
- 在 Service 层方法签名中强制要求 `tenant_id` 参数
- 禁止使用不带条件的 `select(Model)` 全表查询

---

## 2. 缓存（Redis）

### 2.1 Key 命名

- 格式：`{tenant_id}:{domain}:{identifier}`
- 示例：`tenant-123:knowledge_unit:unit-456`
- 禁止使用无命名空间的裸 key

### 2.2 TTL

- 所有缓存必须设置显式 TTL，禁止永不过期的缓存
- 默认 TTL 根据数据类型设定（配置数据 1h，查询结果 5min，session 30min）
- 在 `shared_config` 中统一管理 TTL 配置

### 2.3 缓存失效

- 数据变更时主动清除相关缓存
- 使用 key pattern 批量清除同一资源的缓存

---

## 3. 文件存储（MinIO）

### 3.1 操作入口

- 所有 MinIO 操作通过 `utils/storage.py` 封装函数执行
- 禁止在业务代码中直接创建 MinIO client

### 3.2 文件路径

- 格式：`{tenant_id}/{domain}/{year}/{month}/{file_id}.{ext}`
- 示例：`tenant-123/uploads/2026/03/abc-def.pdf`

### 3.3 下载

- 使用 presigned URL 提供下载链接，URL 有效期 15 分钟
- 禁止在 API 响应中直接返回文件二进制内容（大文件场景）

---

## 4. LLM 调用（ai-orchestrator）

### 4.1 调用入口

- 所有 LLM 调用通过 `services/ai-orchestrator/` 的 `llm_client.py` 发起
- 禁止在其他服务中直接调用 LLM API

### 4.2 超时与重试

- 设置请求超时（默认 60 秒，可按场景配置）
- 使用指数退避重试（最多 3 次），仅对可重试错误（超时、5xx）重试
- 记录每次 LLM 调用的 token 用量和延迟

### 4.3 成本控制

- 输入 prompt 控制最大 token 数
- 记录每次调用的模型、token 数、费用，支持按租户统计

---

## 5. HTTP 外部调用

### 5.1 客户端

- 使用 `httpx.AsyncClient` 发起外部 HTTP 请求
- 设置连接超时（5s）和读取超时（30s）
- 使用连接池复用连接

### 5.2 重试策略

- 对 5xx 和连接超时使用指数退避重试（最多 3 次）
- 对 4xx 不重试（客户端错误）
- 记录所有外部调用的 URL、状态码、延迟

---

## 6. Celery 任务设计

### 6.1 幂等性

- 所有 Celery 任务必须设计为幂等的（重复执行产生相同结果）
- 使用数据库状态或 Redis 锁防止重复处理

### 6.2 失败处理

- 可重试异常：使用 `self.retry()` 并设置 `max_retries`
- 永久失败：发送到 DLQ（`shared_config.dlq`），记录失败原因
- 超时：通过 `task_time_limit` 配置硬超时

### 6.3 结果存储

- 默认不存储任务结果（`ignore_result=True`）
- 需要结果的任务使用 Redis backend，设置 `result_expires`
