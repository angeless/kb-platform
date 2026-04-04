# TODO_NEXT

## 上次停在
- 版本：v0.49.4 | 分支：test-v-0-48-a | 最后完成：v0.49.4 反思循环 v2 规则校验层
- v0.45-v0.48 全部完成 ✅
- v0.49.1 ✅ IR schema 升级（5 个 IR 字段）
- v0.49.2 ✅ 解析器 IR 填充（text/asr/url）
- v0.49.3 ✅ classify + doc_generate IR 适配
- v0.49.6 ✅ pgvector HNSW 索引
- v0.49.4 ✅ 规则校验层（格式/来源/术语）

## 下一步

### v0.49.5 — 反思循环 v2 — AI 自检 + 循环集成
- 新增 reflect_and_revise Celery task
- 接收 quality_check issues → 调用 LLM 修正 → 重新 quality_check
- 最多 3 轮

### 随后
- v0.49.7: Per-stage 幂等性保障
- v0.49.8: Prometheus 指标导出
- v0.49.9: 模型成本限制执行

## 注意事项
- migrations 待执行：u0i1j2k3l4m5（IR 字段）, v1w2x3y4z5a6（HNSW 索引）
- pymupdf 已安装到 .venv
- 分支 test-v-0-48-a 包含 v0.48 全部 + v0.49 前 5 任务
