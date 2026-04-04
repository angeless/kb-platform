# 任务报告 v0.48.2 — URL import 升级

**版本号**: v0.48.2
**任务名称**: URL import 升级 — 使用正文提取替代原始 HTML
**完成日期**: 2026-04-03
**来源**: PRD §7.2

---

## 1. 计划 / 当前迭代目标

**目标**: 修改 URL import 流程，集成 v0.48.1 readability 模块提取正文
**最小闭环**: asset_service.py 修改 + 6 个集成测试
**排除范围**: 批量 URL 导入、已有 URL 资产重提取

## 2. 文件变更清单

| 路径 | 操作 | 职责描述 |
|------|------|---------|
| `services/api/app/services/asset_service.py` | 修改 | import_url 集成 readability，创建 AssetChunk |
| `services/api/tests/test_url_import.py` | 新增 | 6 个集成测试覆盖全部 AC |
| `docs/dev-plans/impl-plan-v0.48.2.md` | 新增 | 实施计划 |

## 3. 用户可见能力

导入 URL 后，资产内容为纯正文（去除了导航、广告、脚本等噪音），提升下游 AI 处理质量。

## 4. 真实场景验证

1. 导入新闻 URL → chunk 存储纯正文，无 HTML 标签 ✅
2. MinIO 保留原始 HTML（可溯源下载） ✅
3. chunk.tags 包含 title/author/date 元数据 ✅
4. 不可解析的 URL → 降级为去标签文本 ✅
5. SSRF 防护不受影响 ✅

## 5. 开放问题

无。

## 6. 收尾说明

**设计偏离说明**: 计划说"元数据存入 Asset.tags"，但 Asset 无 tags JSONB 字段。改为存入 AssetChunk.tags（已有字段），功能等效。

## 7. 版本状态更新

- VERSION: 0.48.2
- CHANGELOG: 已更新
- TODO_NEXT.md: 已更新，指向 v0.48.3

## 8. Commit 信息

见下方。

## 9. 是否继续下一个任务

是 — 继续 v0.48.3（视频解析器）。
