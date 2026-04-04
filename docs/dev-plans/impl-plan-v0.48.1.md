# 实施计划 v0.48.1 — 网页正文提取（Readability 算法集成）

**任务版本号**: v0.48.1
**基线**: v0.47.8
**分支**: test-v-0-48-a
**日期**: 2026-04-03

---

## 1. 目标

新增 Readability 工具模块，使用 `trafilatura` 从 HTML 中提取正文、标题、作者、发布日期，去除导航/广告/脚本噪音。

**注意**: 本任务仅创建工具模块和测试。URL import 流程集成在 v0.48.2。

---

## 2. 现状分析

- `services/api/app/utils/` 目录包含 6 个工具模块（storage, url_fetcher, url_validator, crypto, math_utils, security）
- `import_url()` 在 `asset_service.py:111-176`，下载 HTML 后直接存 MinIO
- 无现有正文提取能力
- `trafilatura` 未安装

---

## 3. 变更文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `services/api/app/utils/readability.py` | **新增** | 正文提取模块：`extract_article(html, url)` |
| `services/api/tests/test_readability.py` | **新增** | 单元测试：5 个验收场景 |

**依赖变更**: 运行时安装 `trafilatura`（`pip install trafilatura`）

---

## 4. 详细设计

### `readability.py` 接口

```python
def extract_article(html: str, url: str) -> dict:
    """Extract article content from HTML.

    Returns:
        {"title": str, "body": str, "author": str | None, "date": str | None}
    """
```

### 业务规则

1. 接收 HTML 字符串和原始 URL
2. 调用 `trafilatura.extract()` 提取正文（纯文本输出）
3. 使用 `trafilatura.bare_extraction()` 提取元数据（title, author, date）
4. 提取失败时降级：使用简单 HTML 去标签（正则 + html.unescape）
5. 空 HTML → 返回 `{"title": "", "body": "", "author": None, "date": None}`
6. 非 HTML 文本（无标签）→ 原样返回 body

---

## 5. 验收标准（逐条）

- [ ] AC-1: 传入新闻网页 HTML → 提取纯正文（无导航/广告/脚本）
- [ ] AC-2: 提取结果包含 title / body / author / date 四个字段
- [ ] AC-3: 传入空 HTML → 返回空 body，不报错
- [ ] AC-4: 传入非 HTML 文本 → 原样返回 body
- [ ] AC-5: trafilatura 提取失败 → 降级为简单 HTML 去标签
- [ ] AC-6: 现有测试全部通过

---

## 6. 风险

| 风险 | 缓解 |
|------|------|
| trafilatura 安装失败 | 仅 pip install，无系统依赖 |
| 中文网页效果 | 降级机制保底 |

---

## 7. 不做

- URL import 集成（v0.48.2）
- 浏览器渲染（明确排除）
- 批量 URL 处理
