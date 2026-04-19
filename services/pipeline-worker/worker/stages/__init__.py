"""Pipeline stages for the knowledge processing pipeline.

v0.52 ships 7 ingestion-pipeline stages (classify → embed → review_notify).
v0.54 adds bridge_ingest as a stage 0 hook that runs BEFORE classify when
files arrive via the bridge service (KB filesystem watcher / explicit
REST call). Pipeline runners that don't use bridge can ignore it.
"""

from .classify import classify_chunks
from .architecture_draft import generate_architecture_draft
from .doc_generate import generate_documents
from .quality_check import quality_check
from .conflict_detect import detect_conflicts
from .embed import generate_embeddings
from .review_notify import notify_review
from .bridge_ingest import bridge_ingest  # v0.54: KB markdown → BridgeSyncRecord

__all__ = [
    "classify_chunks",
    "generate_architecture_draft",
    "generate_documents",
    "quality_check",
    "detect_conflicts",
    "generate_embeddings",
    "notify_review",
    "bridge_ingest",
]
