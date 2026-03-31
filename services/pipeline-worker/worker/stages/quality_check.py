"""Stage 6: Quality check generated documents.

Performs basic quality validation on generated documents including PII detection.
"""

import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import KnowledgeDoc, KnowledgeDocVersion

logger = logging.getLogger(__name__)

# Minimum content length to pass quality check
MIN_CONTENT_LENGTH = 50

# PII detection patterns (PRD §2.8: 脱敏策略)
_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("身份证号", re.compile(r"\b\d{17}[\dXx]\b")),
    ("手机号", re.compile(r"\b1[3-9]\d{9}\b")),
    ("银行卡号", re.compile(r"\b\d{16,19}\b")),
    ("邮箱地址", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("信用卡号", re.compile(r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13})\b")),
    ("护照号", re.compile(r"\b[EeGg]\d{8}\b")),
    ("社会安全号(SSN)", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("IPv4地址", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


def _detect_pii(text: str) -> list[str]:
    """Scan text for PII patterns. Returns list of detected PII type descriptions."""
    found = []
    for label, pattern in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            count = len(matches)
            # Mask examples for the report (show first 3 chars only)
            example = matches[0][:3] + "***"
            found.append(f"检测到{label}（{count}处，如 {example}）")
    return found


def quality_check(
    db: Session,
    doc_ids: list[uuid.UUID],
    config: dict | None = None,
) -> dict:
    """Run quality checks on generated documents.

    Performs quality validation:
    - Content length check
    - Title presence check
    - Empty content detection
    - PII / sensitive info detection (PRD §2.8)

    Config params (via pipeline_stage_config):
    - min_content_length: int (default 50)
    - require_title: bool (default True)
    - detect_pii: bool (default True)

    Returns:
        {"passed": [doc_id, ...], "flagged": [{"doc_id": ..., "issues": [...]}, ...]}
    """
    cfg = config or {}
    min_length = cfg.get("min_content_length", MIN_CONTENT_LENGTH)
    require_title = cfg.get("require_title", True)
    detect_pii = cfg.get("detect_pii", True)

    passed = []
    flagged = []

    for doc_id in doc_ids:
        doc = db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        ).scalar_one_or_none()
        if doc is None:
            continue

        version = db.execute(
            select(KnowledgeDocVersion).where(
                KnowledgeDocVersion.doc_id == doc_id,
                KnowledgeDocVersion.version == doc.current_version,
            )
        ).scalar_one_or_none()

        issues = []
        content_text = ""

        if version is None:
            issues.append("文档缺少版本内容")
        else:
            content_text = version.content_md.strip()
            if len(content_text) < min_length:
                issues.append(f"文档内容过短（{len(content_text)}字符，最少{min_length}）")

        if require_title and (not doc.title or doc.title.strip() == ""):
            issues.append("文档缺少标题")

        # PII detection (PRD §2.8)
        if detect_pii and content_text:
            pii_issues = _detect_pii(content_text)
            if pii_issues:
                issues.extend(pii_issues)
                logger.warning("PII detected in doc %s: %s", doc_id, pii_issues)

        if issues:
            flagged.append({"doc_id": str(doc_id), "issues": issues})
        else:
            passed.append(str(doc_id))

    return {"passed": passed, "flagged": flagged}
