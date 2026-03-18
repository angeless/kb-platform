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


# ---------------------------------------------------------------------------
# Knowledge document generation prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_GENERATE_DOC = """你是一个知识文档生成专家。你的任务是根据知识系统架构中某个节点的定义，
以及与该节点相关的原始资料片段，生成一份结构化的 Markdown 知识文档。

你必须：
- 严格基于提供的资料片段内容，不得编造资料中不存在的事实
- 每个关键结论都标注来源引用（使用 chunk 的序号）
- 如果资料不足以形成完整文档，明确标注"待补充"
- 如果发现资料之间存在矛盾，必须保留双方观点，不得强行合并"""

USER_PROMPT_GENERATE_DOC_TEMPLATE = """请为以下知识系统节点生成一份知识文档。

节点信息：
- 节点名称：{node_name}
- 节点类型：{node_type}
- 节点说明：{node_description}
- 所属层级：{node_level}

--- 相关资料片段 ---
{chunks_text}
--- 资料片段结束 ---

请以如下 JSON 格式输出（不要输出其他内容）：
{{
  "title": "文档标题",
  "doc_type": "{node_type}",
  "reasoning": "生成依据（1-2句话，说明为什么这些资料适合归入此节点）",
  "content_md": "完整的 Markdown 正文内容（含标题、正文、来源引用）",
  "cited_chunk_indices": [0, 1, 2],
  "has_conflicts": false,
  "conflict_description": null
}}

注意：
- content_md 中引用来源时使用 [来源N] 格式，N 对应资料片段的序号（从0开始）
- 如果发现矛盾，设 has_conflicts=true 并填写 conflict_description
- 文档应包含：标题、适用范围、正文内容、来源列表
- 如果资料不够形成有意义的文档，返回 content_md 为空字符串"""


def build_generate_doc_prompt(
    node_name: str,
    node_type: str,
    node_description: str | None,
    node_level: int,
    chunks: list[dict],
    max_chunk_chars: int = 8000,
) -> tuple[str, str]:
    """Build prompts for generating a knowledge document for a single node.

    Returns (system_prompt, user_prompt).

    Each chunk dict should have 'index', 'content_text', and optionally
    'page_or_timestamp'.
    """
    chunk_texts = []
    total_chars = 0
    for chunk in chunks:
        idx = chunk.get("index", "?")
        text = chunk.get("content_text", "")
        page = chunk.get("page_or_timestamp", "")
        prefix = f"[片段{idx}]"
        if page:
            prefix += f" (位置: {page})"
        entry = f"{prefix}\n{text}"

        if total_chars + len(entry) > max_chunk_chars:
            remaining = max_chunk_chars - total_chars
            if remaining > 100:
                chunk_texts.append(entry[:remaining] + "...(截断)")
            break
        chunk_texts.append(entry)
        total_chars += len(entry)

    chunks_text = "\n\n".join(chunk_texts) if chunk_texts else "(无相关资料片段)"

    user_prompt = USER_PROMPT_GENERATE_DOC_TEMPLATE.format(
        node_name=node_name,
        node_type=node_type,
        node_description=node_description or "未指定",
        node_level=node_level,
        chunks_text=chunks_text,
    )

    return SYSTEM_PROMPT_GENERATE_DOC, user_prompt
