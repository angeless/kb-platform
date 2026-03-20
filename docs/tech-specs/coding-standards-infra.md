# KB Platform 编码标准 — 基础设施规范

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**优先级**：可选（涉及基础设施时）

---

## 1. 日志

### 1.1 日志框架

- 使用 Python 标准库 `logging` 模块
- 日志配置通过 `logging_config.py` 统一管理
- 本地开发输出可读文本格式，生产环境输出结构化 JSON

### 1.2 日志级别

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| DEBUG | 开发调试信息，生产环境不输出 | 函数入参、中间变量 |
| INFO | 业务事件，正常流程关键节点 | 用户登录、文件上传完成、任务启动 |
| WARNING | 可恢复的异常情况 | 缓存未命中、重试中、配置降级 |
| ERROR | 操作失败，需要关注 | 数据库连接失败、外部服务不可用、任务执行失败 |

### 1.3 日志内容规范

- 禁止在日志中输出密钥、密码、token、个人身份信息（PII）
- 日志消息使用英文，保持简洁可搜索
- 使用参数化格式（`logger.info("Processing file %s", file_id)`），禁止 f-string 拼接日志

```python
# 正确
logger.info("File uploaded: file_id=%s, size=%d, tenant=%s", file_id, size, tenant_id)

# 禁止 — f-string 在日志未启用时仍会求值
logger.info(f"File uploaded: file_id={file_id}, size={size}")
```

### 1.4 Request ID

- 通过 `RequestIdMiddleware` 在每个 HTTP 请求入口生成唯一 request_id
- request_id 自动注入到该请求内的所有日志条目
- request_id 在 Celery 任务中通过 task header 传播

---

## 2. 指标收集

- 通过 `MetricsMiddleware` 收集请求延迟、状态码分布
- Celery 任务记录执行时间和成功/失败计数
- 关键业务指标（文件处理数、LLM 调用次数）通过 INFO 日志输出，供日志聚合系统统计

---

## 3. 配置管理

### 3.1 配置来源

- 所有配置通过环境变量注入
- 使用 Pydantic `BaseSettings` 定义配置类，支持类型校验和默认值
- 本地开发使用 `.env` 文件，通过 `env_file = ".env"` 加载
- 不同环境（dev/staging/prod）通过不同的环境变量值区分

### 3.2 配置层级

```
环境变量 > .env 文件 > BaseSettings 默认值
```

### 3.3 敏感配置

- 生产环境启动时调用 `Settings.validate_production_secrets()` 校验
- 如果检测到使用默认密钥（如 `changeme`、`secret`），拒绝启动
- 敏感配置值可通过 `utils/crypto.py` 加密存储

---

## 4. Docker

### 4.1 镜像构建

- 所有 Dockerfile 使用多阶段构建，减少最终镜像大小
- 最终镜像使用非 root 用户运行（`USER appuser`）
- `.dockerignore` 排除不必要的文件（.git、node_modules、__pycache__、.env）
- 生产镜像不包含开发依赖

### 4.2 基础镜像

- Python 服务使用 `python:3.12-slim` 作为基础镜像
- Node.js 前端使用 `node:20-alpine` 作为基础镜像

---

## 5. Celery 配置

### 5.1 Worker 配置

- 每个 Worker 类型独立配置并发数（ingestion-worker、pipeline-worker、ai-orchestrator）
- CPU 密集型任务使用 prefork 池，I/O 密集型使用 gevent 池
- 设置 `task_time_limit`（硬超时）和 `task_soft_time_limit`（软超时）

### 5.2 Broker 与 Backend

- Broker：Redis（消息队列）
- Backend：Redis（结果存储，仅需要结果的任务启用）
- 配置 `broker_connection_retry_on_startup = True` 确保启动时等待 Redis 就绪

---

## 6. 资源清理

- 数据库会话：请求结束时通过 FastAPI 依赖注入自动关闭
- 文件句柄：使用 `async with` 或 `with` 上下文管理器
- HTTP 连接：使用 `httpx.AsyncClient` 连接池，应用关闭时调用 `await client.aclose()`
- 临时文件：使用 `tempfile` 模块创建，处理完成后立即删除

---

## 7. 健康检查

### 7.1 端点

- 所有服务暴露 `GET /health` 端点
- 返回 200 表示健康，503 表示不健康

### 7.2 检查项

| 检查项 | 说明 |
|--------|------|
| PostgreSQL | 执行 `SELECT 1` 验证连接 |
| Redis | 执行 `PING` 验证连接 |
| MinIO | 检查 bucket 是否可访问 |
| Celery | 检查 worker 是否在线（仅 API 服务检查） |

### 7.3 响应格式

```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "minio": "ok"
  },
  "version": "0.39.0"
}
```
