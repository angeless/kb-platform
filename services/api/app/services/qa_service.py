"""QA service: RAG-based question answering over knowledge base documents."""

import json
import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import AppException, ErrorCode
from shared_models import ModelProvider, ModelRoute

from .search_service import SearchService
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个知识库助手。用户会提出一个问题，你需要仅根据以下知识库内容来回答。

## 规则
1. 只回答知识库中有依据的内容，不要编造
2. 如果知识库内容不足以回答，请诚实说明
3. 引用来源时使用文档标题
4. 回答完毕后，生成 3-5 个用户可能感兴趣的衍生问题

## 输出格式（JSON）
{
  "answer": "你的回答...",
  "cited_docs": ["文档标题1", "文档标题2"],
  "related_questions": ["问题1", "问题2", "问题3"]
}"""


class QAService:
    """RAG-based question answering: retrieve relevant docs then generate answer via LLM."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, settings: Settings) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.settings = settings

    async def ask(self, project_id: uuid.UUID, question: str, top_k: int = 5) -> dict:
        """Answer a question using knowledge base documents as context.

        1. Hybrid search for relevant documents
        2. Build context from retrieved docs
        3. Call LLM to generate answer
        4. Return structured response with sources and related questions
        """
        # Step 1: Retrieve relevant documents via hybrid search
        search_svc = SearchService(self.db, self.tenant_id)
        results, total = await search_svc.hybrid_search(project_id, question, page=1, page_size=top_k)

        if not results:
            return {
                "answer": "知识库中暂未找到相关内容，请尝试使用不同的关键词搜索。",
                "sources": [],
                "related_questions": [],
            }

        # Step 2: Get LLM configuration
        model_config = await self._get_qa_model_config()
        if model_config is None:
            raise AppException(
                error_code=ErrorCode.QA_MODEL_NOT_CONFIGURED,
                message="AI 问答功能需要先配置模型服务",
                status_code=400,
            )

        # Step 3: Build context from retrieved documents
        context_parts = []
        sources = []
        for i, doc in enumerate(results, 1):
            snippet = doc.get("snippet", "")
            title = doc.get("title", "未命名文档")
            context_parts.append(f"### 来源 {i}: {title}\n{snippet}")
            sources.append({
                "doc_id": doc["doc_id"],
                "title": title,
                "snippet": snippet[:200] if snippet else "",
                "relevance": round(doc.get("score", 0), 4),
            })

        context = "\n\n".join(context_parts)
        user_prompt = f"## 知识库内容\n{context}\n\n## 用户问题\n{question}"

        # Step 4: Call LLM
        try:
            llm_response = await self._call_llm(model_config, user_prompt)
        except Exception as e:
            logger.warning("LLM call failed: %s", e)
            raise AppException(
                error_code=ErrorCode.MODEL_PROVIDER_UNREACHABLE,
                message="AI 服务暂时不可用，请稍后重试",
                status_code=502,
            )

        # Step 5: Parse LLM response
        answer_data = self._parse_llm_response(llm_response)

        return {
            "answer": answer_data.get("answer", llm_response),
            "sources": sources,
            "related_questions": answer_data.get("related_questions", []),
        }

    async def _get_qa_model_config(self) -> dict | None:
        """Get LLM configuration for QA task from ModelRoute."""
        # Look for a route with task_type containing 'qa' or 'chat'
        result = await self.db.execute(
            select(ModelRoute, ModelProvider)
            .join(ModelProvider, ModelRoute.provider_id == ModelProvider.id)
            .where(ModelRoute.is_active == True)  # noqa: E712
            .order_by(ModelRoute.created_at.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None

        route, provider = row
        return {
            "api_key": provider.api_key_encrypted,  # Decrypted at usage time
            "base_url": provider.base_url,
            "model": route.model_name,
        }

    async def _call_llm(self, config: dict, user_prompt: str) -> str:
        """Call LLM via OpenAI-compatible API."""
        url = (config["base_url"] or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        api_key = config["api_key"]

        # Decrypt API key if it's encrypted (bytes-like)
        try:
            from app.utils.crypto import decrypt
            from shared_config.settings import get_settings
            if isinstance(api_key, (bytes, memoryview)):
                api_key = decrypt(bytes(api_key), get_settings().encryption_key)
            elif isinstance(api_key, str) and api_key.startswith("KDF1"):
                api_key = decrypt(api_key.encode("latin-1"), get_settings().encryption_key)
        except Exception:
            pass  # Already plain text (dev mode or unencrypted)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": config["model"],
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _parse_llm_response(self, response: str) -> dict:
        """Parse LLM JSON response, with fallback for non-JSON output."""
        # Try to extract JSON from the response
        try:
            # Handle markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            # Fallback: treat entire response as the answer
            return {
                "answer": response,
                "cited_docs": [],
                "related_questions": [],
            }
