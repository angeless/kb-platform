---
session_id: cc:2026-04-19-kbsql-v0.54.0-seal
parent_session_id: cc:2026-04-19-kbsql-v0.53.0-seal
source: claude-code
---

# TODO_NEXT

## 上次停在
- 版本：v0.54.0 | 分支：`test-v-0-54-a`（已推到 origin）
- 最后完成：bridge graph + visual augmentation + Phase 8 审计 + 12 修复 + 5 ADR
- 153 测试全过 (22.3s) — 较 v0.53 增加 59 测试

## v0.54 完成内容

- ✅ packages/bridge-graph/ — Kuzu 嵌入式图 DB（17 测试）
- ✅ packages/bridge-visual/ — 读者画像 + mermaid + outline（18 测试）
- ✅ services/api/app/routers/bridge.py — 4 个新 REST 端点
- ✅ services/mcp-server/mcp_server/server.py — 5 个新 MCP 工具
- ✅ services/pipeline-worker/worker/stages/bridge_ingest.py — Celery stage 落地
- ✅ services/bridge/bridge/writers/kb_writer.py — `augment_existing_in_place()` 安全契约写回
- ✅ docs/api/bridge-graph.md + docs/api/bridge-visual.md
- ✅ docs/audits/v0.54.0-bridge-audit.md（HEALTH B+）
- ✅ docs/dev-plans/dev-plan-v0.54.md + ADR-004/005
- ✅ Hogwarts-KB .gitignore + .bridge-config.yml 更新
- ✅ services/api/app/main.py CORS X-Requested-With 修复

## 部署前 checklist (从普通 Terminal 跑)

```bash
cd ~/knowledge_SQL && source .venv/bin/activate

# 1. 应用 4 个待执行 migration（v0.51 两个 + v0.53 一个 + 实际上 v0.54 没新增）
./scripts/apply_pending_migrations.sh

# 2. 安装 v0.54 新包
pip install -e ./packages/bridge-graph -e ./packages/bridge-visual

# 3. 在 .env 启用新功能
echo "
BRIDGE_GRAPH_ENABLED=true
BRIDGE_VISUAL_ENABLED=true
BRIDGE_VISUAL_DRYRUN=false  # 设 true 仅观察不写入
" >> .env

# 4. Hogwarts-KB .gitignore 已加 .bridge-state/（v0.54 commit 含）

# 5. 启动 bridge watcher
python -m bridge watch

# 6. 跑全量同步（首次）
python -m bridge sync-once
```

## v0.55 候选任务（按 ROI）

### 高优（Phase 8 审计 deferred 项）

- **bridge_ingest 包装为 Celery task**（ADR-005 deferred）
  - 当前是 sync function；v0.55 加 `bridge.tasks.bridge_ingest_async`
- **VisualAugmentRequest max_length** (S2-M1) — 防 DoS
- **bridge_ingest 暴露 graph_error 到 BridgeOperation.detail** (S2-M3)
- **decision-tree flowchart**（when has_branches=True）— 当前只生成 flowchart/state，分支型不生成
- **bridge 写端点 RBAC**（ADR-003 仍延后）— `Depends(require_permission("bridge:write"))`

### 中优

- LLM_DEEP 抽取模式 — graphiti-core + GLM-4 关系抽取
- POST /v1/bridge/ingest/url — 暴露 trafilatura URL 解析
- POST /v1/bridge/graph/cypher — 受限 cypher 子集端点（高权限）
- Sankey / sequence diagram 支持
- bridge_visual 的 GLM-4V polish（图标签优化）
- Per-file opt-out frontmatter（`bridge_visual: skip`）

### 低优 / 性能

- Graph DB read-only 模式（高并发读场景）
- v0.55 把 graphiti-core 从 optional dep 移除（如不打算用）

## v0.52 永久延后

- I-001 / I-002 / I-003 UI 项（前端 lazy loaded）

## 注意事项

- bridge_visual.augment_existing_in_place 是**唯一**允许修改 wiki/concepts/、wiki/howtos/、
  wiki/entities/、lessons/、memory/、raw-sources/ 的写函数。其他写仍走 wiki/summaries+analyses/。
- BRIDGE_VISUAL_DRYRUN=true 让 visual 计算但不写回，调试用。
- BRIDGE_GRAPH_ENABLED=true 之前**必须**确保 .bridge-state/ 在 .gitignore — 否则 Kuzu DB 会被 obsidian-git 提交到 GitHub。

## 相关入口

- 用户文档：[docs/api/bridge-graph.md](docs/api/bridge-graph.md) + [docs/api/bridge-visual.md](docs/api/bridge-visual.md)
- 部署文档：[docs/operations/bridge-deployment.md](docs/operations/bridge-deployment.md)
- 审计报告：[docs/audits/v0.54.0-bridge-audit.md](docs/audits/v0.54.0-bridge-audit.md)
- 开发计划：[docs/dev-plans/dev-plan-v0.54.md](docs/dev-plans/dev-plan-v0.54.md)
- KB 交接：see Hogwarts-KB `wiki/howtos/kbsql-bridge-v054-handoff.md`
