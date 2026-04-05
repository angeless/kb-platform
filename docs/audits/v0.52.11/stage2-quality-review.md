# Stage 2: 质量工程审计 — v0.52.11

## 审计概要
- **版本**: v0.52.11
- **审计日期**: 2026-04-04
- **审计范围**: v0.52.1 ~ v0.52.11 全部新增/修改代码
- **审计人**: Claude Code (Phase 8 Stage 2)

## 检查项与结果

### 1. 异步/同步 Redis 一致性
- **[I-001] agent.py 在 async handler 中使用同步 Redis** — Important
  - 文件: `services/api/app/routers/agent.py`
  - 描述: rate limiter 使用 `get_redis_client()`（同步）在 async endpoint 中，阻塞事件循环
  - 修复: 迁移至 `get_async_redis_client()`，`incr`/`expire` 改为 `await`，添加 `finally: await r.aclose()`
  - 状态: **已修复** (commit `a5a9f4d`)

### 2. 资源泄漏
- **[I-002] review_notify.py Redis 连接未关闭** — Important
  - 文件: `services/pipeline-worker/worker/stages/review_notify.py`
  - 描述: `get_redis_client()` 返回的连接在函数结束后未显式关闭
  - 修复: 添加 `try/finally: r.close()` 包裹使用块
  - 状态: **已修复** (commit `a5a9f4d`)

### 3. 死代码清理
- **[I-003] 两处无效 `import redis`** — Important
  - 文件: `services/pipeline-worker/worker/tasks.py`, `services/pipeline-worker/worker/stages/review_notify.py`
  - 描述: 顶部 `import redis` 但实际使用 `shared_config.settings.get_redis_client`
  - 修复: 移除两处无用 import
  - 状态: **已修复** (commit `a5a9f4d`)

### 4. HTTP 响应规范
- **[M-001] assets.py Content-Disposition 不符合 RFC 5987** — Minor
  - 文件: `services/api/app/routers/assets.py`
  - 描述: 下载端点的 `Content-Disposition` header 直接拼接中文文件名，部分浏览器无法正确解析
  - 修复: 添加 ASCII fallback `filename="..."` + UTF-8 编码 `filename*=UTF-8''...`（RFC 5987）
  - 状态: **已修复** (commit `a5a9f4d`)

### 5. 错误处理一致性
- **[M-002] 手动 JSONResponse(403) 不走统一错误处理** — Minor
  - 文件: `services/api/app/routers/projects.py`, `services/api/app/routers/architectures.py`
  - 描述: 确认码验证失败时使用 `JSONResponse(status_code=403, ...)` 而非异常路径，绕过全局错误处理器
  - 修复: 替换为 `raise ForbiddenException(error_code=ErrorCode.CONFIRMATION_INVALID, ...)`，新增 `CONFIRMATION_INVALID` 错误码
  - 状态: **已修复** (commit `a5a9f4d`)

### 6. 测试质量
- **[M-003] test_confirmation.py 测试不够完整** — Minor
  - 文件: `services/api/tests/test_confirmation.py`
  - 描述: `test_wrong_user_returns_false` 仅验证错误用户被拒，未验证正确用户仍可使用 token
  - 修复: 重命名为 `test_wrong_user_returns_false_but_token_survives`，添加断言正确用户验证仍通过
  - 状态: **已修复** (commit `a5a9f4d`)

### 7. 代码去重
- **[M-004] 租户隔离检查重复 7 处** — Minor
  - 文件: 多个 router 文件
  - 描述: `select(Project).where(Project.id == project_id, Project.kb_id == kb_id)` 内联查询散落在 skills.py、ontology.py 等多个文件
  - 修复: 提取为 `ensure_project_access()` 共享函数置于 `deps.py`，各 router 统一调用
  - 状态: **已修复** (commit `a5a9f4d`)

## 统计

| 级别 | 发现数 | 已修复 |
|------|--------|--------|
| Critical | 0 | 0 |
| Important | 3 | 3 |
| Minor | 4 | 4 |
| **合计** | **7** | **7** |

## 结论
Stage 2 所有发现均已修复。通过。
