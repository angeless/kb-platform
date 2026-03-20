# KB Platform 测试策略

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**适用范围**：KB Platform 全部后端服务和前端应用

---

## §1 测试类型分类

| 缩写 | 类型 | 定义 | 框架 | 运行位置 |
|------|------|------|------|---------|
| UT | 单元测试 | 测试单个函数/方法，mock 外部依赖 | pytest / vitest | 本地 + CI |
| IT | 集成测试 | 测试多模块协作，使用真实 DB | pytest + testcontainers 或真实 PostgreSQL | 本地 + CI |
| API | API 测试 | 测试 HTTP 端点，验证请求/响应 | pytest + httpx.AsyncClient (FastAPI TestClient) | 本地 + CI |
| E2E | 端到端测试 | 测试完整用户流程，前后端联动 | Playwright / Cypress | CI only |
| SMK | 冒烟测试 | 快速验证核心功能未被破坏 | pytest -m smoke / vitest --grep smoke | 本地 + CI |
| PERF | 性能测试 | 验证响应时间、吞吐量、资源使用 | locust / k6 | 按需 |
| SEC | 安全测试 | 验证认证、授权、注入防护 | pytest (含在 API 测试中) | CI |

## §2 测试频次与触发时机

| 层级 | 触发时机 | 包含测试类型 | 预期耗时 |
|------|---------|-------------|---------|
| Per-Commit | 每次 Phase 3 门禁 | UT + SMK + Lint + Type Check | < 3 分钟 |
| Per-Task | 每个 vX.Y.Z 任务完成时 | UT + IT + API + SMK | < 10 分钟 |
| Per-Version | 版本封板前 (vX.Y.0 完成时) | UT + IT + API + E2E + SMK + SEC | < 30 分钟 |
| Per-Release | 发布前 | 全量 + PERF (如需要) | < 60 分钟 |

## §3 各类型通用五步流程

所有测试类型统一遵循五步流程：

### 步骤 1：准备 (Prepare)
- 确认测试目标和范围
- 准备测试数据和环境
- 确认依赖服务状态（DB、Redis、MinIO）

### 步骤 2：设计 (Design)
- 按"正常路径 → 边界条件 → 异常路径"顺序设计用例
- 每个 API 端点至少：1 个正常 + 1 个权限错误 + 1 个参数错误
- 参照 `docs/experience/common-errors.md` 避免已知错误

### 步骤 3：执行 (Execute)
- 后端：`python3 -m pytest {path} -v`
- 前端：`cd apps/web && npx vitest run`
- 冒烟：`python3 -m pytest -m smoke -v`
- 按标记选择性运行：`python3 -m pytest -m "unit" -v`

### 步骤 4：验证 (Verify)
- 确认所有测试通过（0 failures）
- 检查测试覆盖了目标功能的关键路径
- 新引入的失败必须修复（已知失败除外）

### 步骤 5：记录 (Record)
- 记录测试结果到测试报告
- 记录新发现的问题
- 更新 common-errors.md（如发现新的通用错误模式）

## §4 测试用例编写规范

### 4.1 Python 测试用例
```python
# 文件命名: test_{module}.py
# 函数命名: test_{scenario}_{expected_result}

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_project_success(client: AsyncClient, auth_headers: dict):
    """正常创建项目应返回 201 和项目数据。"""
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "desc"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"


@pytest.mark.asyncio
async def test_create_project_unauthorized(client: AsyncClient):
    """未认证用户创建项目应返回 401。"""
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Test"},
    )
    assert response.status_code == 401
```

### 4.2 TypeScript 测试用例
```typescript
// 文件命名: {Component}.test.tsx
// 描述: describe('{Component}', () => { it('should {expected}', ...) })

import { render, screen } from '@testing-library/react'
import { StatusBadge } from '@/components/status-badge'

describe('StatusBadge', () => {
  it('should render success status with green color', () => {
    render(<StatusBadge status="completed" />)
    expect(screen.getByText('completed')).toBeInTheDocument()
  })
})
```

### 4.3 用例编写规则
- 每个测试函数只测一个行为
- 使用 AAA 模式（Arrange-Act-Assert）
- 测试函数名必须描述场景和预期结果
- 禁止测试之间共享可变状态
- Mock 外部服务但不 mock 被测对象本身
- 异步测试必须使用 `@pytest.mark.asyncio`

## §5 测试文件夹路径管理

### 5.1 后端测试目录
```
services/api/tests/           # API 服务测试（主测试目录）
├── conftest.py               # 共享 fixtures
├── test_auth.py              # 认证测试
├── test_projects.py          # 项目 CRUD 测试
├── test_assets.py            # 资产管理测试
├── test_docs.py              # 文档管理测试
├── test_search.py            # 搜索测试
├── ...                       # 其他模块测试
services/ingestion-worker/tests/  # 解析器测试
services/ai-orchestrator/tests/   # AI 编排测试
```

### 5.2 前端测试目录
```
apps/web/src/__tests__/       # 前端测试目录
├── components/               # 组件测试
├── hooks/                    # Hook 测试
├── lib/                      # 工具函数测试
└── pages/                    # 页面集成测试
```

### 5.3 测试数据目录
```
tests/fixtures/               # 共享测试数据（如需要）
├── sample_files/             # 测试用上传文件
└── mock_responses/           # Mock 的外部服务响应
```

### 5.4 按标记选择性运行

配置 pytest markers（在 pyproject.toml 中）:
```ini
[tool.pytest.ini_options]
markers = [
    "smoke: 冒烟测试，快速验证核心功能",
    "unit: 单元测试",
    "integration: 集成测试，需要真实数据库",
    "api: API 端点测试",
    "slow: 耗时较长的测试",
]
```

运行示例:
- 仅冒烟测试: `python3 -m pytest -m smoke`
- 排除慢测试: `python3 -m pytest -m "not slow"`
- 仅单元测试: `python3 -m pytest -m unit`

## §6 测试报告命名规范

| 报告类型 | 命名格式 | 存放路径 | 示例 |
|---------|---------|---------|------|
| 任务测试报告 | `test-report-vX.Y.Z.md` | `docs/versions/` | `test-report-v0.39.4.md` |
| 版本测试报告 | `test-report-vX.Y.md` | `docs/versions/` | `test-report-v0.39.md` |
| Bug 修复清单 | `bugfix-list-vX.Y.Z-{a}.md` | `docs/versions/` | `bugfix-list-v0.39.0-1.md` |

报告必须包含：
- 测试执行时间
- 测试环境（本地/CI、Python/Node 版本）
- 测试结果汇总（passed/failed/skipped）
- 失败用例详情及原因分析
- 新发现的问题
- 覆盖率数据（如有）

## §7 测试数据管理

### 7.1 原则
- 每个测试自行创建和清理测试数据
- 使用 pytest fixtures 管理生命周期
- 禁止依赖特定的数据库状态
- 敏感数据使用 faker 生成

### 7.2 后端 Fixtures 示例
```python
# conftest.py
@pytest.fixture
async def test_user(db_session):
    """创建测试用户，测试后自动清理。"""
    user = User(email="test@example.com", name="Test User")
    db_session.add(user)
    await db_session.commit()
    yield user
    await db_session.delete(user)
    await db_session.commit()

@pytest.fixture
async def auth_headers(test_user):
    """生成认证 header。"""
    token = create_access_token(user_id=test_user.id)
    return {"Authorization": f"Bearer {token}"}
```

### 7.3 测试数据库
- 单元测试：mock database（不需要真实 DB）
- 集成/API 测试：使用独立测试数据库 `kb_platform_test`
- 每个测试 session 自动创建/销毁测试表
- 使用事务回滚保证测试隔离

---

## 关联文件

| 文件 | 关系 |
|------|------|
| [coding-standards-testing.md](coding-standards-testing.md) | 互补：本文件定义"何时测、测什么、如何组织"，编码标准定义"怎么写测试代码" |
| [dev-governance.md](dev-governance.md) | Phase 3 测试阶段引用本文件；§3.3/§3.5 定义测试操作指南和报告模板 |
| [architecture.md](architecture.md) | 测试范围覆盖架构中定义的所有模块和数据流 |
