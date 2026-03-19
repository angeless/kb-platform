# KB Platform 升级指南: v0.34.0 → v0.35.0

**版本**: v0.35.0
**更新日期**: 2026-03-19

---

## 1. 版本概要

v0.35.0 是 **生产就绪 (Production Readiness)** 版本，在 v0.34.0 基础上新增运维可观测性和基础设施能力，**不涉及数据库结构变更，不影响现有业务逻辑**。

### 新增能力

| 功能 | 说明 |
|------|------|
| CORS 中间件 | 通过 `CORS_ORIGINS` 环境变量控制跨域访问 |
| `/api/versions` 端点 | 返回 API 支持的版本列表 |
| `/api/health/ready` 端点 | 深度健康检查（PG + Redis + MinIO） |
| 结构化 JSON 日志 | stdout 输出 JSON 格式日志，支持 request_id、user_id |
| `/metrics` 端点 | Prometheus 指标暴露 |
| Grafana 仪表盘 | 3 个预配置仪表盘 (需启动监控栈) |
| CI/CD Pipeline | GitHub Actions PR 验证 + Tag 构建 |
| 优雅停机 | API 30s + Worker 35s 停机窗口 |
| OpenAPI 规范 | 所有端点均有 summary/description/responses/security |
| Bearer 安全声明 | Swagger UI 支持 JWT 认证对话框 |

### 不变能力

- 所有 v0.34.0 API 端点保持不变（路径、请求体、响应体、状态码）
- 数据库 schema 无变更
- 前端功能无影响

---

## 2. 升级前置条件

| 条件 | 验证方式 |
|------|----------|
| 当前运行 v0.34.0 | `curl http://localhost:8080/healthz` 确认应用存活 |
| 数据库备份已完成 | 虽然无 schema 变更，仍建议在升级前备份 |
| 了解新增环境变量 | 阅读下方第 3 节 |

---

## 3. 新增环境变量

v0.35.0 新增以下环境变量，均有默认值，无需强制设置（生产环境建议配置）：

| 变量名 | 默认值 | 说明 | 是否必须 |
|--------|--------|------|----------|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | 允许的跨域来源（逗号分隔） | 生产环境建议设置 |
| `LOG_LEVEL` | `INFO` | 日志级别 (已存在，v0.35 开始生效) | 否 |

> 注: `JWT_SECRET` 和 `ENCRYPTION_KEY` 在 v0.34 中已存在。v0.35 新增了 **生产环境验证**：当 `ENVIRONMENT=production` 时，这两个变量不允许使用默认值。

---

## 4. 新增依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| `python-json-logger` | >=2.0 | JSON 结构化日志 |
| `prometheus-client` | >=0.16 | Prometheus 指标收集 |

这两个依赖已添加到 `services/api/pyproject.toml`，Docker 构建时会自动安装。

---

## 5. 升级步骤

### 5.1 拉取新版本代码

```bash
cd kb-platform
git fetch origin
git checkout v0.35.0
```

### 5.2 配置新增环境变量（可选）

```bash
# 编辑 .env 文件，添加：
CORS_ORIGINS=https://your-frontend.example.com
```

如果当前 `ENVIRONMENT=production`，确认 `JWT_SECRET` 和 `ENCRYPTION_KEY` 不是默认值：
```bash
grep -E "^(JWT_SECRET|ENCRYPTION_KEY)" .env
# 两者都不能是 "change-me-in-production" 或 "change-me-32-byte-key-for-aes256"
```

### 5.3 重建并重启服务

```bash
# 重建 Docker 镜像（安装新依赖）
docker compose build api ingestion-worker pipeline-worker ai-orchestrator

# 依次重启服务（推荐逐个重启以避免中断）
docker compose up -d postgres redis minio  # 基础设施不变，确认存活
docker compose up -d api                    # 重启 API
docker compose up -d ingestion-worker pipeline-worker ai-orchestrator  # 重启 Workers
```

### 5.4 验证升级成功

```bash
# 1. 检查 API 存活
curl http://localhost:8080/healthz
# 期望: {"status":"ok"}

# 2. 检查深度健康（新端点）
curl -s http://localhost:8080/api/health/ready | python3 -m json.tool
# 期望: status 为 "ok"，version 为 "0.35.0"

# 3. 检查 API 版本（新端点）
curl http://localhost:8080/api/versions
# 期望: {"versions":[{"version":"v1","status":"active","deprecation_date":null}]}

# 4. 检查 Prometheus 指标（新端点）
curl http://localhost:8080/metrics | head -5
# 期望: Prometheus text 格式输出

# 5. 检查 OpenAPI 文档（增强后）
# 浏览器访问 http://localhost:8080/docs
# 期望: 每个端点都有 summary/description，右上角有 Authorize 按钮

# 6. 检查 CORS（新功能）
curl -X OPTIONS http://localhost:8080/v1/projects \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" -I
# 期望: 返回 Access-Control-Allow-Origin header
```

### 5.5 启动监控（可选，新增）

```bash
# 启动 Prometheus + Grafana
docker compose -f docker-compose.monitoring.yml up -d

# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (初始密码 admin/admin)
```

---

## 6. 数据库迁移

**v0.35.0 无数据库 schema 变更**，不需要执行 Alembic 迁移。

如需确认当前迁移状态：
```bash
docker compose exec api alembic current
```

---

## 7. 回滚步骤

如升级后发现问题，可回滚至 v0.34.0：

```bash
# 1. 停止当前服务
docker compose stop api ingestion-worker pipeline-worker ai-orchestrator

# 2. 切换回 v0.34.0 代码
git checkout v0.34.0

# 3. 重建镜像
docker compose build api ingestion-worker pipeline-worker ai-orchestrator

# 4. 启动服务
docker compose up -d api ingestion-worker pipeline-worker ai-orchestrator

# 5. 验证
curl http://localhost:8080/healthz
```

**回滚注意事项**:
- 无需数据库回滚（v0.35 未变更 schema）
- 回滚后以下功能不可用：`/api/health/ready`、`/metrics`、`/api/versions`、JSON 日志、CORS
- 回滚后需移除 `docker-compose.monitoring.yml` 启动的服务：`docker compose -f docker-compose.monitoring.yml down`
- 如有 `.env` 中新增了 `CORS_ORIGINS`，回滚后该变量会被忽略（不会报错）

---

## 8. 功能启用顺序

v0.35.0 的所有新功能在升级后自动生效，无需手动启用。各功能独立，无启用顺序依赖：

| 功能 | 启用方式 | 配置项 |
|------|----------|--------|
| CORS | 自动 | `CORS_ORIGINS` 环境变量 |
| 深度健康检查 | 自动 | 无需配置 |
| JSON 日志 | 自动 | `LOG_LEVEL` 控制级别 |
| Prometheus 指标 | 自动 | 无需配置 |
| Grafana 仪表盘 | 手动 | 需启动 `docker-compose.monitoring.yml` |
| CI/CD | 自动 | 推送代码到 GitHub 后生效 |
| 优雅停机 | 自动 | Docker `stop_grace_period` 已配置 |
| OpenAPI 增强 | 自动 | 访问 `/docs` 查看 |

---

## 9. 已知限制

- `/api/health/ready` 每次调用会创建临时 Redis 和 S3 连接，适合低频探测（≤1次/30秒），不适合高频轮询
- Grafana 仪表盘初始密码为 `admin/admin`，首次登录后请修改
- CI/CD 流水线需要在 GitHub 仓库 Settings 中配置 `GHCR_TOKEN` secret 才能推送 Docker 镜像
