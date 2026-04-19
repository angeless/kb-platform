"""Triple extractor: markdown IR → list[Triple] for graph upsert.

Extraction modes:

- HEURISTIC (default): pure rule-based. Wiki-links + tags + frontmatter
  fields → triples. Zero LLM calls. Fast, deterministic, ~1ms/file.
- NER_LIGHT (optional): adds spaCy NER on body for PERSON/ORG/PRODUCT
  entities. ~50ms/file with `en_core_web_sm`. Requires `pip install spacy
  + python -m spacy download en_core_web_sm` or `zh_core_web_sm`.
- LLM_DEEP (deferred to v0.55): graphiti-core + GLM-4 for relation
  extraction beyond explicit links. NOT implemented in v0.54 — feature
  flag exists for forward compatibility.

The extractor is **side-effect-free** (no DB writes). The bridge_ingest
stage owns persistence.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from .store import Triple

logger = logging.getLogger(__name__)


class ExtractionMode(str, Enum):
    HEURISTIC = "heuristic"
    NER_LIGHT = "ner_light"
    LLM_DEEP = "llm_deep"  # placeholder, v0.55


def extract_triples(
    ir: dict[str, Any],
    *,
    mode: ExtractionMode = ExtractionMode.HEURISTIC,
) -> list[Triple]:
    """Convert a bridge markdown IR into a list of triples.

    Args:
        ir: bridge IR dict (must have 'relative_path' or 'source_path',
            'frontmatter', 'wiki_links', 'content_md')
        mode: extraction strategy

    Returns:
        List of Triple objects. Subject identifiers are KB-relative paths
        (e.g. "wiki/concepts/foo") with the .md extension stripped.
    """
    if mode == ExtractionMode.LLM_DEEP:
        raise NotImplementedError("LLM_DEEP mode is v0.55 work")

    subj = _normalize_subject(ir)
    if subj is None:
        return []

    triples: list[Triple] = []

    # 1) wiki-links → references_
    for link in ir.get("wiki_links", []) or []:
        target = _strip_md_ext(link)
        if target == subj:
            continue  # skip self-loops
        triples.append(
            Triple(
                subject=subj,
                predicate="references_",
                object=target,
                properties={"kind": "wiki-link"},
            )
        )

    # 2) frontmatter `related: [...]` → references_ (kind=frontmatter-related)
    for related in ir.get("frontmatter", {}).get("related", []) or []:
        if not isinstance(related, str):
            continue
        target = _strip_md_ext(related)
        if target == subj:
            continue
        triples.append(
            Triple(
                subject=subj,
                predicate="references_",
                object=target,
                properties={"kind": "frontmatter-related"},
            )
        )

    # 3) frontmatter `sources: [...]` → references_ (kind=cites)
    for src in ir.get("frontmatter", {}).get("sources", []) or []:
        if not isinstance(src, str):
            continue
        target = _strip_md_ext(src)
        if target == subj:
            continue
        triples.append(
            Triple(
                subject=subj,
                predicate="references_",
                object=target,
                properties={"kind": "cites"},
            )
        )

    # 4) frontmatter `tags: [...]` → tagged_with
    for tag in ir.get("frontmatter", {}).get("tags", []) or []:
        if not isinstance(tag, str) or not tag.strip():
            continue
        triples.append(
            Triple(
                subject=subj,
                predicate="tagged_with",
                object=tag.strip(),
                properties={"weight": 1.0},
            )
        )

    # 5) frontmatter `session_id` → produced_in
    sid = ir.get("frontmatter", {}).get("session_id")
    if isinstance(sid, str) and sid.strip():
        triples.append(
            Triple(
                subject=subj,
                predicate="produced_in",
                object=sid.strip(),
            )
        )

    # 6) NER (optional): extract PERSON/ORG/PRODUCT → tagged_with(weight=0.5)
    if mode == ExtractionMode.NER_LIGHT:
        triples.extend(_ner_triples(subj, ir.get("content_md", "")))

    return triples


def _normalize_subject(ir: dict[str, Any]) -> str | None:
    """Subject = KB-relative path without the .md extension.

    Falls back to source_path stem if no relative_path set.
    """
    rel = ir.get("relative_path")
    if rel:
        return _strip_md_ext(rel)
    src = ir.get("source_path")
    if src:
        from pathlib import Path
        return Path(src).stem
    return None


def _strip_md_ext(path: str) -> str:
    return path[:-3] if path.endswith(".md") else path


def _ner_triples(subj: str, body: str) -> list[Triple]:
    """spaCy NER → tagged_with(weight=0.5) edges. Best-effort."""
    try:
        import spacy
    except ImportError:
        logger.debug("spacy not installed; skipping NER extraction")
        return []

    # Pick the right model (cheap heuristic — first 1000 chars CJK density)
    cjk = sum(1 for ch in body[:1000] if "\u4e00" <= ch <= "\u9fff")
    model_name = "zh_core_web_sm" if cjk > 50 else "en_core_web_sm"
    try:
        nlp = spacy.load(model_name)
    except OSError:
        logger.debug("spaCy model %s not installed; skipping NER", model_name)
        return []

    doc = nlp(body[:50000])  # cap to keep extraction sub-second
    seen: set[str] = set()
    triples: list[Triple] = []
    for ent in doc.ents:
        if ent.label_ not in {"PERSON", "ORG", "PRODUCT", "GPE", "WORK_OF_ART"}:
            continue
        text = ent.text.strip()
        if len(text) < 2 or text in seen:
            continue
        seen.add(text)
        triples.append(
            Triple(
                subject=subj,
                predicate="tagged_with",
                object=f"ner:{ent.label_.lower()}:{text}",
                properties={"weight": 0.5},
            )
        )
    return triples
