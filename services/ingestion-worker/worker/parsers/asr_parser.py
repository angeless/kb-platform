"""Audio ASR parser — extracts text from audio files using OpenAI Whisper.

Uses the openai-whisper library for local speech-to-text transcription.
Supports: MP3, WAV, M4A, FLAC, OGG, WEBM (via ffmpeg).
System dependency: ffmpeg must be installed.

Conforms to the parser interface: parse(content: bytes, filename: str) -> list[dict].
"""

import logging
import os
import tempfile
import threading

logger = logging.getLogger(__name__)

# Default Whisper model size (base = 140MB, good balance of speed/accuracy)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# Minimum segment text length to keep
MIN_SEGMENT_CHARS = 5

# Thread-safe model cache (double-checked locking pattern)
_model_lock = threading.Lock()
_whisper_model = None


def _get_model():
    """Load and cache the Whisper model (thread-safe)."""
    global _whisper_model
    if _whisper_model is None:
        with _model_lock:
            if _whisper_model is None:
                import whisper
                logger.info("Loading Whisper model '%s'...", WHISPER_MODEL)
                _whisper_model = whisper.load_model(WHISPER_MODEL)
    return _whisper_model


def _format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse(content: bytes, filename: str) -> list[dict]:
    """Parse an audio file using Whisper ASR to extract text.

    Returns list of dicts with keys: content_text, page_or_timestamp, tags.
    Returns empty list if Whisper/ffmpeg is unavailable or audio has no speech.
    """
    try:
        import whisper  # noqa: F401
    except ImportError:
        logger.warning("openai-whisper not installed — cannot transcribe %s", filename)
        return []

    # Write audio to temp file (Whisper requires file path)
    suffix = os.path.splitext(filename)[1] or ".wav"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        logger.error("Failed to write temp audio file for %s: %s", filename, e)
        return []

    try:
        model = _get_model()
        result = model.transcribe(tmp_path, verbose=False)
    except Exception as e:
        logger.warning("Whisper transcription failed for %s: %s", filename, e)
        return []
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    segments = result.get("segments", [])
    detected_lang = result.get("language", "unknown")
    full_text = result.get("text", "").strip()

    if not full_text:
        logger.info("No speech detected in %s", filename)
        return []

    # Build chunks from segments
    chunks = []
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if len(text) < MIN_SEGMENT_CHARS:
            continue

        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)
        timestamp = f"{_format_timestamp(start)}-{_format_timestamp(end)}"

        chunks.append({
            "content_text": text,
            "page_or_timestamp": timestamp,
            "tags": {
                "source_type": "audio",
                "filename": filename,
                "language": detected_lang,
                "segment_index": i,
                "start_seconds": round(start, 2),
                "end_seconds": round(end, 2),
            },
        })

    # Fallback: if no segments but full_text exists, return as single chunk
    if not chunks and full_text:
        chunks.append({
            "content_text": full_text,
            "page_or_timestamp": "00:00:00-full",
            "tags": {
                "source_type": "audio",
                "filename": filename,
                "language": detected_lang,
            },
        })

    logger.info(
        "ASR parsed %s: language=%s, %d segments, %d chunks",
        filename, detected_lang, len(segments), len(chunks),
    )
    return chunks
