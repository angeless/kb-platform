# TODO_NEXT

## 上次停在
- 版本：v0.47.0 | 分支：test-v-0-44-a | 最后完成：v0.47-v0.51 开发计划重写 + 交叉审查修复
- v0.45 全部完成 ✅
- v0.46 全部完成 ✅（v0.46.1-7 共 7 个任务）
- PRD Gap 修复 ✅（PII 检测、update_type 追踪、LLM 成本日志）
- v0.47-v0.51 开发计划 ✅（43 个原子任务，规范合规）
- 交叉审查 ✅（4 中风险项已修复）

## 下一步

### 进入开发（v0.47.1 开始）
1. v0.47.1 矛盾检测排除 draft 文档（P0，审计 C-3）
2. v0.47.2 suggest_tags entity_types 从 pipeline config 读取（P0，审计 H-1）
3. v0.47.3 Pipeline params JSON Schema 校验（P1，审计 H-4）
4. ... 共 8 个任务，详见 docs/dev-plans/dev-plan-v0.47.md

### 待 commit
- [x] v0.47-v0.51 计划重写（5 个 dev-plan 文件）
- [x] 交叉审查修复（v0.47 / v0.49 / v0.51 三个文件）

## 注意事项
- weasyprint 需要系统级依赖（Cairo/Pango），Docker 部署时需确认
- migration s8g9h0i1j2k3 待执行：`ALTER TABLE knowledge_doc ADD COLUMN update_type varchar(20)`
- WISHLIST 完整列表见 docs/WISHLIST.md（16 项）
- v0.44.14 Blocked 待 PA 中台日志 API 规范确认
