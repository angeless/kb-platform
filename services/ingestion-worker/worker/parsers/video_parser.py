"""Video parser — extracts audio for ASR + detects embedded subtitles.

Uses ffmpeg-python for video processing.
System dependency: ffmpeg must be installed.

Conforms to the parser interface: parse(content: bytes, filename: str) -> list[dict].
"""

import json
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def _check_ffmpeg() -> None:
    """Verify ffmpeg is available on PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "视频解析依赖缺失：ffmpeg 未安装。"
            "请在 ingestion-worker 容器中安装 ffmpeg (apt-get install ffmpeg)"
        )


def _probe_metadata(file_path: str) -> dict:
    """Extract video metadata using ffprobe.

    Returns dict with duration_s, width, height, fps, has_audio, subtitle_streams.
    """
    try:
        import ffmpeg
        probe = ffmpeg.probe(file_path)
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", file_path, e)
        return {}

    video_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    audio_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"),
        None,
    )
    subtitle_streams = [
        s for s in probe.get("streams", []) if s.get("codec_type") == "subtitle"
    ]

    metadata = {
        "duration_s": float(probe.get("format", {}).get("duration", 0)),
        "has_audio": audio_stream is not None,
        "subtitle_streams": len(subtitle_streams),
    }

    if video_stream:
        metadata["width"] = int(video_stream.get("width", 0))
        metadata["height"] = int(video_stream.get("height", 0))
        fps_str = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = fps_str.split("/")
            metadata["fps"] = round(int(num) / int(den), 2) if int(den) else 0
        except (ValueError, ZeroDivisionError):
            metadata["fps"] = 0

    return metadata


def _extract_audio(video_path: str, output_wav: str) -> bool:
    """Extract audio track from video to WAV file using ffmpeg."""
    try:
        import ffmpeg
        (
            ffmpeg.input(video_path)
            .output(output_wav, acodec="pcm_s16le", ar=16000, ac=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return True
    except Exception as e:
        logger.warning("Audio extraction failed for %s: %s", video_path, e)
        return False


def _extract_subtitles(video_path: str, stream_index: int) -> str:
    """Extract subtitle text from a specific subtitle stream."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-map", f"0:s:{stream_index}",
                "-f", "srt", "-"
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Strip SRT timing/numbering, keep text only
            lines = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                # Skip sequence numbers (pure digits) and timestamps (contain -->)
                if not line or line.isdigit() or "-->" in line:
                    continue
                lines.append(line)
            return "\n".join(lines)
    except Exception as e:
        logger.warning("Subtitle extraction failed (stream %d): %s", stream_index, e)
    return ""


DEFAULT_FRAME_INTERVAL_S = 30  # Extract one frame every N seconds
MAX_FRAMES = 50  # Maximum frames to extract
SCENE_CHANGE_THRESHOLD = 0.4  # FFmpeg scene detection threshold


def _extract_keyframes(video_path: str, interval_s: int = DEFAULT_FRAME_INTERVAL_S) -> list[tuple[str, float]]:
    """Extract keyframes from video at regular intervals with scene change dedup.

    Args:
        video_path: Path to video file.
        interval_s: Seconds between frame captures.

    Returns:
        List of (frame_path, timestamp_seconds) tuples.
    """
    frames_dir = tempfile.mkdtemp(prefix="video_frames_")
    frame_pattern = os.path.join(frames_dir, "frame_%04d.jpg")

    try:
        import ffmpeg
        # Use fps filter for interval-based extraction + scene detection for dedup
        (
            ffmpeg.input(video_path)
            .filter("fps", fps=f"1/{interval_s}")
            .filter("select", f"gt(scene,{SCENE_CHANGE_THRESHOLD})+not(mod(n,1))")
            .output(frame_pattern, vframes=MAX_FRAMES, **{"q:v": 2})
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except Exception as e:
        logger.warning("Keyframe extraction failed: %s", e)
        # Cleanup on failure
        import shutil
        shutil.rmtree(frames_dir, ignore_errors=True)
        return []

    # Collect extracted frames with timestamps
    frames = []
    for fname in sorted(os.listdir(frames_dir)):
        if not fname.endswith(".jpg"):
            continue
        fpath = os.path.join(frames_dir, fname)
        # Estimate timestamp from frame index
        idx = int(fname.replace("frame_", "").replace(".jpg", "")) - 1
        timestamp = idx * interval_s
        frames.append((fpath, timestamp))

    return frames


def _ocr_frames(frames: list[tuple[str, float]], filename: str) -> list[dict]:
    """Run OCR on extracted frames and return chunks for frames with text.

    Args:
        frames: List of (frame_path, timestamp_s) tuples.
        filename: Original video filename for tagging.

    Returns:
        List of chunk dicts with OCR text.
    """
    chunks = []
    try:
        from worker.parsers import ocr_parser
    except Exception:
        logger.warning("OCR parser not available, skipping frame OCR")
        return []

    for frame_path, timestamp_s in frames:
        try:
            with open(frame_path, "rb") as f:
                frame_content = f.read()
            ocr_chunks = ocr_parser.parse(frame_content, f"frame_{timestamp_s:.0f}s.jpg")
            for chunk in ocr_chunks:
                chunk["tags"] = chunk.get("tags", {})
                chunk["tags"]["source"] = "video_frame"
                chunk["tags"]["timestamp_s"] = timestamp_s
                chunk["tags"]["video_filename"] = filename
                chunk["page_or_timestamp"] = f"frame_{timestamp_s:.0f}s"
                chunks.append(chunk)
        except Exception as e:
            logger.warning("OCR failed for frame at %.0fs: %s", timestamp_s, e)

    return chunks


def parse(content: bytes, filename: str) -> list[dict]:
    """Parse a video file: extract audio for ASR, detect subtitles, extract keyframes for OCR.

    Returns list of dicts with keys: content_text, page_or_timestamp, tags.
    Returns empty list if ffmpeg is unavailable or video has no extractable content.
    """
    _check_ffmpeg()

    suffix = os.path.splitext(filename)[1] or ".mp4"
    tmp_video = None
    tmp_audio = None

    try:
        # Write video to temp file
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(content)
            tmp_video = f.name

        # Probe metadata
        metadata = _probe_metadata(tmp_video)
        if not metadata:
            logger.warning("Could not probe video metadata for %s", filename)
            return []

        chunks = []

        # Extract audio → ASR
        if metadata.get("has_audio"):
            tmp_audio = tmp_video + ".wav"
            if _extract_audio(tmp_video, tmp_audio):
                try:
                    with open(tmp_audio, "rb") as af:
                        audio_content = af.read()
                    from worker.parsers import asr_parser
                    asr_chunks = asr_parser.parse(audio_content, filename + ".wav")
                    # Tag ASR chunks with video source info
                    for chunk in asr_chunks:
                        chunk["tags"] = chunk.get("tags", {})
                        chunk["tags"]["source"] = "video_audio"
                        chunk["tags"]["video_filename"] = filename
                    chunks.extend(asr_chunks)
                except Exception as e:
                    logger.warning("ASR processing failed for %s: %s", filename, e)

        # Extract embedded subtitles
        for i in range(metadata.get("subtitle_streams", 0)):
            sub_text = _extract_subtitles(tmp_video, i)
            if sub_text:
                chunks.append({
                    "content_text": sub_text,
                    "page_or_timestamp": f"subtitle_stream_{i}",
                    "tags": {
                        "source": "subtitle",
                        "stream_index": i,
                        "video_filename": filename,
                    },
                })

        # Extract keyframes → OCR (v0.48.4)
        frames = _extract_keyframes(tmp_video)
        if frames:
            ocr_chunks = _ocr_frames(frames, filename)
            chunks.extend(ocr_chunks)
            # Cleanup frame files
            import shutil
            frames_dir = os.path.dirname(frames[0][0]) if frames else None
            if frames_dir:
                shutil.rmtree(frames_dir, ignore_errors=True)

        # Add metadata to first chunk, or create metadata-only chunk if no content
        video_meta_tags = {
            "duration_s": metadata.get("duration_s"),
            "resolution": f"{metadata.get('width', 0)}x{metadata.get('height', 0)}",
            "fps": metadata.get("fps"),
        }
        if chunks:
            chunks[0]["tags"].update(video_meta_tags)
        elif metadata.get("duration_s", 0) > 0:
            # No extractable content but valid video — create metadata chunk
            chunks.append({
                "content_text": f"[Video: {filename}, duration: {metadata.get('duration_s', 0):.0f}s]",
                "page_or_timestamp": "00:00:00",
                "tags": {
                    "source": "video_metadata",
                    "video_filename": filename,
                    **video_meta_tags,
                },
            })

        logger.info(
            "Video parsed %s: duration=%.0fs, %d chunks (audio=%s, subtitles=%d)",
            filename,
            metadata.get("duration_s", 0),
            len(chunks),
            metadata.get("has_audio"),
            metadata.get("subtitle_streams", 0),
        )
        return chunks

    finally:
        # Clean up temp files
        for path in [tmp_video, tmp_audio]:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
