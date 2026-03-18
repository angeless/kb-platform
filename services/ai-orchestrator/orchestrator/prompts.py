"""Prompt templates for AI orchestrator tasks.

Follows constraint from doc 12 section 4:
- Prompt must not instruct model to ignore sources
- Prompt must not induce model to fabricate missing facts
- Model output must include reasoning summary
"""

SYSTEM_PROMPT_ARCHITECTURE = """你是一个知识系统架构设计专家。你的任务是根据用户提供的原始资料片段，
推断这些资料属于什么行业、应该如何组织成一个多层级的知识系统架构。

你必须严格基于提供的资料内容推断，不得编造不存在的分类或主题。
如果资料不足以判断某个层级，应在输出中标注"待确认"。"""

USER_PROMPT_ARCHITECTURE_TEMPLATE = """以下是一个项目中上传的原始资料片段（已解析为文本）。
请根据这些内容：
1. 推断资料所属的行业域
2. 设计一个知识系统架构，包含层级定义和节点树

项目名称：{project_name}
{industry_hint}

--- 资料片段 ---
{chunks_text}
--- 资料片段结束 ---

请以如下 JSON 格式输出（不要输出其他内容）：
{{
  "architecture_name": "xxx知识系统",
  "industry": "推断的行业",
  "reasoning": "推断依据（1-2句话）",
  "levels": [
    {{"level": 1, "name": "层级名称"}},
    {{"level": 2, "name": "层级名称"}},
    {{"level": 3, "name": "层级名称"}}
  ],
  "nodes": [
    {{
      "node_name": "节点名称",
      "node_type": "category",
      "level": 1,
      "parent_name": null,
      "description": "节点说明",
      "accept_types": ["topic", "document"]
    }},
    {{
      "node_name": "子节点名称",
      "node_type": "topic",
      "level": 2,
      "parent_name": "父节点名称",
      "description": "子节点说明"
    }}
  ]
}}

注意：
- node_type 只能是: category, topic, document, glossary, conflict, index
- parent_name 为 null 表示根节点
- 至少输出 2 个层级
- 节点数量应该反映资料内容的实际覆盖范围，不要过多猜测"""


def build_propose_prompt(
    project_name: str,
    industry_hint: str | None,
    chunks: list[dict],
    max_chunk_chars: int = 8000,
) -> tuple[str, str]:
    """Build the system prompt and user prompt for architecture proposal.

    Returns (system_prompt, user_prompt).

    Truncates chunk content to max_chunk_chars total to fit context window.
    """
    # Build chunk text, respecting size limit
    chunk_texts = []
    total_chars = 0
    for chunk in chunks:
        text = chunk.get("content_text", "")
        if total_chars + len(text) > max_chunk_chars:
            remaining = max_chunk_chars - total_chars
            if remaining > 100:
                chunk_texts.append(text[:remaining] + "...(截断)")
            break
        chunk_texts.append(text)
        total_chars += len(text)

    chunks_text = "\n\n".join(chunk_texts) if chunk_texts else "(无资料片段)"

    hint_line = f"行业提示：{industry_hint}" if industry_hint else "行业提示：未指定，请根据内容推断"

    user_prompt = USER_PROMPT_ARCHITECTURE_TEMPLATE.format(
        project_name=project_name,
        industry_hint=hint_line,
        chunks_text=chunks_text,
    )

    return SYSTEM_PROMPT_ARCHITECTURE, user_prompt
