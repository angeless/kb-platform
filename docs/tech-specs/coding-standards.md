# KB Platform 编码标准

**文档版本**：v0.39.0
**最后更新**：2026-03-20
**适用范围**：KB Platform 全部后端服务（Python 3.12）和前端应用（Next.js 15 / TypeScript）

---

## 拆分文件索引

| 文件 | 包含内容 | 优先级 | 何时加载 |
|------|---------|--------|---------|
| [coding-standards-core.md](coding-standards-core.md) | 架构分层 + 命名规范 + 代码结构 + AI 自检 | **必读** | 所有任务 |
| [coding-standards-error-handling.md](coding-standards-error-handling.md) | 错误处理铁律 | **必读** | 所有任务 |
| [coding-standards-testing.md](coding-standards-testing.md) | 测试规范 | **必读** | 所有任务 |
| [coding-standards-security.md](coding-standards-security.md) | 安全基线 | **必读** | 所有任务 |
| [coding-standards-data.md](coding-standards-data.md) | 外部调用 + 数据持久化 | **条件必读** | 涉及 API 调用 / 数据库时 |
| [coding-standards-frontend.md](coding-standards-frontend.md) | 前端规范 | **条件必读** | 涉及前端时 |
| [coding-standards-infra.md](coding-standards-infra.md) | 资源管理 + 日志 + 配置 | **可选** | 涉及基础设施时 |

---

## 加载规则

1. **所有任务必读**：core、error-handling、testing、security 四个文件。
2. **条件必读**：当任务涉及数据库/外部调用时读 data；涉及前端时读 frontend。
3. **可选**：涉及基础设施（Docker、日志、配置）时读 infra。
4. **仅读本索引文件而不读子文件，视为未完成规范加载，禁止进入 Phase 2 编码。**

---

## 关联文件

| 文件 | 内容 | 关系 |
|------|------|------|
| [architecture.md](architecture.md) | 系统架构 | 编码标准在架构约束下执行 |
| [dev-governance.md](dev-governance.md) | 开发治理 | Phase 2 编码时参照编码标准 |
| [testing-strategy.md](testing-strategy.md) | 测试策略 | 与 coding-standards-testing.md 互补 |
