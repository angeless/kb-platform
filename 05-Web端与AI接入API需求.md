# Web 端与 AI 接入 API 需求

## 1. 双入口原则
平台必须同时提供：
- Web 端：给用户看、改、审、管；
- API 端：给外部 AI 和系统接入。

两者使用同一套核心业务能力，但入口体验不同。

## 2. Web 端模块
### 2.1 工作台
显示项目概览、最新任务、待审核项、失败任务、最近更新。

### 2.2 资料接入页
支持上传文件、拖拽上传、填写 URL、导入压缩包、批量导入。

### 2.3 解析任务页
显示任务状态、失败原因、重试按钮、解析结果预览。

### 2.4 架构管理页
显示知识系统架构图、节点详情、版本历史、编辑入口、审核入口。

### 2.5 知识库浏览页
按架构节点查看知识文档，支持搜索、筛选、版本查看。

### 2.6 审核中心
查看待审核文档、待确认分类、冲突项、架构变更。

### 2.7 模型配置页
允许配置大模型供应商、模型名、API Key、路由规则、预算限制。

## 3. API 设计原则
- 所有核心功能可通过 API 调用；
- API 输出必须可供代理式 AI 稳定消费；
- 重要异步任务必须返回任务 ID；
- 所有写操作必须有审计字段；
- 支持租户隔离和项目隔离。

## 4. 核心 API
### 4.1 资料接入
- `POST /api/v1/assets/upload`
- `POST /api/v1/assets/import-url`
- `POST /api/v1/assets/import-archive`

### 4.2 任务管理
- `POST /api/v1/jobs/create`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/retry`

### 4.3 架构管理
- `POST /api/v1/architectures/generate`
- `GET /api/v1/architectures/{architecture_id}`
- `POST /api/v1/architectures/{architecture_id}/publish`
- `POST /api/v1/architectures/{architecture_id}/nodes`
- `PATCH /api/v1/architectures/{architecture_id}/nodes/{node_id}`

### 4.4 知识文档
- `GET /api/v1/docs`
- `GET /api/v1/docs/{doc_id}`
- `POST /api/v1/docs/{doc_id}/review`
- `POST /api/v1/docs/{doc_id}/publish`

### 4.5 增量更新
- `POST /api/v1/ingestion/incremental`
- `POST /api/v1/conflicts/{conflict_id}/resolve`

### 4.6 检索
- `POST /api/v1/search/text`
- `POST /api/v1/search/semantic`
- `POST /api/v1/search/hybrid`

### 4.7 模型配置
- `POST /api/v1/model-providers`
- `POST /api/v1/model-routes`
- `POST /api/v1/model-keys/test`

## 5. 模型配置需求
平台必须允许用户配置：
- 模型供应商名称；
- 模型名称；
- API Key；
- Base URL；
- 调用超时；
- 最大上下文；
- 成本上限；
- 路由规则。

## 6. 大模型选型原则
### 6.1 适合本场景的模型特性
- 长上下文；
- 多模态理解；
- 稳定结构化输出；
- 较强的归类和归纳能力；
- 较好的证据保留能力。

### 6.2 路由建议
- 重整理任务：使用高质量主模型；
- OCR 纠错、轻分类：可用较便宜辅模型；
- 检索增强总结：可使用响应更快的模型。

## 7. AI 代理调用需求
对代理式 AI 开放时，API 返回体中必须明确：
- 当前任务状态；
- 是否需要人工审核；
- 产出文档列表；
- 架构节点绑定结果；
- 冲突与异常信息。
