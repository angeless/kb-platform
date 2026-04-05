# Stage 1: 规格合规审计 — v0.52.11

## 审计概要
- **版本**: v0.52.11
- **审计日期**: 2026-04-04
- **审计范围**: v0.52.1 ~ v0.52.11 全部新增/修改代码
- **审计人**: Claude Code (Phase 8 Stage 1)

## 检查项与结果

### 1. 端点注册与 OpenAPI 一致性
- 检查范围: `services/api/app/routers/` 下所有路由
- 结果: **通过** — 所有新增端点（skills CRUD, confirmation, ontology extract）均已注册在 router 中，路径与 OpenAPI schema 一致

### 2. 租户隔离（跨租户访问防护）
- 检查范围: 所有接受 `project_id` 的端点
- **[I-001] skills.py 四个 CRUD 端点缺少 `kb_id` 校验** — Critical
  - 文件: `services/api/app/routers/skills.py`
  - 描述: POST/GET/PUT/DELETE `/v1/projects/{id}/skills` 未验证 `Project.kb_id == kb_id`，允许跨租户操作 skill
  - 修复: 添加 `kb_id = Depends(get_kb_id)` + `await ensure_project_access(project_id, kb_id, db)` 到全部 4 个端点
  - 状态: **已修复** (commit `2a7aac4`)

### 3. IR（Intermediate Representation）字段完整性
- 检查范围: 所有解析器输出的 IR chunk metadata
- **[M-001] video_parser.py 缺少 `language` 和 `semantic_boundaries` 字段**
  - 文件: `services/ingestion-worker/worker/parsers/video_parser.py`
  - 描述: metadata chunk 和 subtitle chunk 未填充 `language`/`semantic_boundaries` 字段（其他解析器已补全）
  - 修复: 添加 `"language": None, "semantic_boundaries": None` 到 metadata chunk，添加 `"semantic_boundaries": None` 到 subtitle chunk
  - 状态: **已修复** (commit `2a7aac4`)

### 4. 代码注释准确性
- **[M-002] skills.py Gap 编号错误**: 注释写 `Gap-8` 实际应为 `Gap-10`
  - 修复: 更正注释
  - 状态: **已修复** (commit `2a7aac4`)

## 统计

| 级别 | 发现数 | 已修复 |
|------|--------|--------|
| Critical | 1 | 1 |
| Important | 0 | 0 |
| Minor | 2 | 2 |
| **合计** | **3** | **3** |

## 结论
Stage 1 所有发现均已修复。通过。
