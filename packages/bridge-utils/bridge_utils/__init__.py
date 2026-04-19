"""bridge-utils: local summarization + path classification for the KBSQL bridge.

Design goal: produce 80%-quality results WITHOUT any LLM API call. LLM is
reserved as optional quality-boost fallback (see bridge.llm.router).
"""

from .summarize import summarize_extractive, SummaryResult
from .classify import classify_path, TagSuggestion

__all__ = ["summarize_extractive", "SummaryResult", "classify_path", "TagSuggestion"]
