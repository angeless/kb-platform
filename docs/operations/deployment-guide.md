# KB Platform 部署指南

**版本**: v0.35.0
**更新日期**: 2026-03-19

---

## 1. 前置条件检查清单

| 项目 | 最低版本 | 验证命令 |
|------|----------|----------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| 可用磁盘空间 | 10 GB | `df -h` |
| 可用内存 | 4 GB | `free -h` / `sysctl hw.memsize` (macOS) |
| 端口 5432 可用 | — | `lsof -i :5432` (应无输出) |
| 端口 6379 可用 | — | `lsof -i :6379` |
| 端口 8080 可用 | — | `lsof -i :8080` |
| 端口 9000, 9001 可用 | — | `lsof -i :9000` |

---

## 2. 环境变量配置表

### 2.1 必需变量（生产环境必须修改）

| 变量名 | 说明 | 默认值 | 生产要求 |
|--------|------|--------|----------|
| `JWT_SECRET` | JWT 签名密钥 | `change-me-in-production` | 至少 32 字符的随机字符串 |
| `ENCRYPTION_KEY` | AES-256 加密密钥 | `change-me-32-byte-key-for-aes256` | 恰好 32 字节的随机字符串 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | `change_me` | 强密码 |
| `ENVIRONMENT` | 运行环境标识 | `development` | 设为 `production` |

> **重要**: 当 `ENVIRONMENT=production` 时，应用会拒绝启动如果 `JWT_SECRET` 或 `ENCRYPTION_KEY` 使用默认值。

### 2.2 数据库配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_HOST` | PostgreSQL 主机 | `localhost` |
| `POSTGRES_PORT` | PostgreSQL 端口 | `5432` |
| `POSTGRES_USER` | PostgreSQL 用户名 | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | `postgres` |
| `POSTGRES_DB` | 数据库名 | `kb_platform` |

### 2.3 Redis 配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `REDIS_HOST` | Redis 主机 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_DB` | Redis 数据库编号 | `0` |

### 2.4 MinIO / S3 配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `S3_ENDPOINT` | S3 兼容服务端点 | `http://localhost:9000` |
| `S3_ACCESS_KEY` | S3 访问密钥 | `minioadmin` |
| `S3_SECRET_KEY` | S3 密钥 | `minioadmin` |
| `S3_BUCKET` | 存储桶名称 | `kb-assets` |
| `S3_REGION` | S3 区域 | `us-east-1` |

### 2.5 应用配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_PORT` | API 服务端口 | `8080` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `CORS_ORIGINS` | 允许的 CORS 来源（逗号分隔） | `http://localhost:3000,http://localhost:3001` |
| `RATE_LIMIT_PER_MINUTE` | API 限流（每分钟请求数） | `100` |
| `MAX_UPLOAD_SIZE_MB` | 最大上传文件大小 (MB) | `100` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token 有效期 (分钟) | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token 有效期 (天) | `7` |

### 2.6 AI 服务配置（可选）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | (空) |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | (空) |

---

## 3. 首次部署步骤

### 3.1 获取代码

```bash
git clone https://github.com/angeless/kb-platform.git
cd kb-platform
git checkout v0.35.0
```

### 3.2 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，修改以下必需项：
# JWT_SECRET=<生成的随机字符串，至少32字符>
# ENCRYPTION_KEY=<生成的随机字符串，恰好32字节>
# POSTGRES_PASSWORD=<强密码>
# ENVIRONMENT=production
# CORS_ORIGINS=https://your-frontend-domain.com
```

生成安全密钥的推荐方式：
```bash
# JWT_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# ENCRYPTION_KEY (恰好 32 字节)
python3 -c "import secrets; print(secrets.token_urlsafe(24)[:32])"
```

### 3.3 启动基础服务

```bash
# 启动所有服务
docker compose up -d

# 查看启动状态
docker compose ps

# 等待所有服务健康（约 30 秒）
docker compose ps --format '{{.Name}} {{.Status}}'
```

### 3.4 执行数据库迁移

```bash
# 在 API 容器中运行 Alembic 迁移
docker compose exec api alembic upgrade head
```

### 3.5 启动监控服务（可选）

```bash
# 启动 Prometheus + Grafana
docker compose -f docker-compose.monitoring.yml up -d

# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

---

## 4. 配置验证清单

部署完成后，逐项检查以下内容：

| 检查项 | 验证方式 | 期望结果 |
|--------|----------|----------|
| API 存活 | `curl http://localhost:8080/healthz` | `{"status":"ok"}` |
| 数据库连接 | `curl http://localhost:8080/readyz` | `{"status":"ok"}` |
| 深度健康检查 | `curl http://localhost:8080/api/health/ready` | `status` 为 `ok` 或 `degraded` |
| API 版本 | `curl http://localhost:8080/api/versions` | 返回版本列表 |
| Prometheus 指标 | `curl http://localhost:8080/metrics` | 返回 Prometheus text 格式 |
| OpenAPI 文档 | 浏览器访问 `http://localhost:8080/docs` | Swagger UI 正常展示 |
| MinIO 控制台 | 浏览器访问 `http://localhost:9001` | MinIO 登录界面 |

### 深度健康检查详细验证

```bash
curl -s http://localhost:8080/api/health/ready | python3 -m json.tool
```

期望输出：
```json
{
    "status": "ok",
    "version": "0.35.0",
    "checks": {
        "postgres": {"status": "ok", "latency_ms": 5, "message": "Connected"},
        "redis": {"status": "ok", "latency_ms": 2, "message": "PING successful"},
        "minio": {"status": "ok", "latency_ms": 8, "message": "Bucket access OK"}
    }
}
```

---

## 5. 常见部署问题排查

### 5.1 API 容器无法启动

**症状**: `docker compose ps` 显示 api 容器状态为 `Exit` 或 `Restarting`

**排查步骤**:
```bash
# 查看容器日志
docker compose logs api --tail=50

# 常见错误原因：
# 1. "jwt_secret must not use default value in production"
#    → 修改 .env 中的 JWT_SECRET
# 2. "encryption_key must not use default value in production"
#    → 修改 .env 中的 ENCRYPTION_KEY
# 3. 端口被占用
#    → 修改 APP_PORT 或释放端口
```

### 5.2 数据库连接失败

**症状**: `/readyz` 返回 500 或超时

```bash
# 检查 PostgreSQL 容器状态
docker compose ps postgres

# 检查数据库连接
docker compose exec postgres pg_isready -U kb_user -d kb_platform

# 检查环境变量是否正确传递
docker compose exec api env | grep POSTGRES
```

### 5.3 Redis 连接失败

**症状**: `/api/health/ready` 中 redis.status 为 `error`

```bash
# 检查 Redis 容器状态
docker compose ps redis

# 测试 Redis 连接
docker compose exec redis redis-cli ping
# 期望输出: PONG
```

### 5.4 MinIO 连接失败

**症状**: `/api/health/ready` 中 minio.status 为 `error`

```bash
# 检查 MinIO 容器状态
docker compose ps minio

# 检查 bucket 是否存在
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc ls local/kb-assets

# 如果 bucket 不存在，重新初始化
docker compose restart minio-init
```

### 5.5 Alembic 迁移失败

```bash
# 查看当前迁移版本
docker compose exec api alembic current

# 查看迁移历史
docker compose exec api alembic history

# 如果需要回滚
docker compose exec api alembic downgrade -1
```

---

## 6. 服务架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   API (8080)  │────▶│ PostgreSQL   │
│  (3000/3001) │     │   FastAPI     │     │  (pgvector)  │
└──────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────┼──────┐
                    │      │      │
               ┌────▼─┐ ┌─▼───┐ ┌▼─────┐
               │Redis │ │MinIO│ │Celery │
               │(6379)│ │(9000)│ │Workers│
               └──────┘ └─────┘ └───────┘
                                 3 queues:
                                 - ingestion
                                 - pipeline
                                 - ai
```

### 容器列表

| 容器 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | pgvector/pgvector:pg16 | 5432 | 数据库 (含向量搜索扩展) |
| redis | redis:7 | 6379 | 缓存 + 消息队列 broker |
| minio | minio/minio:latest | 9000, 9001 | 对象存储 (S3 兼容) |
| api | 自建 | 8080 | FastAPI 应用服务 |
| ingestion-worker | 自建 | — | Celery worker (文件解析) |
| pipeline-worker | 自建 | — | Celery worker (知识管道) |
| ai-orchestrator | 自建 | — | Celery worker (AI 编排) |
