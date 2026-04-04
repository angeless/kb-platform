# 测试报告 v0.48.1 — 网页正文提取

**测试日期**: 2026-04-03
**测试框架**: pytest 9.0.2, Python 3.13.12

---

## 测试结果汇总

| 类型 | 通过 | 失败 | 错误 | 总计 |
|------|------|------|------|------|
| 新增单元测试 | 8 | 0 | 0 | 8 |
| 回归测试（全量） | 246 | 0 | 156* | 402 |

*156 个 ERROR 为预存在的 async 会话 fixture 问题（`ValueError: the greenlet...`），与本任务无关。

## 新增测试用例

| 用例 | 覆盖 AC | 结果 |
|------|---------|------|
| test_extracts_article_body_from_html | AC-1 | PASSED |
| test_returns_all_four_fields | AC-2 | PASSED |
| test_empty_html_returns_empty_body | AC-3 | PASSED |
| test_whitespace_only_html | AC-3 | PASSED |
| test_plain_text_returned_as_body | AC-4 | PASSED |
| test_fallback_strips_tags_on_minimal_html | AC-5 | PASSED |
| test_html_entities_decoded | 补充 | PASSED |
| test_none_url_does_not_crash | 补充 | PASSED |

## 子 Agent 验收

独立子 Agent 逐条验证 AC-1 至 AC-6，结论: **PASS**。
2 条 minor observation（测试断言改进 + fallback mock 覆盖），已修复 1 条。
