# KB Platform 运维手册 (Runbook)

**版本**: v0.35.0
**更新日期**: 2026-03-19

---

## 1. 故障场景与处理

### 场景 1: 数据库连接失败

**症状**:
- `/readyz` 返回 500 或超时
- `/api/health/ready` 中 `postgres.status` 为 `error`
- 应用日志中出现 `Connection refused` 或 `timeout` 错误

**诊断步骤**:

```bash
# 1. 检查 PostgreSQL 容器状态
docker compose ps postgres

# 2. 查看 PostgreSQL 日志
docker compose logs postgres --tail=30

# 3. 测试数据库连接
docker compose exec postgres pg_isready -U kb_user -d kb_platform

# 4. 检查数据库进程
docker compose exec postgres psql -U kb_user -d kb_platform -c "SELECT 1"

# 5. 检查连接数
docker compose exec postgres psql -U kb_user -d kb_platform -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='kb_platform'"

# 6. 检查磁盘空间
docker compose exec postgres df -h /var/lib/postgresql/data
```

**解决步骤**:

| 问题 | 解决方案 |
|------|----------|
| 容器未运行 | `docker compose up -d postgres` |
| 容器 OOM Killed | 增加 Docker 内存限制，重启 `docker compose restart postgres` |
| 连接数耗尽 | `docker compose exec postgres psql -U kb_user -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle' AND datname='kb_platform'"` |
| 磁盘满 | 清理 WAL 日志，参见场景 5 |
| 数据损坏 | 从备份恢复（参见备份恢复部分） |

---

### 场景 2: Redis 连接失败

**症状**:
- `/api/health/ready` 中 `redis.status` 为 `error`
- Celery worker 无法接收任务
- WebSocket 推送中断

**诊断步骤**:

```bash
# 1. 检查 Redis 容器状态
docker compose ps redis

# 2. 测试 Redis 连接
docker compose exec redis redis-cli ping
# 期望: PONG

# 3. 检查 Redis 内存使用
docker compose exec redis redis-cli info memory

# 4. 检查连接数
docker compose exec redis redis-cli info clients

# 5. 查看 Redis 日志
docker compose logs redis --tail=30
```

**解决步骤**:

| 问题 | 解决方案 |
|------|----------|
| 容器未运行 | `docker compose up -d redis` |
| 内存不足 | `docker compose exec redis redis-cli FLUSHDB`（清除非持久化数据），或增加内存限制 |
| 连接数过多 | 检查 Celery worker 数量，减少并发 |
| 持久化异常 | 重启 Redis `docker compose restart redis` |

**影响评估**: Redis 下线时，系统状态为 `degraded`（非 `unhealthy`），API 仍可服务，但以下功能受影响：
- Celery 任务无法派发和执行
- WebSocket 实时推送中断
- 限流功能可能不准确

---

### 场景 3: MinIO 连接失败

**症状**:
- `/api/health/ready` 中 `minio.status` 为 `error`
- 文件上传失败
- 应用日志中出现 `EndpointConnectionError`

**诊断步骤**:

```bash
# 1. 检查 MinIO 容器状态
docker compose ps minio

# 2. 检查 MinIO 健康
curl -f http://localhost:9000/minio/health/live
# 期望: 返回 200

# 3. 检查 bucket 是否存在
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc ls local/

# 4. 查看 MinIO 日志
docker compose logs minio --tail=30

# 5. 检查磁盘空间
docker compose exec minio df -h /data
```

**解决步骤**:

| 问题 | 解决方案 |
|------|----------|
| 容器未运行 | `docker compose up -d minio` |
| Bucket 不存在 | `docker compose restart minio-init` |
| 磁盘满 | 清理旧文件或扩展存储卷 |
| 认证失败 | 检查 `S3_ACCESS_KEY` 和 `S3_SECRET_KEY` 是否与 `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` 一致 |

**影响评估**: MinIO 下线时，系统状态为 `degraded`，API 仍可服务，但文件上传/下载功能不可用。

---

### 场景 4: 应用无响应

**症状**:
- `/healthz` 不返回或超时
- 前端显示 502/504 错误
- `docker compose ps api` 显示状态异常

**诊断步骤**:

```bash
# 1. 检查 API 容器状态
docker compose ps api

# 2. 查看 API 最近日志
docker compose logs api --tail=50

# 3. 检查容器资源使用
docker stats --no-stream kb-platform-api-1

# 4. 检查所有依赖服务状态
curl -s http://localhost:8080/api/health/ready | python3 -m json.tool

# 5. 检查端口是否被占用
lsof -i :8080
```

**解决步骤**:

| 问题 | 解决方案 |
|------|----------|
| 容器崩溃/退出 | 查看日志定位错误原因，修复后 `docker compose up -d api` |
| 内存耗尽 (OOM) | 增加内存限制，检查是否有内存泄漏 |
| CPU 100% | 检查是否有请求风暴，启用/调整限流 |
| 线程死锁 | `docker compose restart api`（优雅停机 30s 超时） |
| 依赖不可用 | 按照场景 1-3 逐一排查 |

**紧急恢复**:
```bash
# 强制重启所有服务
docker compose restart

# 如仍不恢复，完全重建
docker compose down && docker compose up -d
```

---

### 场景 5: 磁盘空间不足

**症状**:
- 数据库写入失败
- MinIO 上传失败
- Docker 日志报 `no space left on device`

**诊断步骤**:

```bash
# 1. 检查宿主机磁盘
df -h

# 2. 检查 Docker 占用
docker system df

# 3. 检查各容器卷大小
docker system df -v | head -30

# 4. 检查 PostgreSQL WAL 日志
docker compose exec postgres du -sh /var/lib/postgresql/data/pg_wal/
```

**清理步骤**:

```bash
# 1. 清理未使用的 Docker 资源（镜像、网络、卷）
docker system prune -f

# 2. 清理旧的 Docker 镜像
docker image prune -a -f --filter "until=168h"

# 3. 手动清理 PostgreSQL WAL（谨慎操作）
docker compose exec postgres psql -U kb_user -c "CHECKPOINT;"

# 4. 查看 Prometheus 数据大小（如启用监控）
du -sh /var/lib/docker/volumes/*prometheus*
```

**监控建议**:
- 在 Grafana 中设置磁盘使用率告警（阈值 80%）
- 设置日志轮转策略，避免日志无限增长
- Prometheus 保留时间默认 30 天（可在 `docker-compose.monitoring.yml` 中调整 `--storage.tsdb.retention.time`）

---

## 2. 性能调优建议

### 2.1 API 服务调优

| 参数 | 默认值 | 生产建议 | 说明 |
|------|--------|----------|------|
| `RATE_LIMIT_PER_MINUTE` | 100 | 根据流量调整 | 全局 API 限流 |
| `MAX_UPLOAD_SIZE_MB` | 100 | 根据业务需求 | 文件上传大小限制 |
| Uvicorn workers | 1 | CPU 核数 × 2 + 1 | 在 Dockerfile 中调整 |

### 2.2 数据库调优

```bash
# 查看慢查询
docker compose exec postgres psql -U kb_user -d kb_platform -c \
  "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 检查索引使用率
docker compose exec postgres psql -U kb_user -d kb_platform -c \
  "SELECT schemaname, relname, seq_scan, idx_scan FROM pg_stat_user_tables ORDER BY seq_scan DESC LIMIT 10;"
```

### 2.3 Celery Worker 调优

| 参数 | 当前值 | 说明 |
|------|--------|------|
| `-c 2` | 2 并发 | 增加可提高吞吐，但需更多内存 |
| `--soft-time-limit=25` | 25s | 任务软超时，超时后抛 `SoftTimeLimitExceeded` |
| `--time-limit=30` | 30s | 硬超时，强制杀死任务 |
| `stop_grace_period: 35s` | 35s | Docker 停止等待时间（> time-limit） |

---

## 3. 日志查询示例

v0.35.0 启用了 JSON 结构化日志，可通过以下方式查询：

### 3.1 基本查询

```bash
# 查看 API 最近日志（JSON 格式）
docker compose logs api --tail=20

# 按 request_id 查找请求链路
docker compose logs api 2>&1 | grep '"request_id": "abc-123"'

# 查找错误日志
docker compose logs api 2>&1 | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        log = json.loads(line.strip())
        if log.get('level') == 'ERROR':
            print(json.dumps(log, indent=2))
    except: pass
"
```

### 3.2 使用 jq 查询（推荐）

```bash
# 安装 jq: apt-get install jq / brew install jq

# 查看所有 ERROR 级别日志
docker compose logs api --no-log-prefix 2>&1 | jq -r 'select(.level == "ERROR")'

# 按 user_id 过滤
docker compose logs api --no-log-prefix 2>&1 | jq -r 'select(.user_id == "uuid-here")'

# 查看慢请求（假设有 duration 字段）
docker compose logs api --no-log-prefix 2>&1 | jq -r 'select(.level == "WARNING")'
```

### 3.3 Worker 日志

```bash
# 查看 ingestion worker 日志
docker compose logs ingestion-worker --tail=30

# 查看 pipeline worker 日志
docker compose logs pipeline-worker --tail=30

# 查看 AI orchestrator 日志
docker compose logs ai-orchestrator --tail=30
```

---

## 4. 监控与告警

### 4.1 关键指标

| 指标 | Prometheus 查询 | 告警阈值 |
|------|-----------------|----------|
| 请求错误率 | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` | > 5% |
| P95 响应时间 | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` | > 500ms |
| P99 响应时间 | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` | > 1s |
| 请求速率 | `rate(http_requests_total[1m])` | 异常波动 |

### 4.2 健康检查端点

| 端点 | 用途 | 检查间隔建议 |
|------|------|-------------|
| `GET /healthz` | K8s liveness probe | 10s |
| `GET /readyz` | K8s readiness probe | 10s |
| `GET /api/health/ready` | 深度健康检查（含 Redis + MinIO） | 30s |

### 4.3 Grafana 预配置仪表盘

启动监控栈后（`docker-compose.monitoring.yml`），Grafana 自动加载 3 个仪表盘：

1. **Application Performance** — 请求速率、错误率、P50/P95/P99 响应时间
2. **Resource Utilization** — 请求/响应大小分布、进程 CPU/内存
3. **Business Metrics** — 端点级请求速率、上传/搜索/认证活动

访问地址: `http://localhost:3001` (admin/admin)

---

## 5. 备份与恢复

### 5.1 数据库备份

```bash
# 逻辑备份
docker compose exec postgres pg_dump -U kb_user -d kb_platform \
  --format=custom -f /tmp/kb_backup_$(date +%Y%m%d).dump

# 从容器中复制备份
docker compose cp postgres:/tmp/kb_backup_$(date +%Y%m%d).dump ./backups/
```

### 5.2 数据库恢复

```bash
# 将备份复制到容器
docker compose cp ./backups/kb_backup_20260319.dump postgres:/tmp/

# 恢复（会覆盖现有数据）
docker compose exec postgres pg_restore -U kb_user -d kb_platform \
  --clean --if-exists /tmp/kb_backup_20260319.dump
```

### 5.3 MinIO 数据备份

```bash
# 使用 mc 工具备份
docker compose exec minio mc mirror local/kb-assets /tmp/kb-assets-backup/

# 从宿主机直接备份 Docker 卷
docker run --rm -v kb-platform_miniodata:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/minio_backup_$(date +%Y%m%d).tar.gz /data
```

---

## 6. 优雅停机流程

v0.35.0 实现了优雅停机机制：

1. Docker 发送 `SIGTERM` 信号
2. API 服务停止接受新请求
3. 等待现有请求完成（最长 30s）
4. 关闭数据库连接池
5. 刷新日志缓冲
6. 容器退出

```bash
# 优雅停机（推荐）
docker compose stop api
# API 有 30s 优雅停机期

# Celery worker 优雅停机
docker compose stop ingestion-worker pipeline-worker ai-orchestrator
# Workers 有 35s 优雅停机期（> 任务硬超时 30s）
```

> **注意**: 不要使用 `docker compose kill` 或 `docker kill`，这会发送 SIGKILL 直接杀死进程，可能导致正在处理的请求中断。
