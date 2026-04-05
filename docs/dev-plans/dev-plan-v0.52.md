# KB Platform v0.52 版本开发任务计划

**文档编号**: PLAN-2026-04-04-v052
**版本**: V1.0
**日期**: 2026-04-04
**基线**: v0.51.13 (main, commit 2db030f)
**依据**: Gap 审查报告 — 16 个 plan-vs-code 差距
**作者**: Claude Code（自动生成）

---

## 第一章 版本主题

**v0.52：集成补全 — 打通模型层到运行时的"最后一公里"**

> v0.47-v0.51 建立了完整的 Schema/模型/Prompt 层。v0.52 不引入新模型或 migration，
> 仅将已有能力接入运行时调用方，使 16 个 gap 中的 P0+P1 全部闭环。

---

## 第二章 任务列表

| 任务版本号 | 任务名称 | 优先级 | Gap# | 预估行数 |
|----------|--------|------|------|---------|
| v0.52.1 | IR 字段补全：pdf/ocr/video/word parser | P0 | Gap-1 | ~60 行 |
| v0.52.2 | CostTracker 接入 LLM 调用链 | P0 | Gap-16 | ~20 行 |
| v0.52.3 | SKILL 运行时：pipeline stages 加载 prompt_template | P0 | Gap-3 | ~40 行 |
| v0.52.4 | Stage execution_order + condition 运行时生效 | P0 | Gap-4 | ~30 行 |
| v0.52.5 | 租户配额 check_quota/check_feature | P1 | Gap-5 | ~50 行 |
| v0.52.6 | Redis Sentinel 连接逻辑 | P1 | Gap-6 | ~30 行 |
| v0.52.7 | Ontology 提取 Celery task | P1 | Gap-9 | ~40 行 |
| v0.52.8 | SKILL CRUD 端点补全 | P1 | Gap-10 | ~60 行 |
| v0.52.9 | 确认码接入高危路由 | P1 | Gap-7 | ~20 行 |
| v0.52.10 | Asset.tags 数据流修复 | P1 | Gap-15 | ~30 行 |
| v0.52.11 | Review Kanban 操作按钮 | P1 | Gap-11 | ~40 行 |

### 不做

- Gap-12 (stage 幂等去重) — 已有 job 级幂等，stage 级可推后
- Gap-13 (术语表/维护指南 task) — node_type 路由已部分覆盖
- Gap-14 (视频多阶段进度) — UX 优化，非功能断裂
- Gap-15 (Prometheus increment) — 需要实际 LLM 环境验证
- Gap-16 (前端 tsc) — 需要 Node.js 环境

---

## 第三章 执行顺序

```
v0.52.1 → v0.52.2 → v0.52.3 → v0.52.4 → v0.52.5 → v0.52.6 →
v0.52.7 → v0.52.8 → v0.52.9 → v0.52.10 → v0.52.11
```

---

## 第四章 约束

- **无新 migration** — 所有所需字段已存在
- **无新模型** — 所有所需模型已定义
- **无新依赖** — 仅接线已有代码
- **最小改动** — 每个 task 只改必须改的文件
