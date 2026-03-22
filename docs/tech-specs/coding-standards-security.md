# KB Platform 编码标准 — 安全基线

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**优先级**：必读（所有任务）

---

## 1. 密钥管理

- **禁止** 在代码中硬编码密钥、密码、token、API key
- 所有密钥通过环境变量注入，使用 Pydantic `BaseSettings` 读取
- 本地开发使用 `.env` 文件（已在 `.gitignore` 中排除）
- 生产环境通过 `Settings.validate_production_secrets()` 校验，拒绝使用默认密钥启动
- 敏感配置值使用 AES-256 加密存储（通过 `utils/crypto.py`）

---

## 2. 认证与授权

### 2.1 JWT Token

- Access Token 有效期 30 分钟
- Refresh Token 有效期 7 天
- Token 中只包含 `user_id`、`tenant_id`、`role`，不包含敏感信息
- Token 签名密钥通过环境变量配置，生产环境必须使用强密钥

### 2.2 密码

- 使用 bcrypt 哈希（通过 passlib）
- 禁止明文存储、禁止 MD5/SHA1 哈希
- 密码最小长度 8 位

### 2.3 RBAC

- 权限检查在 Router 层通过 FastAPI Dependency 实现
- 每个需要权限控制的端点必须声明所需权限
- 禁止在 Service 层之后才做权限检查（为时已晚）

```python
@router.get("/knowledge-units/{unit_id}")
async def get_unit(
    unit_id: UUID,
    current_user: User = Depends(require_permission("knowledge_unit:read")),
):
    ...
```

---

## 3. 输入验证

- 所有 API 输入通过 Pydantic Schema 校验，不信任客户端数据
- 文件上传必须验证文件类型（MIME type + 扩展名双重检查）
- 文件大小通过 `max_upload_size_mb` 配置项限制
- 字符串输入检查长度上限，防止超大 payload

---

## 4. SQL 注入防护

- **必须** 使用 SQLAlchemy ORM 操作数据库
- 如果必须写原始 SQL，**必须** 使用参数化查询（`text()` + `bindparams`）
- **禁止** 字符串拼接 SQL

```python
# 正确 — 参数化查询
from sqlalchemy import text
stmt = text("SELECT * FROM users WHERE tenant_id = :tid")
result = await session.execute(stmt, {"tid": tenant_id})

# 禁止 — 字符串拼接
stmt = f"SELECT * FROM users WHERE tenant_id = '{tenant_id}'"
```

---

## 5. 租户隔离

- **所有数据库查询必须包含 `tenant_id` 过滤条件**
- 禁止不带 `tenant_id` 的全表查询（管理员后台除外，需明确标注）
- 在 Service 层统一注入 `tenant_id`，不依赖前端传入
- 文件存储（MinIO）按 tenant_id 分 bucket 或分路径

---

## 6. 网络安全

### 6.1 CORS

- 使用显式 origin 白名单，禁止生产环境使用 `*` 通配符
- 仅允许必要的 HTTP 方法和 Headers

### 6.2 速率限制

- 所有 API 端点设置速率限制
- 认证端点（登录、注册、忘记密码）使用更严格的限制
- 返回 429 状态码，响应头包含 `Retry-After`

---

## 7. 审计追踪

- 所有状态变更操作（创建、更新、删除、权限变更）通过 `audit_service` 记录
- 审计日志包含：操作类型、操作者、租户、目标资源、时间戳、变更内容
- 审计日志不可删除、不可修改

---

## 8. 依赖安全

- 添加新依赖前必须检查许可证兼容性
- 定期更新依赖版本，修复已知安全漏洞
- 生产镜像不包含开发依赖
- Docker 镜像使用非 root 用户运行
