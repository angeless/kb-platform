# KB Platform 开发者上手指南

## 项目结构

```
knowledge_SQL/
├── services/
│   ├── api/              # FastAPI 主服务（认证、CRUD、搜索）
│   ├── ingestion-worker/ # 解析工作器（text/pdf/ocr/asr/video）
│   ├── pipeline-worker/  # 9 阶段流水线工作器
│   └── ai-orchestrator/  # LLM 编排服务
├── packages/
│   ├── shared-config/    # 共享配置（Settings）
│   ├── shared-models/    # SQLAlchemy 模型
│   ├── shared-schemas/   # Pydantic 请求/响应模型
│   └── shared-errors/    # 统一错误码
├── apps/web/             # Next.js 15 前端 SPA
├── infra/sql/            # Alembic 迁移
└── docs/                 # 技术规范 + 开发计划
```

## 本地开发

```bash
# 1. 安装依赖
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd apps/web && npm install && cd ../..

# 2. 启动基础设施
docker-compose up -d postgres redis minio

# 3. 数据库迁移
cd infra/sql && alembic upgrade head && cd ../..

# 4. 运行测试
PYTHONPATH=services/api:packages/shared-config:packages/shared-models:packages/shared-schemas:packages/shared-errors \
  python -m pytest services/api/tests/ -v
```

## 关键概念

- **Tenant (KB)**: 顶层租户，包含用户和项目
- **Project**: 知识项目，包含资产和文档
- **Asset**: 上传的原始文件（text/pdf/image/audio/video/url）
- **AssetChunk**: 解析后的文本片段 + IR 元数据
- **KnowledgeDoc**: 生成的知识文档（Markdown）
- **Pipeline**: 9 阶段处理流水线（classify → generate → quality_check → ...）
- **Skill**: 用户自定义的知识处理规则
- **ReviewTask**: 审批工作流

## 开发规范

详见 `docs/tech-specs/` 目录下的技术规范文件。
