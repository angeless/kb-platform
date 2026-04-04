# KB Platform 部署指南

## 系统要求

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (with pgvector extension)
- Redis 7+
- MinIO (本地开发) 或 AWS S3 (生产)
- FFmpeg (视频解析功能)
- ClamAV daemon (可选，文件恶意扫描)

## 环境变量

### 必需

| 变量 | 说明 | 示例 |
|------|------|------|
| `POSTGRES_HOST` | PostgreSQL 主机 | `localhost` |
| `POSTGRES_DB` | 数据库名 | `kb_platform` |
| `JWT_SECRET` | JWT 签名密钥 (>=32 字符) | `your-secret-key-at-least-32-chars` |
| `ENCRYPTION_KEY` | AES-256 加密密钥 | `your-32-byte-encryption-key-here` |

### 可选

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `STORAGE_BACKEND` | 存储后端 | `minio` |
| `S3_ENDPOINT` | MinIO/S3 端点 | `http://localhost:9000` |
| `REDIS_SENTINEL_HOSTS` | Redis Sentinel | 空（单实例） |
| `CLAMAV_ENABLED` | 启用恶意扫描 | `false` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel 收集器 | 空（禁用） |

## 部署步骤

### 1. 数据库迁移

```bash
cd infra/sql && alembic upgrade head
```

### 2. 启动后端服务

```bash
# API 服务
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8080

# Ingestion Worker
celery -A services.ingestion-worker.worker.celery_app worker -Q ingestion

# Pipeline Worker
celery -A services.pipeline-worker.worker.celery_app worker -Q pipeline

# AI Orchestrator
celery -A services.ai-orchestrator.orchestrator.celery_app worker -Q ai
```

### 3. 启动前端

```bash
cd apps/web && npm run build && npm start
```

## Docker Compose

参考 `docker-compose.yml`（需确保 FFmpeg 安装在 ingestion-worker 镜像中）。

## 监控

- Prometheus: `GET /metrics`
- 健康检查: `GET /healthz`
- 深度健康: `GET /readyz`
