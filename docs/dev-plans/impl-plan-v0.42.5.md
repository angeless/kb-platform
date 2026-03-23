# 实施计划 — v0.42.5 (T-42-05: 前端 Wiki 呈现改造)

## 1. 任务目标

纯前端 Wiki 视图，三栏布局（左侧架构树导航 + 文档正文 + 右侧 TOC），复用已有后端 API，不改动后端。

## 2. 验收标准 Checklist

- [ ] Wiki 首页展示架构概览和最近更新文档列表
- [ ] 左侧架构树导航可展开/收起，点击节点显示关联文档
- [ ] 文档阅读页正确渲染 Markdown 内容
- [ ] 面包屑显示当前文档在架构中的路径
- [ ] TOC 自动提取 h2/h3 标题，点击平滑滚动到对应位置
- [ ] 来源追溯卡片显示文档关联的原始素材
- [ ] 相关知识推荐显示 top-5 语义相似文档
- [ ] Wiki 内搜索支持全文 + 语义搜索
- [ ] 侧栏新增 Wiki 入口链接
- [ ] 移动端小屏隐藏左导航和 TOC

## 3. 代码现状

### 可复用组件
- tree-node.tsx: 架构树节点（展开/选中/图标）+ buildTree 工具
- markdown-view.tsx: Markdown 渲染（react-markdown + rehype-sanitize）
- mobile-nav.tsx: 移动端滑出导航
- pagination.tsx: 分页组件
- sidebar.tsx: 全局侧栏

### 可用 API
- GET /v1/projects/{pid}/architectures -> 架构列表
- GET /v1/architectures/{id}/nodes -> 节点列表（用于构建树）
- GET /v1/docs?project_id=&page=&page_size= -> 文档列表
- GET /v1/docs/{id} -> 文档详情（content_md + source_refs）
- GET /v1/search/hybrid?project_id=&query= -> 混合搜索

## 4. 文件变更清单

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| apps/web/src/app/(dashboard)/projects/[id]/wiki/page.tsx | 新增 | Wiki 首页 |
| apps/web/src/app/(dashboard)/projects/[id]/wiki/[docId]/page.tsx | 新增 | 文档阅读页 |
| apps/web/src/app/(dashboard)/projects/[id]/wiki/search/page.tsx | 新增 | Wiki 搜索 |
| apps/web/src/components/wiki-sidebar.tsx | 新增 | 架构树导航 |
| apps/web/src/components/wiki-breadcrumb.tsx | 新增 | 面包屑 |
| apps/web/src/components/wiki-toc.tsx | 新增 | 文内目录 |
| apps/web/src/components/source-refs.tsx | 新增 | 来源追溯 |
| apps/web/src/components/sidebar.tsx | 修改 | 添加 Wiki 入口 |
| VERSION | 修改 | 0.42.4 -> 0.42.5 |
| CHANGELOG.md | 修改 | 记录变更 |

## 5. 实施顺序

A -> J -> B -> C -> D+E+F -> G -> K -> H -> I -> L

## 6. 测试策略

- 单元测试: wiki-toc (标题提取)、wiki-breadcrumb (路径计算)
- 组件测试: vitest + @testing-library/react
- 手工验证: 路由跳转、响应式布局、搜索交互

## 7. 风险

- 架构树 API 返回扁平节点列表需用 buildTree 转换 -> 已有工具函数
- TOC 需在 Markdown 渲染后提取 DOM -> 使用 useEffect + querySelectorAll
