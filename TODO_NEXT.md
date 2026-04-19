---
session_id: cc:2026-04-19-kbsql-v0.53.0-seal
parent_session_id: cc:2026-04-19-kbsql-bridge-design
source: claude-code
---

# TODO_NEXT

## 上次停在
- 版本：v0.53.0 | 分支：`test-v-0-53-a` (推到 origin)
- 最后完成：bridge 服务 + REST + MCP + 文档 + Phase 8 审计 + 修复 + ADR (HEALTH B+)
- 94 测试全过 (9.9s)

## v0.53 已封板内容
- ✅ services/bridge/ 完整服务（parsers/watchers/writers/llm/config/main）
- ✅ services/mcp-server/ FastMCP 8 工具
- ✅ packages/bridge-utils/ 摘要+分类（无 LLM）
- ✅ /v1/bridge/* 9 个 REST 端点
- ✅ 3 个新 SQLAlchemy 模型 + Alembic migration（未应用）
- ✅ Hogwarts-KB 仓 .bridge-config.yml + .bridge-managed 标记
- ✅ docs/api/bridge-service.md + docs/operations/bridge-deployment.md
- ✅ docs/audits/v0.53.0-bridge-audit.md（Phase 8 跨审计 + 9 修复 + 3 ADR）

## 部署前 checklist (用户必须做)
1. **应用 3 个待执行 migration**（按顺序）：
   - `y4z5a6b7c8d9` (v0.51 tenant tier + user org)
   - `z5a6b7c8d9e0` (v0.51 stage order + skill + ontology)
   - `a6b7c8d9e0f1` (v0.53 bridge tables)
   - 命令：`cd infra/sql && alembic upgrade head`
2. **轮换 .env 占位密钥**：JWT_SECRET 和 ENCRYPTION_KEY 仍是 change_me
3. **下载 NLTK punkt 数据**：`python -c "import nltk; nltk.download('punkt_tab', quiet=True); nltk.download('punkt', quiet=True)"`
4. **启动 bridge watcher**（可选）：`python -m bridge watch`
5. **配置 Claude Code/Desktop MCP**：见 docs/api/bridge-service.md

## v0.54 候选任务

### 高优先级（v0.54 应做）
- **bridge_ingest Celery stage**（v0.53 deferred per ADR-002）
  - 创建 `services/pipeline-worker/worker/stages/bridge_ingest.py`
  - 在 `bridge.tasks` 添加 Celery task
  - 修改 `kb_watcher.run_watcher()` 默认注入 enqueue_fn
  - 移除 `/v1/bridge/mappings` 的 stub 注释
- **POST /v1/bridge/ingest/url**：暴露已实现的 trafilatura URL 解析
- **自动写回 hook**：在 pipeline-worker 的 review_notify stage 后触发 kb_writer
- **bridge 写端点 RBAC**：Depends(require_permission("bridge:write"))（ADR-003）
- **`asyncio.to_thread` 包装 run_watcher** 用于多 KB 并发场景

### 中优先级（v0.54 可做）
- **malformed YAML frontmatter 优雅处理**（S2-M5）
- **bridge 模型补 tenant_id**（S2-L6）
- **deployment-guide.md 加 bridge 交叉引用**（S3-M2）
- **ENCRYPTION_KEY 命令注释清晰化**（S3-M4）
- **将 docling/whisperx/playwright 重型依赖移到 docker image** 而非 pip 安装步骤

### 低优先级（v0.55+）
- v0.52 遗留 UI 项：I-001 (tenant quota indicator) / I-002 (pipeline editor) / I-003 (ontology graph)
- pipeline-worker `9-stage` docstring 修正为 `7-stage`（S1-L7）
- Bridge 监控页面（v0.53 没有 UI）

## 注意事项
- bridge 写入限制硬编码：仅 wiki/summaries/ + wiki/analyses/，不要扩展（破坏安全契约）
- BRIDGE_LLM_STRICT=true 是默认值，**不要改成 false** 除非显式要换 provider
- v0.53 watcher 是 detect-only — 不要假定 BridgeSyncRecord 自动有数据
- migration 必须按顺序应用，否则 a6b7c8d9e0f1 找不到 down_revision

## 相关入口
- 开发计划：[docs/dev-plans/dev-plan-v0.53.md](docs/dev-plans/dev-plan-v0.53.md)
- 审计报告：[docs/audits/v0.53.0-bridge-audit.md](docs/audits/v0.53.0-bridge-audit.md)
- 用户文档：[docs/api/bridge-service.md](docs/api/bridge-service.md)
- 部署文档：[docs/operations/bridge-deployment.md](docs/operations/bridge-deployment.md)
- 工具栈调研：[Hogwarts-KB wiki/analyses/kbsql-bridge-toolkit-research.md](../Hogwarts-Knowledge-Base/wiki/analyses/kbsql-bridge-toolkit-research.md)
