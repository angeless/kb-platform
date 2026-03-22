# KB Platform 编码标准 — 核心规范

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**优先级**：必读（所有任务）

---

## 第一部分：架构分层规则

### 1.1 层级定义

| 层 | 位置 | 职责 | 禁止 |
|----|------|------|------|
| Routers（接入层） | `services/{service}/routers/` | 处理 HTTP 请求/响应，调用 Service 层，返回 Pydantic schema | 包含业务逻辑、直接操作数据库 |
| Services（业务层） | `services/{service}/services/` | 业务逻辑，调用 shared-models 操作数据库，返回 Pydantic schema | 处理 HTTP 细节（status code、headers） |
| Shared Packages（共享层） | `packages/shared-{name}/` | Models、Schemas、Config、Errors，跨服务共享 | 包含业务逻辑、依赖具体服务 |
| Workers（异步处理层） | `services/{worker}/worker/tasks/` | Celery 任务，调用 Service 或通过 shared-models 直接访问数据库 | 导入 services/api 的代码 |
| Frontend（展示层） | `apps/web/src/` | Next.js 页面和组件，通过 lib/api.ts 调用后端 API | 直接导入后端代码、直接访问数据库 |

### 1.2 依赖方向

```
Routers → Services → Shared Packages ← Workers
Frontend → API (REST only)
```

### 1.3 跨层禁令

- **禁止** Routers 直接导入 `shared-models`（必须经过 Service 层）
- **禁止** Workers 导入 `services/api/` 下的任何模块
- **禁止** Frontend 导入后端 Python 代码
- **禁止** 任何服务直接导入其他服务的内部模块（跨服务通信走 API 或 Celery 任务）
- **禁止** shared packages 之间的循环依赖

---

## 第二部分：命名规范

### 2.1 Python

| 类别 | 规范 | 示例 |
|------|------|------|
| 文件名 | snake_case | `knowledge_unit_service.py` |
| 函数/变量 | snake_case | `get_knowledge_unit()`, `unit_count` |
| 类名 | PascalCase | `KnowledgeUnitService` |
| 常量 | UPPER_SNAKE_CASE | `MAX_UPLOAD_SIZE_MB` |
| 私有方法 | 前缀下划线 | `_validate_input()` |

### 2.2 TypeScript

| 类别 | 规范 | 示例 |
|------|------|------|
| 函数/变量 | camelCase | `getKnowledgeUnit()`, `unitCount` |
| 组件 | PascalCase | `KnowledgeUnitCard` |
| 类型/接口 | PascalCase | `KnowledgeUnit`, `ApiResponse` |
| 常量 | UPPER_SNAKE_CASE 或 camelCase | `MAX_FILE_SIZE`, `apiBaseUrl` |

### 2.3 文件命名

| 类别 | 规范 | 示例 |
|------|------|------|
| Python Service | `{entity}_service.py` | `knowledge_unit_service.py` |
| Python Router | `{entity}.py` | `knowledge_units.py` |
| Python Model | `{entity}.py` | `knowledge_unit.py` |
| Python Schema | `{entity}.py` | `knowledge_unit.py` |
| TypeScript 页面 | `{feature}/page.tsx` | `knowledge-base/page.tsx` |
| TypeScript 组件 | `{ComponentName}.tsx` | `KnowledgeUnitCard.tsx` |

### 2.4 其他命名

| 类别 | 规范 | 示例 |
|------|------|------|
| 数据库表名 | snake_case 复数 | `users`, `knowledge_units` |
| API 端点 | `/api/v1/{resource}` kebab-case 复数 | `/api/v1/knowledge-units` |
| Celery 任务名 | `{service}.{action}` | `ingestion.parse_file` |
| Alembic 迁移 | 自动生成 hash 前缀 | `a1b2c3d4_add_status_column.py` |
| Git commit | `{type}(v{X.Y.Z}): {description}` | `feat(v0.39.0): add file upload endpoint` |
| Git commit 类型 | feat / fix / refactor / test / docs / chore | — |

---

## 第三部分：代码结构

### 3.1 Python 文件模板

```python
"""模块文档字符串：简要描述该模块的职责。"""

# stdlib
import logging
from datetime import datetime
from uuid import UUID

# third-party
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# shared packages
from shared_models.knowledge_unit import KnowledgeUnit
from shared_schemas.knowledge_unit import KnowledgeUnitResponse
from shared_errors.exceptions import NotFoundError

# local
from ..deps import get_db_session
from ..services.knowledge_unit_service import KnowledgeUnitService

logger = logging.getLogger(__name__)
```

### 3.2 导入分组规则

1. 标准库（stdlib）
2. 第三方库（third-party）
3. 共享包（shared packages：shared_models, shared_schemas, shared_config, shared_errors）
4. 本地模块（local：同服务内的其他模块）

各组之间空一行。每组内按字母排序。

### 3.3 类型注解

- **所有函数签名必须有类型注解**（参数和返回值）
- 允许使用 Python 3.12 语法（如 `type` 语句、`X | Y` 联合类型）
- 复杂类型使用 `TypeAlias` 或 `type` 语句定义

```python
# 正确
async def get_unit(unit_id: UUID, session: AsyncSession) -> KnowledgeUnit | None:
    ...

# 错误 — 缺少类型注解
async def get_unit(unit_id, session):
    ...
```

### 3.4 Pydantic 模型

- 所有 API 输入使用 Pydantic 模型（Request Schema）
- 所有 API 输出使用 Pydantic 模型（Response Schema）
- Schema 统一定义在 `packages/shared-schemas/`
- 使用 `model_config = ConfigDict(from_attributes=True)` 支持 ORM 转换

### 3.5 SQLAlchemy 模型

- 所有模型继承自 `shared_models.base.Base`
- 统一定义在 `packages/shared-models/`
- 必须包含 `id`（UUID 主键）、`tenant_id`、`created_at`、`updated_at` 字段
- 关系用 `relationship()` 声明，外键用 `ForeignKey` 约束

### 3.6 函数长度

- **推荐** < 50 行
- **硬限制** < 100 行（超过必须拆分）
- 每个函数只做一件事（单一职责）

### 3.7 文件职责

- 每个文件有明确的单一职责
- 如果一个文件超过 300 行，考虑拆分
- 避免"utils.py 垃圾桶"——工具函数按领域拆分（如 `utils/storage.py`、`utils/crypto.py`）

---

## 第四部分：AI 自检清单

每次提交代码前，必须逐项确认：

- [ ] 没有硬编码的密钥、密码、token
- [ ] 没有无 ticket 编号的 TODO 注释
- [ ] 没有被注释掉的代码块（删除而非注释）
- [ ] 没有未使用的 import
- [ ] 所有函数签名有完整的类型注解
- [ ] 所有新增 API 端点有对应的 Pydantic 请求/响应 Schema
- [ ] 依赖方向正确（无跨层违规导入）
- [ ] 函数长度在限制范围内
- [ ] 新增模块有模块文档字符串
- [ ] 变量命名符合本文件第二部分规范
