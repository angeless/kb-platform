# 实施计划 v0.48.2 — URL import 升级

**任务版本号**: v0.48.2
**基线**: v0.48.1
**分支**: test-v-0-48-a
**日期**: 2026-04-03

---

## 1. 目标

修改 URL import 流程，使用 v0.48.1 的 readability 模块提取正文。原始 HTML 仍存 MinIO 保留溯源。AssetChunk 使用提取后正文。

## 2. 现状分析

- `import_url()` 下载 HTML → 存 MinIO → 创建 Asset（parse_status="pending"）
- 不创建 AssetChunk，留给 ingestion worker
- `Asset` 无 `tags` JSONB 字段，但 `AssetChunk` 有
- 计划假设 `Asset.tags` 存在 → 实际不存在，改为存储在 AssetChunk.tags

## 3. 设计决策

**偏离计划说明**: 计划说"元数据存入 Asset.tags"，但 Asset 无 tags 字段且计划明确说"v0.48 不新增数据库表/列"。改为存入 AssetChunk.tags（已有 JSONB 字段），功能等效。

**流程变更**:
1. 下载 HTML（不变）
2. 调用 `extract_article(html, url)` 提取正文
3. 原始 HTML 上传 MinIO（不变）
4. **新增**: 创建一个 AssetChunk，content_text = 提取后正文，tags = 元数据
5. **变更**: parse_status = "completed"（URL 文本提取已在 import 时完成）

## 4. 变更文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `services/api/app/services/asset_service.py` | 修改 | import_url 集成 readability |
| `services/api/tests/test_url_import.py` | 新增 | 集成测试 |

## 5. 验收标准

- [ ] AC-1: 导入新闻 URL → AssetChunk.content_text 为纯正文（非 HTML）
- [ ] AC-2: MinIO 中保存了原始 HTML
- [ ] AC-3: AssetChunk.tags 包含 extracted_title / extracted_author / extracted_date
- [ ] AC-4: 导入不可解析的 URL → 降级为去标签文本，不报错
- [ ] AC-5: SSRF 防护不受影响
- [ ] AC-6: 现有测试全部通过
