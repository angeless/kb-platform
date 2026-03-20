# KB Platform

将多模态原始资料自动整理为可追溯、可维护、可被 AI 使用的结构化知识系统。

## 快速启动

### 环境要求

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (with pgvector)
- Redis 7+
- MinIO (或 S3 兼容存储)

### 本地开发

```bash
# 1. 克隆并安装后端依赖
git clone <repo-url> && cd knowledge_SQL
pip install -e ".[dev]"

# 2. 安装前端依赖
cd apps/web && npm install && cd ../..

# 3. 启动基础设施 (PostgreSQL, Redis, MinIO)
docker-compose up -d postgres redis minio

# 4. 运行数据库迁移
cd infra/sql && alembic upgrade head && cd ../..

# 5. 启动后端 API
cd services/api && uvicorn app.main:create_app --factory --reload --port 8080

# 6. 启动前端
cd apps/web && npm run dev
```

### Docker 一键启动

```bash
docker-compose up -d
```

访问：
- API: http://localhost:8080
- 前端: http://localhost:3000
- MinIO Console: http://localhost:9001

## 项目结构

```
services/
  api/              # FastAPI 主服务（认证、CRUD、搜索、导出）
  ingestion-worker/  # 解析工作器（text/pdf/ocr/asr）
  pipeline-worker/   # 9 阶段知识流水线
  ai-orchestrator/   # LLM 编排服务
packages/
  shared-config/     # 共享配置
  shared-models/     # SQLAlchemy 数据模型
  shared-schemas/    # Pydantic 请求/响应模型
  shared-errors/     # 统一错误码
apps/
  web/              # Next.js 15 前端 SPA
infra/
  docker/           # Dockerfile + 入口脚本
  sql/              # Alembic 迁移
docs/
  tech-specs/       # 技术规范
  dev-plans/        # 开发计划
  prd/              # 产品 PRD
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.12) |
| 前端框架 | Next.js 15 + React 19 + TypeScript |
| 数据库 | PostgreSQL 16 (pgvector) |
| 缓存/消息 | Redis 7 |
| 对象存储 | MinIO (S3 兼容) |
| 异步任务 | Celery 5 |
| 监控 | Prometheus + Grafana |

## 测试

```bash
# 后端测试
python3 -m pytest services/api/tests/ -v

# 前端测试
cd apps/web && npx vitest run

# 整合检查
bash scripts/ci_verify.sh
```

## 版本

当前版本：见 [VERSION](VERSION) 文件
变更日志：见 [CHANGELOG.md](CHANGELOG.md)

## 许可证

Proprietary
