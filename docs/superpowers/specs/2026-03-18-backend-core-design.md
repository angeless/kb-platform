# KB Platform 后端核心设计文档

## 1. 概述

### 1.1 项目定位
AI 知识整理与知识系统构建平台（kb-platform）—— 将多模态原始资料转化为结构化、可追溯、可被 AI 使用的知识系统。

### 1.2 本阶段范围
后端核心：`services/api` + 4 个共享包（shared-models / shared-schemas / shared-config / shared-errors）+ 数据库迁移 + docker-compose + 基础测试。

**不包含**：ingestion-worker、pipeline-worker、ai-orchestrator、Web 前端、语义/全文检索（需向量库和搜索引擎，留待下一阶段）、增量更新流水线（`POST /v1/ingestion/incremental`）、架构自动生成（`POST /v1/architectures/generate`，依赖 AI Orchestrator）、病毒扫描（需集成第三方服务）。

### 1.3 技术选型

| 项 | 选择 | 理由 |
|---|------|------|
| 语言 | Python 3.12+ | AI/ML 生态最强，大模型 SDK 支持好 |
| Web 框架 | FastAPI | 异步、自带 OpenAPI、Pydantic 集成 |
| ORM | SQLAlchemy 2.0 (async) | 关系映射成熟，支持复杂查询 |
| 迁移 | Alembic | SQLAlchemy 标配迁移工具 |
| 任务队列 | Celery + Redis | 经典可靠，重试/链式/定时任务齐全 |
| 数据库 | PostgreSQL 16 | 文档定义的存储方案 |
| 对象存储 | MinIO (S3 兼容) | 本地开发替代 AWS S3 |
| 缓存/Broker | Redis 7 | Celery broker + 缓存 |
| 认证 | JWT (HS256) | 无状态认证 |
| 密钥加密 | AES-256 | 模型 API Key 加密存储 |

---

## 2. 架构设计

### 2.1 服务划分（严格微服务）

```
kb-platform/
├── services/
│   ├── api/                  # FastAPI - 对外 REST API 入口
│   ├── ingestion-worker/     # Celery Worker - 资料解析（本阶段不实现）
│   ├── pipeline-worker/      # Celery Worker - 流水线编排（本阶段不实现）
│   └── ai-orchestrator/      # 大模型调用封装（本阶段不实现）
├── packages/
│   ├── shared-models/        # SQLAlchemy 模型定义
│   ├── shared-schemas/       # Pydantic schema
│   ├── shared-config/        # 配置读取
│   └── shared-errors/        # 错误码与异常
├── infra/
│   ├── sql/                  # Alembic 迁移
│   └── docker/               # Dockerfile
├── openapi/
├── examples/
├── docker-compose.yml
└── .env.example
```

### 2.2 服务间通信
- **API → Workers**：Celery 任务下发（Redis 作为 broker）
- **Workers → AI Orchestrator**：HTTP 内部调用
- **所有服务共享** PostgreSQL（通过 shared-models 包）

### 2.3 services/api 内部结构

```
services/api/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── deps.py              # 依赖注入（DB session, 当前用户）
│   ├── routers/
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── assets.py
│   │   ├── jobs.py
│   │   ├── architectures.py
│   │   ├── docs.py
│   │   └── model_providers.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── asset_service.py
│   │   ├── job_service.py
│   │   ├── architecture_service.py
│   │   ├── doc_service.py
│   │   └── model_provider_service.py
│   └── middleware/
│       ├── auth.py
│       └── tenant.py
├── tests/
├── requirements.txt
├── Dockerfile
└── pyproject.toml
```

**分层原则**：Router（参数校验 + 响应格式化）→ Service（业务逻辑）→ Model（数据访问）

---

## 3. 数据模型

### 3.1 基础层

**tenant**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(200) | 租户名称 |
| status | VARCHAR(20) | active / suspended |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**user**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | UUID FK | 所属租户 |
| email | VARCHAR(255) | 邮箱，唯一 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| role | VARCHAR(30) | platform_admin / tenant_admin / project_admin / editor / reviewer / viewer |
| status | VARCHAR(20) | active / disabled |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**project**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | UUID FK | 所属租户 |
| name | VARCHAR(200) | 项目名称 |
| industry_hint | VARCHAR(100) | 行业提示 |
| status | VARCHAR(20) | active / archived |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 3.2 资料层

**asset**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID FK | 所属项目 |
| asset_type | VARCHAR(20) | image / audio / video / pdf / doc / url / zip / text |
| filename | VARCHAR(500) | 文件名 |
| source_url | TEXT | 来源 URL（可选） |
| object_path | VARCHAR(500) | MinIO 存储路径 |
| file_hash | VARCHAR(64) | SHA-256 哈希 |
| file_size | BIGINT | 文件大小（字节） |
| parse_status | VARCHAR(20) | pending / parsing / parsed / failed |
| uploaded_by | UUID FK | 上传人 |
| uploaded_at | TIMESTAMP | |

**asset_chunk**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| asset_id | UUID FK | 所属资料 |
| chunk_index | INTEGER | 片段序号 |
| content_text | TEXT | 文本内容 |
| page_or_timestamp | VARCHAR(50) | 页码或时间戳 |
| tags | JSONB | 初步标签 |
| created_at | TIMESTAMP | |

### 3.3 架构层

**architecture**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID FK | 所属项目 |
| name | VARCHAR(200) | 架构名称 |
| version | VARCHAR(20) | 语义化版本号 |
| status | VARCHAR(20) | draft / reviewing / published / deprecated |
| levels_json | JSONB | 层级定义 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**architecture_node**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| architecture_id | UUID FK | 所属架构 |
| parent_id | UUID FK | 父节点（可为空） |
| node_name | VARCHAR(200) | 节点名称 |
| node_type | VARCHAR(30) | category / topic / document / glossary / conflict / index |
| level | INTEGER | 层级 |
| description | TEXT | 说明 |
| accept_types | JSONB | 可接收类型 |
| reject_types | JSONB | 禁止接收类型 |
| update_policy | VARCHAR(30) | 更新规则 |
| review_policy | VARCHAR(30) | 审核规则 |
| status | VARCHAR(20) | draft / reviewing / published / deprecated |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 3.4 知识层

**knowledge_doc**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID FK | 所属项目 |
| node_id | UUID FK | 绑定的架构节点 |
| doc_type | VARCHAR(30) | source_index / topic / procedure / faq / entity / glossary / conflict / governance |
| title | VARCHAR(500) | 标题 |
| current_version | INTEGER | 当前版本号 |
| status | VARCHAR(20) | draft / reviewing / published / deprecated |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**knowledge_doc_version**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| doc_id | UUID FK | 所属文档 |
| version | INTEGER | 版本号 |
| content_md | TEXT | Markdown 内容 |
| change_reason | TEXT | 变更原因 |
| created_by | UUID FK | 创建人 |
| created_at | TIMESTAMP | |

**source_ref**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| doc_version_id | UUID FK | 所属文档版本 |
| asset_chunk_id | UUID FK | 来源片段 |
| location_hint | VARCHAR(200) | 定位信息 |

**conflict_record**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID FK | 所属项目 |
| node_id | UUID FK | 关联节点 |
| description | TEXT | 冲突描述 |
| status | VARCHAR(20) | open / resolved / dismissed |
| resolved_by | UUID FK | 解决人 |
| resolved_at | TIMESTAMP | |
| created_at | TIMESTAMP | |

### 3.5 任务层

**job**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| project_id | UUID FK | 所属项目 |
| job_type | VARCHAR(30) | ingest / classify / architecture_draft / kb_generate / review_publish |
| status | VARCHAR(20) | pending / running / completed / failed |
| error_message | TEXT | 错误信息 |
| retry_count | INTEGER | 重试次数 |
| celery_task_id | VARCHAR(100) | Celery 任务 ID |
| created_by | UUID FK | 创建人 |
| started_at | TIMESTAMP | |
| finished_at | TIMESTAMP | |
| created_at | TIMESTAMP | |

### 3.6 配置层

**model_provider**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | UUID FK | 所属租户 |
| provider_name | VARCHAR(50) | openai / anthropic / google 等 |
| api_key_encrypted | TEXT | AES-256 加密 |
| base_url | VARCHAR(500) | 自定义 Base URL |
| timeout_seconds | INTEGER | 超时（秒） |
| max_context | INTEGER | 最大上下文 |
| status | VARCHAR(20) | active / disabled |
| created_at | TIMESTAMP | |

**model_route**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | UUID FK | 所属租户 |
| task_type | VARCHAR(30) | 任务类型 |
| provider_id | UUID FK | 供应商 |
| model_name | VARCHAR(100) | 模型名称 |
| priority | INTEGER | 优先级 |
| cost_limit_usd | DECIMAL(10,2) | 成本上限 |
| created_at | TIMESTAMP | |

### 3.7 审计层

**audit_log**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| tenant_id | UUID | 租户 |
| project_id | UUID | 项目（可选） |
| user_id | UUID | 操作人 |
| action | VARCHAR(50) | 操作类型 |
| resource_type | VARCHAR(50) | 资源类型 |
| resource_id | UUID | 资源 ID |
| detail | JSONB | 详情 |
| created_at | TIMESTAMP | |

---

## 4. API 设计

### 4.1 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/auth/register` | 注册（创建租户+管理员） |
| POST | `/v1/auth/login` | 登录，返回 Access Token + Refresh Token |
| POST | `/v1/auth/refresh` | 刷新 Access Token |

### 4.2 项目管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/projects` | 创建项目 |
| GET | `/v1/projects` | 列出当前租户的项目 |
| GET | `/v1/projects/{id}` | 项目详情 |
| PATCH | `/v1/projects/{id}` | 更新项目（名称、状态等） |
| DELETE | `/v1/projects/{id}` | 删除项目（需二次确认） |

### 4.3 资料接入
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/assets/upload` | 上传文件（multipart） |
| POST | `/v1/assets/import-url` | URL 导入 |
| POST | `/v1/assets/import-archive` | 压缩包导入 |
| GET | `/v1/assets` | 列出项目资料（query param: project_id） |
| GET | `/v1/assets/{id}` | 资料详情 + 解析状态 |

### 4.4 任务管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/jobs` | 创建任务 |
| GET | `/v1/jobs/{id}` | 任务状态 |
| POST | `/v1/jobs/{id}/retry` | 重试 |
| GET | `/v1/jobs` | 列出项目任务（query param: project_id） |

### 4.5 架构管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/projects/{project_id}/architectures` | 获取项目的架构列表 |
| GET | `/v1/architectures/{id}` | 架构详情 |
| POST | `/v1/architectures/{id}/publish` | 发布架构 |
| POST | `/v1/architectures/{id}/nodes` | 新增节点 |
| PATCH | `/v1/architectures/{id}/nodes/{node_id}` | 修改节点 |

### 4.6 冲突管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/conflicts` | 列出冲突（query param: project_id） |
| GET | `/v1/conflicts/{id}` | 冲突详情 |
| POST | `/v1/conflicts/{id}/resolve` | 解决冲突 |

### 4.7 知识文档
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/docs` | 列出文档（query param: project_id） |
| GET | `/v1/docs/{id}` | 文档详情（含版本列表） |
| POST | `/v1/docs/{id}/review` | 提交审核 |
| POST | `/v1/docs/{id}/publish` | 发布 |

### 4.8 模型配置
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/model-providers` | 添加供应商 |
| GET | `/v1/model-providers` | 列出供应商 |
| POST | `/v1/model-providers/test` | 测试连通性 |
| POST | `/v1/model-routes` | 创建模型路由 |
| GET | `/v1/model-routes` | 列出路由规则 |
| PATCH | `/v1/model-routes/{id}` | 修改路由 |
| DELETE | `/v1/model-routes/{id}` | 删除路由 |

### 4.9 用户管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/users` | 列出租户用户 |
| POST | `/v1/users/invite` | 邀请用户 |
| PATCH | `/v1/users/{id}` | 修改角色/状态 |
| DELETE | `/v1/users/{id}` | 禁用用户 |

### 4.10 健康检查
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/healthz` | 存活检查 |
| GET | `/readyz` | 就绪检查（含 DB/Redis 连通性） |

### 4.11 统一响应格式

**成功（单条）**：
```json
{
  "data": {...},
  "meta": {"request_id": "..."}
}
```

**成功（列表，带分页）**：
```json
{
  "data": [...],
  "meta": {
    "request_id": "...",
    "page": 1,
    "page_size": 20,
    "total": 150
  }
}
```
所有列表接口支持 `page`（默认 1）和 `page_size`（默认 20，最大 100）查询参数。

**错误**：
```json
{
  "error_code": "ASSET_NOT_FOUND",
  "message": "资料不存在",
  "detail": {},
  "meta": {"request_id": "..."}
}
```

---

## 5. 安全设计

### 5.1 认证
- JWT (HS256)，token 携带 `user_id` + `tenant_id` + `role`
- Access Token 有效期 30 分钟，Refresh Token 有效期 7 天
- `POST /v1/auth/refresh` 用 Refresh Token 换新 Access Token
- Refresh Token 存入 Redis，支持主动吊销（用户禁用时清除该用户所有 token）
- 注：HS256 为本阶段简化选择，密钥通过环境变量管理；后续可升级为 RS256

### 5.2 多租户隔离
- 所有数据库查询自动注入 `tenant_id` 过滤条件（通过 FastAPI 依赖注入）
- project 通过 `tenant_id` 外键绑定，asset/doc/job 通过 project 链路隔离

### 5.3 密钥安全
- 模型 API Key 使用 AES-256-GCM 加密存储
- 加密密钥从环境变量 `ENCRYPTION_KEY` 读取
- API 响应中 API Key 字段返回掩码值（`sk-****xxxx`）

### 5.4 文件安全
- 上传文件限制类型白名单和最大大小（默认 100MB）
- 存入 MinIO 前计算 SHA-256 哈希用于幂等
- 病毒扫描：本阶段不集成，在文件元数据中预留 `scan_status` 字段，后续接入 ClamAV

### 5.5 URL 导入安全（SSRF 防护）
- 仅允许 http/https 协议
- 禁止访问私有 IP 段（10.x, 172.16-31.x, 192.168.x, 127.x, ::1）
- 限制重定向次数（最多 3 次）
- 设置请求超时（30 秒）

### 5.6 速率限制
- 基于 Redis 的滑动窗口限流
- 默认：每租户 100 次/分钟（可配置）
- 文件上传：每租户 20 次/分钟

---

## 6. 错误处理

### 6.1 错误码分类
- `AUTH_*`：认证相关
- `PROJECT_*`：项目相关
- `ASSET_*`：资料相关
- `ARCH_*`：架构相关
- `DOC_*`：文档相关
- `JOB_*`：任务相关
- `MODEL_*`：模型配置相关
- `SYSTEM_*`：系统内部错误

### 6.2 异常处理
- 自定义 `AppException` 基类，子类对应不同业务异常
- FastAPI 全局异常处理器统一格式化
- 业务异常返回 4xx，系统异常返回 5xx

---

## 7. 测试策略

### 7.1 单元测试
- Service 层业务逻辑
- pytest + mock（不使用 SQLite，因 PostgreSQL 特有类型如 JSONB、UUID 不兼容）

### 7.2 集成测试
- API 端到端
- pytest + httpx.AsyncClient + 测试数据库
- 每个 API 覆盖：正常路径 + 权限不足 + 资源不存在

### 7.3 测试目录
- 各服务下 `tests/` 目录

---

## 8. 可观测性

### 8.1 日志
- JSON 结构化日志
- 每个请求带 `request_id` 贯穿链路

### 8.2 审计
- 关键操作写入 `audit_log` 表（不设外键，防止级联删除影响日志持久性）
- 覆盖：上传、审核、发布、回滚、架构修改、密钥操作

---

## 9. 数据库索引策略

- `user`: 唯一索引 `(email)`，索引 `(tenant_id, status)`
- `project`: 索引 `(tenant_id, status)`
- `asset`: 索引 `(project_id, parse_status)`，唯一索引 `(project_id, file_hash)` 用于幂等
- `architecture`: 索引 `(project_id, status)`
- `architecture_node`: 索引 `(architecture_id, level)`，索引 `(parent_id)`
- `knowledge_doc`: 索引 `(project_id, status)`，索引 `(node_id)`
- `knowledge_doc_version`: 索引 `(doc_id, version)`
- `job`: 索引 `(project_id, status)`，索引 `(celery_task_id)`
- `audit_log`: 索引 `(tenant_id, created_at)`，索引 `(resource_type, resource_id)`

---

## 10. 命名对齐说明

原 `openapi/openapi.yaml` 使用 `/v1/materials`、`/v1/tasks`、`/v1/knowledge-architectures`、`/v1/knowledge-documents`。本设计统一为 `/v1/assets`、`/v1/jobs`、`/v1/architectures`、`/v1/docs`。实施时将同步更新 `openapi.yaml`。

---

## 11. 交付范围确认

| 组件 | 本阶段 | 下一阶段 |
|------|--------|----------|
| services/api | ✅ | |
| packages/shared-models | ✅ | |
| packages/shared-schemas | ✅ | |
| packages/shared-config | ✅ | |
| packages/shared-errors | ✅ | |
| infra/sql (Alembic) | ✅ | |
| docker-compose.yml | ✅ | |
| services/ingestion-worker | | ✅ |
| services/pipeline-worker | | ✅ |
| services/ai-orchestrator | | ✅ |
| apps/web | | ✅ |
