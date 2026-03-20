# KB Platform 编码标准 — 测试规范

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**优先级**：必读（所有任务）

---

## 1. 测试框架

| 端 | 框架 | 运行命令 |
|----|------|---------|
| Python 后端 | pytest + pytest-asyncio | `pytest services/{service}/tests/` |
| Next.js 前端 | vitest | `cd apps/web && npx vitest` |

---

## 2. 文件组织

### 2.1 后端测试目录

```
services/{service}/
└── tests/
    ├── conftest.py          # fixtures（数据库会话、测试客户端、mock 对象）
    ├── helpers/             # 共享测试工具函数
    ├── test_{module}.py     # 单元测试
    └── test_{module}_integration.py  # 集成测试
```

### 2.2 前端测试目录

```
apps/web/src/
├── __tests__/
│   ├── components/          # 组件测试
│   │   └── KnowledgeUnitCard.test.tsx
│   ├── hooks/               # Hook 测试
│   │   └── useKnowledgeUnits.test.ts
│   └── lib/                 # 工具函数测试
│       └── api.test.ts
```

### 2.3 命名规范

- Python: `test_{module}.py`，测试函数 `test_{behavior}` 或 `test_{method}_{scenario}`
- TypeScript: `{Component}.test.tsx` 或 `{module}.test.ts`

---

## 3. 后端测试规则

### 3.1 异步测试

项目使用 pytest-asyncio auto 模式，所有 async 测试函数自动识别：

```python
# conftest.py 或 pyproject.toml 中已配置 asyncio_mode = "auto"

async def test_create_knowledge_unit(db_session, test_client):
    response = await test_client.post("/api/v1/knowledge-units", json={...})
    assert response.status_code == 201
```

### 3.2 Fixtures

- 数据库会话、测试客户端、认证 token 等公共 fixture 定义在 `conftest.py`
- 每个测试函数使用独立的数据库事务，测试结束自动回滚
- 共享测试数据工厂函数放在 `tests/helpers/`

### 3.3 Mock 规则

- **单元测试**：mock 所有外部依赖（MinIO、LLM、Redis、外部 HTTP 调用）
- **集成测试**：使用真实 PostgreSQL 测试数据库，mock 外部服务
- 使用 `unittest.mock.patch` 或 `pytest-mock` 的 `mocker` fixture
- Mock 对象必须验证调用参数（不仅验证是否被调用）

```python
async def test_parse_file_calls_minio(mocker):
    mock_download = mocker.patch("worker.tasks.storage.download_file")
    mock_download.return_value = b"file content"

    await parse_file("file-123")

    mock_download.assert_called_once_with(bucket="uploads", key="file-123")
```

### 3.4 最低测试要求

- 每个新增 API 端点至少 1 个正常路径测试 + 1 个异常路径测试
- 每个新增 Service 方法至少 1 个单元测试
- 每个新增 Celery 任务至少 1 个成功测试 + 1 个失败/重试测试

---

## 4. 前端测试规则

### 4.1 组件测试

- 使用 vitest + @testing-library/react
- 测试用户可见行为，不测试内部实现细节
- 必须测试：渲染、用户交互、加载状态、错误状态、空状态

### 4.2 Hook 测试

- 使用 `renderHook` 测试自定义 Hook
- Mock API 调用，验证状态变化

---

## 5. 测试质量要求

### 5.1 测试隔离

- 每个测试函数必须独立运行，不依赖其他测试的执行顺序
- 禁止测试之间共享可变状态
- 禁止测试依赖外部网络（所有外部调用必须 mock）

### 5.2 测试可读性

- 测试函数名描述被测试的行为，不是被测试的方法名
- 使用 Arrange-Act-Assert 模式
- 每个测试只验证一个行为

```python
# 正确 — 描述行为
async def test_returns_404_when_knowledge_unit_not_found():
    ...

# 错误 — 描述方法名
async def test_get_knowledge_unit():
    ...
```

### 5.3 覆盖率

- 跟踪覆盖率但不设硬性门槛
- 优先覆盖关键业务路径（创建、更新、删除、权限检查）
- 不追求 100%，但所有新增代码应有对应测试

---

## 6. 已知错误模式

编写测试时，参考 `docs/experience/common-errors.md` 中记录的历史错误模式，确保同类问题有回归测试覆盖。
