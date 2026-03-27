# Agent API 接口文档

> 版本: v0.43.3 | 日期: 2026-03-27

## 认证方式

Agent API 使用 API Key 认证，不依赖 session cookie。

```
Authorization: Bearer kb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

API Key 通过项目设置页创建，绑定到特定项目。Key 仅在创建时展示一次。

## 端点

### POST /v1/agent/search — 知识检索

语义检索项目知识库，返回最相关的文档片段。

**请求体：**

```json
{
  "project_id": "uuid",
  "query": "退款流程是怎样的？",
  "top_k": 5
}
```

**响应 200：**

```json
{
  "results": [
    {
      "doc_id": "uuid",
      "title": "退款政策",
      "content_snippet": "退款需在 30 天内提交...",
      "relevance_score": 0.92,
      "node_path": ["客服知识", "售后", "退款"],
      "source_assets": ["退款政策v3.docx", "客服手册.pdf"]
    }
  ],
  "query": "退款流程是怎样的？",
  "total": 5
}
```

### POST /v1/agent/ask — 知识问答

基于知识库的 RAG 问答，返回同步 JSON（非流式）。

**请求体：**

```json
{
  "project_id": "uuid",
  "question": "退款需要多久？",
  "top_k": 5
}
```

**响应 200：**

```json
{
  "answer": "根据退款政策，退款通常在 3-5 个工作日内处理完成...",
  "source_docs": [
    {
      "doc_id": "uuid",
      "title": "退款政策",
      "node_path": ["客服知识", "售后", "退款"]
    }
  ],
  "question": "退款需要多久？"
}
```

## 错误码

| HTTP Status | error_code | 说明 |
|-------------|-----------|------|
| 401 | API_KEY_INVALID | API Key 无效或已撤销 |
| 403 | FORBIDDEN | API Key 与请求的 project_id 不匹配 |
| 404 | PROJECT_NOT_FOUND | 项目不存在 |

## curl 示例

```bash
# 检索
curl -X POST https://your-domain/v1/agent/search \
  -H "Authorization: Bearer kb_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "uuid", "query": "退款", "top_k": 5}'

# 问答
curl -X POST https://your-domain/v1/agent/ask \
  -H "Authorization: Bearer kb_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "uuid", "question": "退款需要多久？"}'
```

## API Key 管理

通过项目设置页或以下 API（需登录态）管理 Key：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/projects/{id}/api-keys` | 创建 Key（body: `{name}`, 返回 raw_key） |
| GET | `/v1/projects/{id}/api-keys` | 列出 Key（仅返回 prefix） |
| DELETE | `/v1/projects/{id}/api-keys/{key_id}` | 撤销 Key |
