# 任务报告 v0.48.1 — 网页正文提取（Readability 算法集成）

**版本号**: v0.48.1
**任务名称**: 网页正文提取 — Readability 算法集成
**完成日期**: 2026-04-03
**来源**: PRD §7.2

---

## 1. 计划 / 当前迭代目标

**目标**: 新增 Readability 工具模块，使用 trafilatura 从 HTML 提取正文/标题/作者/日期
**最小闭环**: readability.py + 8 个单元测试
**排除范围**: URL import 集成（v0.48.2）、浏览器渲染

## 2. 文件变更清单

| 路径 | 操作 | 职责描述 |
|------|------|---------|
| `services/api/app/utils/readability.py` | 新增 | 正文提取模块（trafilatura + fallback） |
| `services/api/tests/test_readability.py` | 新增 | 8 个单元测试覆盖全部 AC |
| `docs/dev-plans/impl-plan-v0.48.1.md` | 新增 | 实施计划 |
| `docs/versions/test-report-v0.48.1.md` | 新增 | 测试报告 |

## 3. 用户可见能力

无直接用户可见变更（工具模块，v0.48.2 集成后用户可见）。

## 4. 真实场景验证

1. 新闻网页 HTML → 提取纯正文，无导航/广告/脚本 ✅
2. 空 HTML → 空 body，不报错 ✅
3. 纯文本 → 原样返回 ✅
4. trafilatura 失败 → 降级为 HTML 去标签 ✅
5. HTML 实体 → 正确解码 ✅

## 5. 开放问题

无。

## 6. 收尾说明

闭环完成。v0.48.2 将集成到 URL import 流程。

## 7. 版本状态更新

- VERSION: 0.48.1
- CHANGELOG: 已更新
- TODO_NEXT.md: 已更新，指向 v0.48.2

## 8. Commit 信息

见下方 Phase 6 commit。

## 9. 是否继续下一个任务

是 — 继续 v0.48.2（URL import 升级）。
