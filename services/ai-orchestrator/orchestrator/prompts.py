"""Prompt templates for AI orchestrator tasks.

Follows constraint from doc 12 section 4:
- Prompt must not instruct model to ignore sources
- Prompt must not induce model to fabricate missing facts
- Model output must include reasoning summary
"""

SYSTEM_PROMPT_ARCHITECTURE = """你是一个知识系统架构设计专家。你的任务是根据用户提供的原始资料片段，
推断这些资料属于什么行业、应该如何组织成一个多层级的知识系统架构。

你必须严格基于提供的资料内容推断，不得编造不存在的分类或主题。
如果资料不足以判断某个层级，应在输出中标注"待确认"。

架构设计必须满足 MECE 原则（互斥且穷举）：
- 互斥：任何一个知识片段的主归位唯一，不能同时属于两个同级节点
- 穷举：所有资料片段都能归入某个节点，无遗漏"""

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
  "classification_dimension": "topic|process|audience|chronological|hybrid",
  "dimension_rationale": "选择此分类维度的原因（1句话）",
  "coverage_score": 85,
  "uncovered_chunks": ["无法归类的内容描述（如有）"],
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
- 节点数量应该反映资料内容的实际覆盖范围，不要过多猜测
- classification_dimension 说明：topic=按主题, process=按流程, audience=按受众, chronological=按时间, hybrid=混合
- coverage_score 为 0-100 整数，表示资料内容被架构覆盖的百分比
- 架构深度不超过 5 层，每层 3-7 个节点
- 确保节点名称无重复"""


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
  "conflict_description": null,
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "knowledge_type": "fact|process|rule|definition|case"
}}

注意：
- content_md 中引用来源时使用 [来源N] 格式，N 对应资料片段的序号（从0开始）
- 如果发现矛盾，设 has_conflicts=true 并填写 conflict_description
- 文档应包含：标题、适用范围、正文内容、来源列表
- 如果资料不够形成有意义的文档，返回 content_md 为空字符串
- keywords：2-5 个描述核心主题的关键词
- knowledge_type：fact=事实, process=流程, rule=规范, definition=定义, case=案例"""


def build_generate_doc_prompt(
    node_name: str,
    node_type: str,
    node_description: str | None,
    node_level: int,
    chunks: list[dict],
    max_chunk_chars: int = 8000,
    entity_types: list[str] | None = None,
) -> tuple[str, str]:
    """Build prompts for generating a knowledge document for a single node.

    Returns (system_prompt, user_prompt).

    Each chunk dict should have 'index', 'content_text', and optionally
    'page_or_timestamp'.
    entity_types: optional user-defined entity types to guide keyword extraction.
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

    entity_hint = ""
    if entity_types:
        types_str = "、".join(entity_types[:20])
        entity_hint = f"\n\n【实体类型指引】生成文档时请优先识别和标注以下用户定义的实体类型作为 keywords：{types_str}"

    user_prompt = USER_PROMPT_GENERATE_DOC_TEMPLATE.format(
        node_name=node_name,
        node_type=node_type,
        node_description=node_description or "未指定",
        node_level=node_level,
        chunks_text=chunks_text,
    ) + entity_hint

    return SYSTEM_PROMPT_GENERATE_DOC, user_prompt


# ---------------------------------------------------------------------------
# Incremental classification prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_CLASSIFY = """你是一个知识管理专家。你的任务是判断新资料片段与已有知识文档的关系。

你必须：
- 严格基于内容判断，不得编造不存在的关联
- 如果新资料与已有文档明显矛盾，必须标记为冲突，不得强行合并
- 如果新资料涉及已有文档未覆盖的新主题，标记为新增
- 判断依据必须写明"""

USER_PROMPT_CLASSIFY_TEMPLATE = """以下是一个知识系统中已有的知识文档摘要，以及一批新提交的资料片段。
请判断每段新资料与已有知识的关系。

--- 已有知识文档 ---
{existing_docs_text}
--- 已有知识文档结束 ---

--- 新资料片段 ---
{new_chunks_text}
--- 新资料片段结束 ---

请以如下 JSON 格式输出（不要输出其他内容）：
{{
  "reasoning": "整体判断依据（1-2句话）",
  "classifications": [
    {{
      "chunk_index": 0,
      "relation_type": "new|supplement|correction|conflict|restructure",
      "target_doc_id": "已有文档ID（supplement/correction时必填，其他为null）",
      "reason": "判断理由",
      "conflict_description": "冲突描述（仅conflict时必填，其他为null）",
      "restructure_suggestion": "结构变更建议（仅restructure时必填，其他为null）"
    }}
  ]
}}

relation_type 说明：
- new：已有知识中没有对应主题，需要新建文档
- supplement：已有主题但缺少这些细节，需要补充到已有文档
- correction：新资料证明已有知识过期或有误，需要修正已有文档
- conflict：新旧资料互相矛盾且无法自动判断，需要人工确认
- restructure：节点文档数过多(>15篇)或内容跨域(>3节点相关)，建议结构变更

触发 restructure 的条件：
1. 目标节点已有 > 15 篇文档（节点过载）
2. 新内容与 3 个以上不同节点都高度相关（跨域内容）
输出 restructure 时需补充 restructure_suggestion 字段说明建议"""


# ---------------------------------------------------------------------------
# AI summary prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_SUMMARY = """你是一个知识文档摘要专家。你的任务是为给定的知识文档生成简洁准确的摘要。

你必须：
- 严格基于文档内容概括，不得编造文档中不存在的信息
- 摘要应覆盖文档的核心观点和关键信息
- 使用中文，不超过 200 字"""

USER_PROMPT_SUMMARY_TEMPLATE = """请为以下知识文档生成一份不超过 200 字的摘要。

--- 文档内容 ---
{content}
--- 文档内容结束 ---

请以如下 JSON 格式输出（不要输出其他内容）：
{{
  "summary": "不超过200字的摘要文本"
}}"""


SYSTEM_PROMPT_SUGGEST_TAGS = """你是一个知识标签专家。你的任务是为给定的知识文档推荐准确的关键词标签。

你必须：
- 严格基于文档内容提取关键词，不得编造文档中不存在的概念
- 关键词应涵盖核心主题、关键实体和领域术语
- 返回 3-8 个关键词"""

USER_PROMPT_SUGGEST_TAGS_TEMPLATE = """请为以下知识文档推荐 3-8 个关键词标签。

--- 文档内容 ---
{content}
--- 文档内容结束 ---

请以如下 JSON 格式输出（不要输出其他内容）：
{{
  "keywords": ["关键词1", "关键词2", "关键词3"]
}}"""


def build_summary_prompt(content: str, max_content_chars: int = 6000) -> tuple[str, str]:
    """Build prompts for generating a document summary.

    Returns (system_prompt, user_prompt).
    """
    truncated = content[:max_content_chars]
    if len(content) > max_content_chars:
        truncated += "...(截断)"

    user_prompt = USER_PROMPT_SUMMARY_TEMPLATE.format(content=truncated)
    return SYSTEM_PROMPT_SUMMARY, user_prompt


def build_suggest_tags_prompt(
    content: str, max_content_chars: int = 6000, entity_types: list[str] | None = None,
) -> tuple[str, str]:
    """Build prompts for suggesting document tags/keywords.

    Returns (system_prompt, user_prompt).
    entity_types: optional user-defined entity types to guide tag suggestion.
    """
    truncated = content[:max_content_chars]
    if len(content) > max_content_chars:
        truncated += "...(截断)"

    entity_hint = ""
    if entity_types:
        types_str = "、".join(entity_types[:20])
        entity_hint = f"\n\n【实体类型指引】推荐标签时请优先从以下用户定义的实体类型中提取：{types_str}"

    user_prompt = USER_PROMPT_SUGGEST_TAGS_TEMPLATE.format(content=truncated) + entity_hint
    return SYSTEM_PROMPT_SUGGEST_TAGS, user_prompt


# ---------------------------------------------------------------------------
# Reflection prompts (v0.45.13)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_REFLECTION = """你是一个严格的知识文档质量审查专家。你的任务是评审 AI 生成的摘要或标签，
判断其质量并给出置信度评分。

你必须：
- 严格对照原文内容评审，不偏袒生成结果
- 列出具体问题，不能只说"质量很好"
- 置信度评分 0.0-1.0，标准如下：
  - 0.9+：完全忠于原文、覆盖核心内容、无幻觉
  - 0.7-0.9：基本准确，有小问题
  - 0.5-0.7：有明显遗漏或不准确
  - <0.5：严重问题（幻觉、偏题、遗漏关键内容）"""

USER_PROMPT_SUMMARY_REFLECTION_TEMPLATE = """请评审以下 AI 生成的摘要是否准确。

--- 原文内容 ---
{original_content}
--- 原文内容结束 ---

--- AI 生成的摘要 ---
{generated_summary}
--- 摘要结束 ---

评审维度：
1. 忠实度：摘要是否忠于原文？是否存在幻觉（原文中不存在的信息）？
2. 覆盖度：摘要是否覆盖了原文的核心观点？
3. 简洁度：摘要是否控制在 200 字以内？是否有冗余？

请以如下 JSON 格式输出（不要输出其他内容）：
{{
  "confidence": 0.85,
  "issues": ["问题1", "问题2"],
  "revised_summary": "如果 confidence < 0.7，提供修正后的摘要；否则为 null"
}}"""

USER_PROMPT_TAGS_REFLECTION_TEMPLATE = """请评审以下 AI 推荐的关键词标签是否准确。

--- 原文内容 ---
{original_content}
--- 原文内容结束 ---

--- AI 推荐的标签 ---
{generated_tags}
--- 标签结束 ---

评审维度：
1. 准确性：每个标签是否真实反映原文主题？
2. 覆盖度：是否遗漏了重要的核心概念？
3. 冗余度：是否有含义重复或过于模糊的标签？

请以如下 JSON 格式输出（不要输出其他内容）：
{{
  "confidence": 0.85,
  "issues": ["问题1", "问题2"],
  "revised_tags": ["修正后的标签列表（如果 confidence < 0.7），否则为 null"]
}}"""


def build_summary_reflection_prompt(
    original_content: str, generated_summary: str, max_content_chars: int = 4000
) -> tuple[str, str]:
    """Build prompts for reflecting on a generated summary."""
    truncated = original_content[:max_content_chars]
    if len(original_content) > max_content_chars:
        truncated += "...(截断)"

    user_prompt = USER_PROMPT_SUMMARY_REFLECTION_TEMPLATE.format(
        original_content=truncated,
        generated_summary=generated_summary,
    )
    return SYSTEM_PROMPT_REFLECTION, user_prompt


def build_tags_reflection_prompt(
    original_content: str, generated_tags: list[str], max_content_chars: int = 4000
) -> tuple[str, str]:
    """Build prompts for reflecting on suggested tags."""
    truncated = original_content[:max_content_chars]
    if len(original_content) > max_content_chars:
        truncated += "...(截断)"

    tags_text = ", ".join(generated_tags)
    user_prompt = USER_PROMPT_TAGS_REFLECTION_TEMPLATE.format(
        original_content=truncated,
        generated_tags=tags_text,
    )
    return SYSTEM_PROMPT_REFLECTION, user_prompt


def build_classify_prompt(
    existing_docs: list[dict],
    new_chunks: list[dict],
    max_existing_chars: int = 4000,
    max_new_chars: int = 4000,
    entity_types: list[str] | None = None,
) -> tuple[str, str]:
    """Build prompts for classifying new chunks against existing knowledge.

    existing_docs: list of {doc_id, title, summary} dicts
    new_chunks: list of {index, content_text, page_or_timestamp} dicts
    entity_types: optional user-defined entity types to guide classification

    Returns (system_prompt, user_prompt).
    """
    # Build existing docs summary
    doc_texts = []
    total = 0
    for doc in existing_docs:
        entry = f"[文档 {doc['doc_id']}] {doc['title']}\n{doc['summary']}"
        if total + len(entry) > max_existing_chars:
            break
        doc_texts.append(entry)
        total += len(entry)
    existing_docs_text = "\n\n".join(doc_texts) if doc_texts else "(当前无已有知识文档)"

    # Build new chunks text
    chunk_texts = []
    total = 0
    for chunk in new_chunks:
        idx = chunk.get("index", "?")
        text = chunk.get("content_text", "")
        page = chunk.get("page_or_timestamp", "")
        entry = f"[片段{idx}]"
        if page:
            entry += f" (位置: {page})"
        entry += f"\n{text}"

        if total + len(entry) > max_new_chars:
            remaining = max_new_chars - total
            if remaining > 100:
                chunk_texts.append(entry[:remaining] + "...(截断)")
            break
        chunk_texts.append(entry)
        total += len(entry)
    new_chunks_text = "\n\n".join(chunk_texts) if chunk_texts else "(无新资料片段)"

    entity_hint = ""
    if entity_types:
        types_str = "、".join(entity_types[:20])
        entity_hint = f"\n\n【实体类型指引】分类时请优先关注以下用户定义的实体类型：{types_str}"

    user_prompt = USER_PROMPT_CLASSIFY_TEMPLATE.format(
        existing_docs_text=existing_docs_text,
        new_chunks_text=new_chunks_text,
    ) + entity_hint

    return SYSTEM_PROMPT_CLASSIFY, user_prompt
