# KB Platform — 部署指南

## 环境要求

- Docker 24+ 和 Docker Compose V2
- 至少 8GB RAM、4 核 CPU、50GB 磁盘
- 域名（可选，内网部署可用 IP）
- 端口 80 和 443 可用

## 部署步骤

### 1. 准备配置

```bash
# 克隆代码
git clone <repo-url> /opt/kb-platform && cd /opt/kb-platform

# 创建生产配置
cp .env.production.example .env.production

# 编辑配置，填写所有必填项
vim .env.production
```

**必填项清单**：
- `JWT_SECRET` — `openssl rand -base64 48`
- `ENCRYPTION_KEY` — `openssl rand -base64 32`
- `POSTGRES_PASSWORD` — `openssl rand -base64 24`
- `REDIS_PASSWORD` — `openssl rand -base64 24`
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`
- `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`

### 2. SSL 证书

**方案 A — Let's Encrypt（推荐）：**
```bash
# certbot 容器会自动申请和续签，前提是域名已解析到服务器
# 首次需要先启动 Nginx 以响应 ACME challenge
```

**方案 B — 自签证书（内网/测试）：**
```bash
bash infra/nginx/ssl/generate-self-signed.sh your-domain.com
```

### 3. 一键部署

```bash
bash infra/scripts/deploy.sh
```

脚本会依次执行：前置检查 → 构建镜像 → 数据库迁移 → 启动服务 → 健康检查。

### 4. 验证

```bash
# 检查服务状态
docker compose -f docker-compose.yml -f infra/docker/docker-compose.production.yml ps

# 检查 API 健康
curl -k https://localhost/api/health/ready

# 检查版本
curl -k https://localhost/api/_version
```

### 5. 配置备份（推荐）

```bash
# 安装 crontab
crontab infra/scripts/crontab.example
```

### 6. 启动监控（可选）

```bash
docker compose -f docker-compose.yml -f infra/monitoring/docker-compose.monitoring.yml up -d
# Grafana: http://localhost:3001 (admin / 你在 .env.production 中设置的 GRAFANA_PASSWORD)
```

## 目录结构

```
/opt/kb-platform/
├── docker-compose.yml                    # 基础服务定义
├── infra/
│   ├── docker/docker-compose.production.yml  # 生产 override
│   ├── nginx/                            # Nginx 配置
│   ├── scripts/                          # 部署/备份脚本
│   └── monitoring/                       # Prometheus + Grafana
├── .env.production                       # 生产环境变量（不入库）
└── backups/                              # 备份目录（自动创建）
```
