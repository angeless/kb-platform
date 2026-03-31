# TODO_NEXT

## 上次停在
- 版本：v0.47.0 | 分支：test-v-0-44-a | 最后完成：PRD Gap 修复 + WISHLIST
- v0.45 全部完成 ✅
- v0.46 全部完成 ✅（v0.46.1-7 共 7 个任务）
- PRD Gap 修复 ✅（PII 检测、update_type 追踪、LLM 成本日志）

## 下一步

### PRD 范围内（已修复）
- [x] PII 敏感信息检测 — quality_check 新增 8 类 PII 正则扫描（PRD §2.8）
- [x] update_type 追踪 — KnowledgeDoc 新增 update_type 字段 + 前端标签展示（PRD §2.4）
- [x] LLM 成本日志 — llm_client 输出 token 用量日志（PRD §5 基础版）
- [x] WISHLIST.md — 16 项非 PRD 范围改进建议

### PRD 范围内（需开发计划，工作量大）
1. **视频解析器** — PRD §7.2 要求视频帧提取 + 字幕检测，需 FFmpeg 集成
2. **网页正文提取** — PRD §7.2 要求 Readability 智能提取，当前 URL import 仅存原始文本
3. **审批工作流引擎** — PRD §7 review_gate 要求审批人分配/多人共识/驳回，当前仅通知
4. **高危操作二次确认** — PRD §4.6 要求发布/回滚/删除等操作 2FA 确认
5. **IR 中间表示** — PRD §2.3 要求统一结构化片段 schema，当前 AssetChunk 仅 raw text
6. **术语表 / 维护指南文档模板** — PRD §8 核心产出，需新增文档类型

### 其他
- v0.44.14 Blocked 待 PA 中台日志 API 规范确认
- 交叉审计留存项（C-3 draft 过滤、H-1 entity_types 来源、H-4 params 校验）

## 注意事项
- weasyprint 需要系统级依赖（Cairo/Pango），Docker 部署时需确认
- migration s8g9h0i1j2k3 待执行：`ALTER TABLE knowledge_doc ADD COLUMN update_type varchar(20)`
- WISHLIST 完整列表见 docs/WISHLIST.md（16 项）
